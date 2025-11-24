import os
import sys
import time
import re
import json
import logging
import traceback
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import quote
from html import escape as html_escape
from datetime import datetime

import requests
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager


# ================== CRASH LOGGING ==================

def _crash_log_path() -> Path:
    """Get path to crash log file in app data directory."""
    if sys.platform == "win32":
        app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        app_data = Path.home() / ".local" / "share"
    log_dir = app_data / "ElliottsSingularControls" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "crash_report.txt"


def log_crash(error: Exception, context: str = ""):
    """Log a crash/error to the crash report file."""
    try:
        log_path = _crash_log_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"CRASH REPORT - {timestamp}\n")
            f.write(f"Version: {_runtime_version()}\n")
            if context:
                f.write(f"Context: {context}\n")
            f.write(f"Error Type: {type(error).__name__}\n")
            f.write(f"Error Message: {str(error)}\n")
            f.write("\nTraceback:\n")
            f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        pass  # Don't crash while logging crashes


def setup_crash_handler():
    """Setup global exception handler to log unhandled exceptions."""
    def exception_handler(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log_crash(exc_value, "Unhandled exception")
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = exception_handler


# Initialize crash handler
setup_crash_handler()

# ================== 0. PATHS & VERSION ==================

def _app_root() -> Path:
    """Folder where the app is running from (install dir or source)."""
    if getattr(sys, "frozen", False):  # PyInstaller exe
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent  # Go up one level from elliotts_singular_controls/


def _runtime_version() -> str:
    """
    Try to read version from version.txt next to the app, then package version.
    Fallback to '1.0.9' if not present.
    """
    try:
        vfile = _app_root() / "version.txt"
        if vfile.exists():
            text = vfile.read_text(encoding="utf-8").strip()
            if ":" in text:
                text = text.split(":", 1)[1].strip()
            return text
    except Exception:
        pass
    # Try to get version from package
    try:
        from elliotts_singular_controls import __version__
        return __version__
    except Exception:
        pass
    return "1.0.9"


# ================== 1. CONFIG & GLOBALS ==================

DEFAULT_PORT = int(os.getenv("SINGULAR_TWEAKS_PORT", "3113"))

SINGULAR_API_BASE = "https://app.singular.live/apiv2"
TFL_URL = (
    "https://api.tfl.gov.uk/Line/Mode/"
    "tube,overground,dlr,elizabeth-line,tram,cable-car/Status"
)

# Underground lines
TFL_UNDERGROUND = [
    "Bakerloo",
    "Central",
    "Circle",
    "District",
    "Hammersmith & City",
    "Jubilee",
    "Metropolitan",
    "Northern",
    "Piccadilly",
    "Victoria",
    "Waterloo & City",
]

# Overground/Other lines
TFL_OVERGROUND = [
    "Liberty",
    "Lioness",
    "Mildmay",
    "Suffragette",
    "Weaver",
    "Windrush",
    "DLR",
    "Elizabeth line",
    "Tram",
    "IFS Cloud Cable Car",
]

# All TFL lines combined
TFL_LINES = TFL_UNDERGROUND + TFL_OVERGROUND

# Official TFL line colours (matched to TfL brand guidelines)
TFL_LINE_COLOURS = {
    # Underground
    "Bakerloo": "#B36305",
    "Central": "#E32017",
    "Circle": "#FFD300",
    "District": "#00782A",
    "Hammersmith & City": "#F3A9BB",
    "Jubilee": "#A0A5A9",
    "Metropolitan": "#9B0056",
    "Northern": "#000000",
    "Piccadilly": "#003688",
    "Victoria": "#0098D4",
    "Waterloo & City": "#95CDBA",
    # London Overground lines (new branding)
    "Liberty": "#6bcdb2",
    "Lioness": "#fbb01c",
    "Mildmay": "#137cbd",
    "Suffragette": "#6a9a3a",
    "Weaver": "#9b4f7a",
    "Windrush": "#e05206",
    # Other rail
    "DLR": "#00afad",
    "Elizabeth line": "#6950a1",
    "Tram": "#6fc42a",
    "IFS Cloud Cable Car": "#e21836",
}

def _config_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        # When running from source, use elliotts_singular_controls directory
        base = Path(__file__).resolve().parent
    return base

CONFIG_PATH = _config_dir() / "elliotts_singular_controls_config.json"

logger = logging.getLogger("elliotts_singular_controls")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class AppConfig(BaseModel):
    singular_token: Optional[str] = None  # Legacy single token (for migration)
    singular_tokens: Dict[str, str] = {}  # name → token mapping for multiple apps
    singular_stream_url: Optional[str] = None
    tfl_app_id: Optional[str] = None
    tfl_app_key: Optional[str] = None
    enable_tfl: bool = False  # Disabled by default for new installs
    tfl_auto_refresh: bool = False  # Auto-refresh TFL data every 60s
    # TriCaster module settings
    enable_tricaster: bool = False
    tricaster_host: Optional[str] = None
    tricaster_user: str = "admin"
    tricaster_pass: Optional[str] = None
    # DDR-to-Singular Timer Sync settings
    tricaster_singular_token: Optional[str] = None  # Control App token for timer sync
    tricaster_timer_fields: Dict[str, Dict[str, str]] = {}  # DDR mappings: {"1": {"min": "field_id", "sec": "field_id", "timer": "field_id"}}
    tricaster_round_mode: str = "frames"  # "frames" or "none" - whether to round to frame boundaries
    # Auto-sync settings
    tricaster_auto_sync: bool = False  # Enable automatic DDR duration syncing
    tricaster_auto_sync_interval: int = 3  # Seconds between sync checks (2-10)
    theme: str = "dark"
    port: Optional[int] = None


def load_config() -> AppConfig:
    base: Dict[str, Any] = {
        "singular_token": os.getenv("SINGULAR_TOKEN") or None,
        "singular_tokens": {},
        "singular_stream_url": os.getenv("SINGULAR_STREAM_URL") or None,
        "tfl_app_id": os.getenv("TFL_APP_ID") or None,
        "tfl_app_key": os.getenv("TFL_APP_KEY") or None,
        "enable_tfl": False,  # Disabled by default
        "tfl_auto_refresh": False,
        # TriCaster defaults
        "enable_tricaster": False,
        "tricaster_host": os.getenv("TRICASTER_HOST") or None,
        "tricaster_user": os.getenv("TRICASTER_USER", "admin"),
        "tricaster_pass": os.getenv("TRICASTER_PASS") or None,
        # DDR-to-Singular Timer Sync defaults
        "tricaster_singular_token": os.getenv("TRICASTER_SINGULAR_TOKEN") or None,
        "tricaster_timer_fields": {},
        "tricaster_round_mode": os.getenv("TRICASTER_ROUND_MODE", "frames"),
        # Auto-sync defaults
        "tricaster_auto_sync": False,
        "tricaster_auto_sync_interval": 3,
        "theme": "dark",
        "port": int(os.getenv("SINGULAR_TWEAKS_PORT")) if os.getenv("SINGULAR_TWEAKS_PORT") else None,
    }
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                file_data = json.load(f)
            base.update(file_data)
        except Exception as e:
            logger.warning("Failed to load config file %s: %s", CONFIG_PATH, e)
    cfg = AppConfig(**base)
    # Migrate legacy singular_token to singular_tokens
    if cfg.singular_token and not cfg.singular_tokens:
        cfg.singular_tokens = {"Default": cfg.singular_token}
        cfg.singular_token = None  # Clear legacy field
    return cfg


def save_config(cfg: AppConfig) -> None:
    try:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(cfg.model_dump(), f, indent=2)
        logger.info("Saved config to %s", CONFIG_PATH)
    except Exception as e:
        logger.error("Failed to save config file %s: %s", CONFIG_PATH, e)


CONFIG = load_config()

def effective_port() -> int:
    return CONFIG.port or DEFAULT_PORT


COMMAND_LOG: List[str] = []
MAX_LOG_ENTRIES = 200

def log_event(kind: str, detail: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    line = f"[{ts}] {kind}: {detail}"
    COMMAND_LOG.append(line)
    if len(COMMAND_LOG) > MAX_LOG_ENTRIES:
        del COMMAND_LOG[: len(COMMAND_LOG) - MAX_LOG_ENTRIES]


# ================== 2. FASTAPI APP ==================

def generate_unique_id(route: APIRoute) -> str:
    methods = sorted([m for m in route.methods if m in {"GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"}])
    method = methods[0].lower() if methods else "get"
    safe_path = re.sub(r"[^a-z0-9]+", "-", route.path.lower()).strip("-")
    return f"{route.name}-{method}-{safe_path}"

app = FastAPI(
    title="Elliott's Singular Controls",
    description="Helper UI and HTTP API for Singular.live + optional TfL data.",
    version=_runtime_version(),
    generate_unique_id_function=generate_unique_id,
)

# static files (for font)
STATIC_DIR = _app_root() / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=False), name="static")


def tfl_params() -> Dict[str, str]:
    p: Dict[str, str] = {}
    if CONFIG.tfl_app_id and CONFIG.tfl_app_key and CONFIG.enable_tfl:
        p["app_id"] = CONFIG.tfl_app_id
        p["app_key"] = CONFIG.tfl_app_key
    return p


def fetch_all_line_statuses() -> Dict[str, str]:
    if not CONFIG.enable_tfl:
        raise HTTPException(400, "TfL integration is disabled in settings")
    try:
        r = requests.get(TFL_URL, params=tfl_params(), timeout=10)
        r.raise_for_status()
        out: Dict[str, str] = {}
        for line in r.json():
            out[line["name"]] = line.get("lineStatuses", [{}])[0].get("statusSeverityDescription", "Unknown")
        return out
    except requests.RequestException as e:
        logger.error("TfL API request failed: %s", e)
        raise HTTPException(503, f"TfL API request failed: {str(e)}")


# ================== TRICASTER API HELPERS ==================

import xml.etree.ElementTree as ET
from requests.auth import HTTPBasicAuth

def tricaster_request(endpoint: str, method: str = "GET", data: str = None) -> requests.Response:
    """Make a request to the TriCaster API."""
    if not CONFIG.enable_tricaster:
        raise HTTPException(400, "TriCaster module is disabled")
    if not CONFIG.tricaster_host:
        raise HTTPException(400, "TriCaster host not configured")

    url = f"http://{CONFIG.tricaster_host}{endpoint}"
    auth = None
    if CONFIG.tricaster_user and CONFIG.tricaster_pass:
        auth = HTTPBasicAuth(CONFIG.tricaster_user, CONFIG.tricaster_pass)

    headers = {"Connection": "close", "Accept": "application/xml"}
    if method == "POST" and data:
        headers["Content-Type"] = "text/xml"

    try:
        if method == "GET":
            resp = requests.get(url, auth=auth, headers=headers, timeout=6)
        else:
            resp = requests.post(url, auth=auth, headers=headers, data=data, timeout=6)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        logger.error("TriCaster request failed: %s", e)
        raise HTTPException(503, f"TriCaster request failed: {str(e)}")


def tricaster_shortcut(name: str, params: Dict[str, str] = None) -> Dict[str, Any]:
    """Execute a TriCaster shortcut command."""
    xml_parts = [f"<shortcut name='{name}'>"]
    if params:
        for key, value in params.items():
            xml_parts.append(f"<entry key='{key}' value='{value}'/>")
    xml_parts.append("</shortcut>")
    xml_data = "".join(xml_parts)

    resp = tricaster_request("/v1/shortcut", method="POST", data=xml_data)
    return {"ok": True, "command": name, "params": params}


def tricaster_get_dictionary(key: str) -> Dict[str, Any]:
    """Get data from TriCaster dictionary (timecodes, status, etc)."""
    resp = tricaster_request(f"/v1/dictionary?key={key}")
    return {"raw_xml": resp.text}


def tricaster_get_ddr_info() -> Dict[str, Any]:
    """Get DDR timecode and duration info from TriCaster."""
    try:
        resp = tricaster_request("/v1/dictionary?key=ddr_timecode")
        xml_text = resp.text
        root = ET.fromstring(xml_text)

        ddr_info = {}
        for i in range(1, 5):  # DDR1-4
            # Try different XML formats
            el = root.find(f".//ddr[@index='{i}']") or root.find(f".//ddr{i}")
            if el is not None:
                info = {
                    "duration": el.get("file_duration") or el.get("duration"),
                    "elapsed": el.get("clip_seconds_elapsed"),
                    "remaining": el.get("clip_seconds_remaining"),
                    "framerate": el.get("clip_framerate"),
                    "playing": el.get("playing", "false") == "true",
                    "filename": el.get("filename") or el.get("clip_name"),
                }
                ddr_info[f"ddr{i}"] = info

        return {"ok": True, "ddrs": ddr_info}
    except ET.ParseError as e:
        logger.error("Failed to parse TriCaster XML: %s", e)
        return {"ok": False, "error": f"XML parse error: {str(e)}"}
    except Exception as e:
        logger.error("TriCaster DDR info failed: %s", e)
        raise HTTPException(503, f"TriCaster DDR info failed: {str(e)}")


def tricaster_get_tally() -> Dict[str, Any]:
    """Get current program/preview tally status from TriCaster."""
    try:
        resp = tricaster_request("/v1/dictionary?key=tally")
        xml_text = resp.text
        root = ET.fromstring(xml_text)

        tally = {
            "program": [],
            "preview": [],
        }

        # Parse tally data - format varies by TriCaster model
        for el in root.iter():
            if el.get("on_pgm") == "true" or el.get("program") == "true":
                tally["program"].append(el.tag or el.get("name", "unknown"))
            if el.get("on_pvw") == "true" or el.get("preview") == "true":
                tally["preview"].append(el.tag or el.get("name", "unknown"))

        return {"ok": True, "tally": tally}
    except Exception as e:
        logger.error("TriCaster tally failed: %s", e)
        return {"ok": False, "error": str(e)}


def tricaster_test_connection() -> Dict[str, Any]:
    """Test connection to TriCaster."""
    if not CONFIG.tricaster_host:
        return {"ok": False, "error": "No TriCaster host configured"}

    try:
        resp = tricaster_request("/v1/version")
        return {"ok": True, "host": CONFIG.tricaster_host, "response": resp.text[:200]}
    except HTTPException as e:
        return {"ok": False, "error": e.detail}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# DDR-to-Singular Timer Sync Functions
# ─────────────────────────────────────────────────────────────────────────────

# Cache for Singular field-to-subcomposition mappings (per token)
_singular_field_map_cache: Dict[str, Dict[str, str]] = {}


def _timecode_to_seconds(timecode: Optional[str]) -> Optional[float]:
    """Convert timecode string (HH:MM:SS.ff or MM:SS.ff or seconds) to float seconds."""
    if timecode is None:
        return None
    s = str(timecode).strip()
    if not s:
        return None
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 3:
            h, m, sec = parts
            return int(h) * 3600 + int(m) * 60 + float(sec)
        if len(parts) == 2:
            m, sec = parts
            return int(m) * 60 + float(sec)
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _split_minutes_seconds(total_seconds: float, fps: Optional[float]) -> Tuple[int, float]:
    """Split total seconds into minutes and seconds, optionally rounding to frame boundaries."""
    ts = max(0.0, float(total_seconds))
    if CONFIG.tricaster_round_mode.lower() == "frames" and fps and fps > 0:
        ts = round(ts * fps) / fps
    minutes = int(ts // 60)
    seconds = ts - minutes * 60
    seconds = round(seconds + 1e-9, 2)
    if seconds >= 60.0:
        minutes += 1
        seconds = 0.0
    return minutes, seconds


def _get_ddr_duration_and_fps(ddr_index: int) -> Tuple[float, Optional[float]]:
    """Get duration and FPS for a specific DDR from TriCaster."""
    if not CONFIG.enable_tricaster:
        raise HTTPException(400, "TriCaster module is disabled")
    if not CONFIG.tricaster_host:
        raise HTTPException(400, "TriCaster host not configured")

    # Try both dictionary keys
    for key in ["ddr_timecode", "timecode"]:
        try:
            resp = tricaster_request(f"/v1/dictionary?key={key}")
            root = ET.fromstring(resp.text)

            # Try format: <ddr index="1" ...>
            el = root.find(f".//ddr[@index='{ddr_index}']")
            if el is not None:
                dur = _timecode_to_seconds(el.get("file_duration") or el.get("duration"))
                fps = None
                if el.get("clip_framerate"):
                    try:
                        fps = float(el.get("clip_framerate"))
                    except ValueError:
                        pass
                if dur is not None:
                    return dur, fps

            # Try format: <ddr1 ...>
            el = root.find(f".//ddr{ddr_index}")
            if el is not None:
                dur = _timecode_to_seconds(el.get("file_duration") or el.get("duration"))
                if dur is None:
                    # Calculate from elapsed + remaining
                    elapsed = el.get("clip_seconds_elapsed")
                    remaining = el.get("clip_seconds_remaining")
                    if elapsed and remaining:
                        try:
                            dur = float(elapsed) + float(remaining)
                        except ValueError:
                            pass
                fps = None
                if el.get("clip_framerate"):
                    try:
                        fps = float(el.get("clip_framerate"))
                    except ValueError:
                        pass
                if dur is not None:
                    return dur, fps
        except Exception:
            continue

    raise HTTPException(404, f"DDR{ddr_index} duration not found in TriCaster data")


def _get_singular_model(token: str) -> list:
    """Fetch the Singular control app model."""
    url = f"{SINGULAR_API_BASE}/controlapps/{token}/model"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _build_singular_field_map(token: str, field_ids: List[str]) -> Dict[str, str]:
    """Build a mapping of field IDs to their subcomposition IDs."""
    needed = set(field_ids)
    mapping: Dict[str, str] = {}
    data = _get_singular_model(token)

    for comp in data:
        comp_id = comp.get("id")
        for node in comp.get("model", []):
            node_id = node.get("id")
            if node_id in needed:
                mapping[node_id] = comp_id
        for sub in comp.get("subcompositions", []):
            sub_id = sub.get("id")
            for node in sub.get("model", []):
                node_id = node.get("id")
                if node_id in needed:
                    mapping[node_id] = sub_id

    return mapping


def _ensure_singular_field_map(token: str, field_ids: List[str]) -> Dict[str, str]:
    """Ensure we have a cached field map for the given token and fields."""
    cache_key = f"{token}:{','.join(sorted(field_ids))}"
    if cache_key not in _singular_field_map_cache:
        _singular_field_map_cache[cache_key] = _build_singular_field_map(token, field_ids)
    return _singular_field_map_cache[cache_key]


def _patch_singular_fields(token: str, field_values: Dict[str, Any]) -> Dict[str, Any]:
    """Patch Singular fields with values, grouping by subcomposition."""
    field_ids = list(field_values.keys())
    field_map = _ensure_singular_field_map(token, field_ids)

    # Group fields by subcomposition
    grouped: Dict[str, Dict[str, Any]] = {}
    for field_id, value in field_values.items():
        sub_id = field_map.get(field_id)
        if sub_id:
            grouped.setdefault(sub_id, {})[field_id] = value

    # Build payload
    body = [{"subCompositionId": sub_id, "payload": payload} for sub_id, payload in grouped.items()]

    url = f"{SINGULAR_API_BASE}/controlapps/{token}/control"
    resp = requests.patch(url, json=body, timeout=10)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {"success": True}


def sync_ddr_to_singular(ddr_num: int) -> Dict[str, Any]:
    """Sync a DDR's duration to Singular timer fields."""
    token = CONFIG.tricaster_singular_token
    if not token:
        raise HTTPException(400, "No Singular token configured for timer sync")

    ddr_key = str(ddr_num)
    fields = CONFIG.tricaster_timer_fields.get(ddr_key)
    if not fields:
        raise HTTPException(400, f"No timer fields configured for DDR {ddr_num}")

    min_field = fields.get("min")
    sec_field = fields.get("sec")
    if not min_field or not sec_field:
        raise HTTPException(400, f"DDR {ddr_num} missing 'min' or 'sec' field configuration")

    # Get duration from TriCaster
    duration, fps = _get_ddr_duration_and_fps(ddr_num)
    minutes, seconds = _split_minutes_seconds(duration, fps)

    # Patch Singular fields
    field_values = {
        min_field: int(minutes),
        sec_field: float(seconds),
    }
    _patch_singular_fields(token, field_values)

    return {
        "ok": True,
        "ddr": ddr_num,
        "duration_seconds": duration,
        "minutes": minutes,
        "seconds": seconds,
        "fps": fps,
        "round_mode": CONFIG.tricaster_round_mode,
    }


def sync_all_ddrs_to_singular() -> Dict[str, Any]:
    """Sync all configured DDRs to their Singular timer fields."""
    results = {}
    errors = []

    for ddr_key in CONFIG.tricaster_timer_fields.keys():
        try:
            ddr_num = int(ddr_key)
            result = sync_ddr_to_singular(ddr_num)
            results[f"ddr{ddr_num}"] = result
        except Exception as e:
            errors.append(f"DDR {ddr_key}: {str(e)}")

    return {
        "ok": len(errors) == 0,
        "results": results,
        "errors": errors if errors else None,
    }


def send_timer_command(ddr_num: int, command: str) -> Dict[str, Any]:
    """Send a timer command (start, pause, reset) to Singular for a DDR."""
    token = CONFIG.tricaster_singular_token
    if not token:
        raise HTTPException(400, "No Singular token configured for timer sync")

    ddr_key = str(ddr_num)
    fields = CONFIG.tricaster_timer_fields.get(ddr_key)
    if not fields:
        raise HTTPException(400, f"No timer fields configured for DDR {ddr_num}")

    timer_field = fields.get("timer")
    if not timer_field:
        raise HTTPException(400, f"DDR {ddr_num} missing 'timer' field configuration")

    # Send timer command
    field_values = {
        timer_field: {"command": command}
    }
    _patch_singular_fields(token, field_values)

    return {"ok": True, "ddr": ddr_num, "command": command}


def restart_timer(ddr_num: int) -> Dict[str, Any]:
    """Restart a timer: pause -> reset (no auto-start)."""
    send_timer_command(ddr_num, "pause")
    time.sleep(0.05)  # Small delay between commands
    send_timer_command(ddr_num, "reset")
    return {"ok": True, "ddr": ddr_num, "action": "restart (paused/reset)"}


def send_to_datastream(payload: Dict[str, Any]):
    if not CONFIG.singular_stream_url:
        raise HTTPException(400, "No Singular data stream URL configured")
    resp = None
    try:
        resp = requests.put(
            CONFIG.singular_stream_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        return {
            "stream_url": CONFIG.singular_stream_url,
            "status": resp.status_code,
            "response": resp.text,
        }
    except requests.RequestException as e:
        logger.exception("Datastream PUT failed")
        return {
            "stream_url": CONFIG.singular_stream_url,
            "status": resp.status_code if resp is not None else 0,
            "response": resp.text if resp is not None else "",
            "error": str(e),
        }


def ctrl_patch(items: list, token: str):
    """Send control PATCH to Singular with a specific token."""
    if not token:
        raise HTTPException(400, "No Singular control app token provided")
    ctrl_control = f"{SINGULAR_API_BASE}/controlapps/{token}/control"
    try:
        resp = requests.patch(
            ctrl_control,
            json=items,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        log_event("Control PATCH", f"{ctrl_control} items={len(items)}")
        return resp
    except requests.RequestException as e:
        logger.exception("Control PATCH failed")
        raise HTTPException(503, f"Control PATCH failed: {str(e)}")


def now_ms_float() -> float:
    return float(time.time() * 1000)


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "item"


def _base_url(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{proto}://{host}"


# ================== 3. REGISTRY (Control App model) ==================

# REGISTRY structure: {app_name: {key: {id, name, fields, app_name, token}}}
REGISTRY: Dict[str, Dict[str, Dict[str, Any]]] = {}
ID_TO_KEY: Dict[str, Tuple[str, str]] = {}  # id → (app_name, key)

def singular_model_fetch(token: str) -> Any:
    """Fetch model for a specific token."""
    ctrl_model = f"{SINGULAR_API_BASE}/controlapps/{token}/model"
    try:
        r = requests.get(ctrl_model, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.error("Model fetch failed: %s", e)
        raise RuntimeError(f"Model fetch failed: {r.status_code if 'r' in locals() else 'unknown'}")


def _walk_nodes(node):
    items = []
    if isinstance(node, dict):
        items.append(node)
        for k in ("subcompositions", "Subcompositions"):
            if k in node and isinstance(node[k], list):
                for child in node[k]:
                    items.extend(_walk_nodes(child))
    elif isinstance(node, list):
        for el in node:
            items.extend(_walk_nodes(el))
    return items


def build_registry_for_app(app_name: str, token: str) -> int:
    """Build registry for a single app. Returns number of subcompositions found."""
    if app_name not in REGISTRY:
        REGISTRY[app_name] = {}
    else:
        # Clear existing entries for this app from ID_TO_KEY
        for sid, (a, k) in list(ID_TO_KEY.items()):
            if a == app_name:
                del ID_TO_KEY[sid]
        REGISTRY[app_name].clear()

    try:
        data = singular_model_fetch(token)
    except Exception as e:
        logger.warning("Failed to fetch model for app %s: %s", app_name, e)
        return 0

    flat = _walk_nodes(data)
    for n in flat:
        sid = n.get("id")
        name = n.get("name")
        model = n.get("model")
        if not sid or name is None or model is None:
            continue
        key = slugify(name)
        orig_key = key
        i = 2
        while key in REGISTRY[app_name] and REGISTRY[app_name][key]["id"] != sid:
            key = f"{orig_key}-{i}"
            i += 1
        REGISTRY[app_name][key] = {
            "id": sid,
            "name": name,
            "fields": {(f.get("id") or ""): f for f in (model or [])},
            "app_name": app_name,
            "token": token,
        }
        ID_TO_KEY[sid] = (app_name, key)
    return len(REGISTRY[app_name])


def build_registry():
    """Build registry for all configured apps."""
    REGISTRY.clear()
    ID_TO_KEY.clear()
    total = 0
    for app_name, token in CONFIG.singular_tokens.items():
        count = build_registry_for_app(app_name, token)
        total += count
        log_event("Registry", f"App '{app_name}': {count} subcompositions")
    log_event("Registry", f"Total: {total} subcompositions from {len(CONFIG.singular_tokens)} app(s)")


def kfind(key_or_id: str, app_name: Optional[str] = None) -> Tuple[str, str]:
    """Find a subcomposition by key or id. Returns (app_name, key)."""
    # If app_name specified, look only in that app
    if app_name:
        if app_name in REGISTRY and key_or_id in REGISTRY[app_name]:
            return (app_name, key_or_id)
        if key_or_id in ID_TO_KEY:
            found_app, found_key = ID_TO_KEY[key_or_id]
            if found_app == app_name:
                return (found_app, found_key)
        raise HTTPException(404, f"Subcomposition not found: {key_or_id} in app {app_name}")

    # Search across all apps
    for a_name, subs in REGISTRY.items():
        if key_or_id in subs:
            return (a_name, key_or_id)
    if key_or_id in ID_TO_KEY:
        return ID_TO_KEY[key_or_id]
    raise HTTPException(404, f"Subcomposition not found: {key_or_id}")


def coerce_value(field_meta: Dict[str, Any], value_str: str, as_string: bool = False):
    if as_string:
        return value_str
    ftype = (field_meta.get("type") or "").lower()
    if ftype in ("number", "range", "slider"):
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str
    if ftype in ("checkbox", "toggle", "bool", "boolean"):
        return value_str.lower() in ("1", "true", "yes", "on")
    return value_str


# ================== AUTO-SYNC STATE ==================
_auto_sync_task: Optional[asyncio.Task] = None
_auto_sync_running: bool = False
_last_ddr_values: Dict[str, Tuple[int, float]] = {}  # DDR num -> (minutes, seconds)
_last_auto_sync_time: Optional[str] = None
_auto_sync_error: Optional[str] = None


async def _auto_sync_loop():
    """Background task that polls TriCaster and syncs changed DDR durations to Singular."""
    global _auto_sync_running, _last_ddr_values, _last_auto_sync_time, _auto_sync_error
    _auto_sync_running = True
    _auto_sync_error = None
    logger.info("[AUTO-SYNC] Started with interval %ds", CONFIG.tricaster_auto_sync_interval)

    while _auto_sync_running and CONFIG.tricaster_auto_sync:
        try:
            # Only sync if we have the required config
            if not CONFIG.tricaster_host or not CONFIG.tricaster_singular_token:
                await asyncio.sleep(CONFIG.tricaster_auto_sync_interval)
                continue

            # Get current DDR durations from TriCaster
            for ddr_num_str, fields in CONFIG.tricaster_timer_fields.items():
                if not fields.get("min") or not fields.get("sec"):
                    continue  # Skip DDRs without field mappings

                try:
                    ddr_num = int(ddr_num_str)
                    duration, fps = _get_ddr_duration_and_fps(ddr_num)
                    if duration is None:
                        continue

                    mins, secs = _split_minutes_seconds(duration, fps)
                    current_val = (mins, round(secs, 2))  # Round for comparison

                    # Only sync if value changed
                    if _last_ddr_values.get(ddr_num_str) != current_val:
                        _last_ddr_values[ddr_num_str] = current_val
                        # Sync to Singular using existing function
                        sync_ddr_to_singular(ddr_num)
                        _last_auto_sync_time = datetime.now().strftime("%H:%M:%S")
                        logger.info("[AUTO-SYNC] DDR %d synced: %dm %.2fs", ddr_num, mins, secs)

                except HTTPException as e:
                    logger.debug("[AUTO-SYNC] DDR %s: %s", ddr_num_str, e.detail)
                except Exception as e:
                    logger.debug("[AUTO-SYNC] DDR %s error: %s", ddr_num_str, e)

            _auto_sync_error = None

        except Exception as e:
            _auto_sync_error = str(e)
            logger.warning("[AUTO-SYNC] Error: %s", e)

        await asyncio.sleep(CONFIG.tricaster_auto_sync_interval)

    _auto_sync_running = False
    logger.info("[AUTO-SYNC] Stopped")


def start_auto_sync():
    """Start the auto-sync background task."""
    global _auto_sync_task, _auto_sync_running
    if _auto_sync_running:
        return  # Already running

    _auto_sync_running = True
    loop = asyncio.get_event_loop()
    _auto_sync_task = loop.create_task(_auto_sync_loop())


def stop_auto_sync():
    """Stop the auto-sync background task."""
    global _auto_sync_running, _auto_sync_task
    _auto_sync_running = False
    if _auto_sync_task:
        _auto_sync_task.cancel()
        _auto_sync_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if CONFIG.singular_tokens:
            build_registry()
    except Exception as e:
        logger.warning("[WARN] Registry build failed: %s", e)

    # Start auto-sync if enabled in config
    if CONFIG.tricaster_auto_sync:
        asyncio.create_task(_auto_sync_loop())

    yield

    # Stop auto-sync on shutdown
    stop_auto_sync()

app.router.lifespan_context = lifespan

# ================== 4. Pydantic models ==================

class SingularConfigIn(BaseModel):
    token: str

class TflConfigIn(BaseModel):
    app_id: str
    app_key: str

class StreamConfigIn(BaseModel):
    stream_url: str

class SettingsIn(BaseModel):
    port: Optional[int] = None
    enable_tfl: bool = False
    theme: Optional[str] = "dark"

class SingularItem(BaseModel):
    subCompositionId: str
    state: Optional[str] = None
    payload: Optional[dict] = None


# ================== 5. HTML helpers ==================

def _nav_html(active: str = "") -> str:
    pages = [("Home", "/"), ("Commands", "/commands"), ("Modules", "/modules"), ("Settings", "/settings")]
    parts = ['<div class="nav">']
    for name, href in pages:
        cls = ' class="active"' if active.lower() == name.lower() else ''
        parts.append(f'<a href="{href}"{cls}>{name}</a>')
    parts.append('</div>')
    return "".join(parts)


def _base_style() -> str:
    theme = CONFIG.theme or "dark"
    if theme == "light":
        bg = "#f0f2f5"; fg = "#1a1a2e"; card_bg = "#ffffff"; border = "#e0e0e0"; accent = "#00bcd4"
        accent_hover = "#0097a7"; text_muted = "#666666"; input_bg = "#fafafa"
    else:
        # Modern dark theme - matched to desktop GUI colours
        bg = "#1a1a1a"; fg = "#ffffff"; card_bg = "#2d2d2d"; border = "#3d3d3d"; accent = "#00bcd4"
        accent_hover = "#0097a7"; text_muted = "#888888"; input_bg = "#252525"

    lines = []
    lines.append('<link rel="icon" type="image/x-icon" href="/static/favicon.ico">')
    lines.append('<link rel="icon" type="image/png" href="/static/esc_icon.png">')
    lines.append("<style>")
    lines.append("  @font-face {")
    lines.append("    font-family: 'ITVReem';")
    lines.append("    src: url('/static/ITV Reem-Regular.ttf') format('truetype');")
    lines.append("    font-weight: normal;")
    lines.append("    font-style: normal;")
    lines.append("  }")
    lines.append("  * { box-sizing: border-box; }")
    lines.append(
        f"  body {{ font-family: 'ITVReem', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;"
        f" max-width: 900px; margin: 0 auto; background: {bg}; color: {fg}; padding: 20px; line-height: 1.6; }}"
    )
    lines.append(f"  h1 {{ font-size: 28px; font-weight: 700; margin: 20px 0 8px 0; padding-top: 50px; color: {fg}; }}")
    lines.append(f"  h1 + p {{ color: {text_muted}; margin-bottom: 24px; }}")
    lines.append(
        f"  fieldset {{ margin-bottom: 20px; padding: 20px 24px; background: {card_bg}; "
        f"border: 1px solid {border}; border-radius: 12px; }}"
    )
    lines.append(f"  legend {{ font-weight: 600; padding: 0 12px; font-size: 14px; color: {text_muted}; }}")
    lines.append(f"  label {{ display: block; margin-top: 12px; font-size: 14px; color: {text_muted}; }}")
    lines.append(
        f"  input, select {{ width: 100%; padding: 10px 14px; margin-top: 6px; "
        f"background: {input_bg}; color: {fg}; border: 1px solid {border}; border-radius: 8px; "
        f"font-size: 14px; transition: border-color 0.2s, box-shadow 0.2s; }}"
    )
    lines.append(f"  input:focus, select:focus {{ outline: none; border-color: {accent}; box-shadow: 0 0 0 3px {accent}33; }}")
    lines.append(
        f"  button {{ display: inline-flex; align-items: center; justify-content: center; gap: 8px; "
        f"margin-top: 12px; margin-right: 8px; padding: 0 20px; height: 40px; cursor: pointer; "
        f"background: {accent}; color: #fff; border: none; border-radius: 8px; "
        f"font-size: 14px; font-weight: 500; transition: all 0.2s; }}"
    )
    lines.append(f"  button:hover {{ background: {accent_hover}; transform: translateY(-1px); box-shadow: 0 4px 12px {accent}40; }}")
    lines.append(f"  button:active {{ transform: translateY(0); }}")
    # Button variants
    lines.append(f"  button.secondary {{ background: {border}; color: {fg}; }}")
    lines.append(f"  button.secondary:hover {{ background: #4a4a4a; box-shadow: none; transform: none; }}")
    lines.append(f"  button.danger {{ background: #ef4444; }}")
    lines.append(f"  button.danger:hover {{ background: #dc2626; }}")
    lines.append(f"  button.warning {{ background: #f59e0b; color: #000; }}")
    lines.append(f"  button.warning:hover {{ background: #d97706; }}")
    lines.append(f"  button.success {{ background: #22c55e; }}")
    lines.append(f"  button.success:hover {{ background: #16a34a; }}")
    # Button row utility
    lines.append(f"  .btn-row {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 16px; }}")
    lines.append(f"  .btn-row button, .btn-row .status {{ margin: 0 !important; margin-top: 0 !important; margin-right: 0 !important; }}")
    # Status indicator (same height as buttons for alignment)
    lines.append(f"  .status {{ display: inline-flex; align-items: center; justify-content: center; padding: 0 20px; height: 40px; border-radius: 8px; font-size: 14px; font-weight: 500; white-space: nowrap; }}")
    lines.append(f"  .status.idle {{ background: {border}; color: {text_muted}; }}")
    lines.append(f"  .status.success {{ background: #22c55e; color: #fff; }}")
    lines.append(f"  .status.error {{ background: #ef4444; color: #fff; }}")
    lines.append(
        f"  pre {{ background: #000; color: #00bcd4; padding: 16px; white-space: pre-wrap; "
        f"max-height: 250px; overflow: auto; border-radius: 8px; font-size: 13px; "
        f"font-family: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace; border: 1px solid {border}; }}"
    )
    lines.append(
        f"  .nav {{ position: fixed; top: 16px; left: 16px; display: flex; gap: 4px; z-index: 1000; "
        f"background: {card_bg}; padding: 6px; border-radius: 10px; border: 1px solid {accent}40; box-shadow: 0 2px 12px rgba(0,188,212,0.15); }}"
    )
    lines.append(
        f"  .nav a {{ color: {text_muted}; text-decoration: none; padding: 8px 14px; border-radius: 6px; "
        f"font-size: 13px; font-weight: 500; transition: all 0.2s; }}"
    )
    lines.append(f"  .nav a:hover {{ background: {accent}20; color: {accent}; }}")
    lines.append(f"  .nav a.active {{ background: {accent}; color: #fff; }}")
    lines.append(f"  table {{ border-collapse: collapse; width: 100%; margin-top: 12px; border-radius: 8px; overflow: hidden; }}")
    lines.append(f"  th, td {{ border: 1px solid {border}; padding: 10px 14px; font-size: 13px; text-align: left; }}")
    lines.append(f"  th {{ background: {accent}; color: #fff; font-weight: 600; }}")
    lines.append(f"  tr:nth-child(even) td {{ background: {input_bg}; }}")
    lines.append(f"  tr:hover td {{ background: {border}; }}")
    lines.append(
        f"  code {{ font-family: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace; "
        f"background: {input_bg}; padding: 3px 8px; border-radius: 6px; font-size: 12px; "
        f"border: 1px solid {border}; display: inline-block; max-width: 450px; overflow-x: auto; "
        f"white-space: nowrap; vertical-align: middle; }}"
    )
    lines.append(f"  h3 {{ margin-top: 24px; margin-bottom: 8px; font-size: 16px; color: {fg}; }}")
    lines.append(f"  h3 small {{ color: {text_muted}; font-weight: 400; }}")
    lines.append(f"  p {{ margin: 8px 0; }}")
    lines.append(f"  .status-badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 20px; font-size: 13px; }}")
    lines.append(f"  .status-badge.success {{ background: #10b98120; color: #10b981; }}")
    lines.append(f"  .status-badge.error {{ background: #ef444420; color: #ef4444; }}")
    lines.append(f"  .status-badge.warning {{ background: #f59e0b20; color: #f59e0b; }}")
    lines.append(f"  .play-btn {{ display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; "
                 f"background: {accent}; color: #fff; border-radius: 50%; text-decoration: none; font-size: 14px; "
                 f"transition: all 0.2s; }}")
    lines.append(f"  .play-btn:hover {{ background: {accent_hover}; transform: scale(1.1); box-shadow: 0 2px 8px {accent}60; }}")
    lines.append("</style>")
    return "\n".join(lines)


# ================== 6. JSON config endpoints ==================

@app.get("/config")
def get_config():
    total_subs = sum(len(subs) for subs in REGISTRY.values())
    return {
        "singular": {
            "tokens": CONFIG.singular_tokens,
            "token_count": len(CONFIG.singular_tokens),
            "stream_url": CONFIG.singular_stream_url,
        },
        "tfl": {
            "app_id_set": bool(CONFIG.tfl_app_id),
            "app_key_set": bool(CONFIG.tfl_app_key),
        },
        "settings": {
            "port": effective_port(),
            "raw_port": CONFIG.port,
            "enable_tfl": CONFIG.enable_tfl,
            "tfl_auto_refresh": CONFIG.tfl_auto_refresh,
            "theme": CONFIG.theme,
        },
        "registry": {
            "apps": len(REGISTRY),
            "total_subs": total_subs,
        }
    }


class AddTokenIn(BaseModel):
    name: str
    token: str


@app.post("/config/singular/add")
def add_singular_token(cfg: AddTokenIn):
    """Add a new Singular control app token."""
    name = cfg.name.strip()
    token = cfg.token.strip()
    if not name:
        raise HTTPException(400, "App name is required")
    if not token:
        raise HTTPException(400, "Token is required")
    if name in CONFIG.singular_tokens:
        raise HTTPException(400, f"App '{name}' already exists")
    CONFIG.singular_tokens[name] = token
    save_config(CONFIG)
    try:
        count = build_registry_for_app(name, token)
        log_event("Token Added", f"App '{name}': {count} subcompositions")
    except Exception as e:
        raise HTTPException(400, f"Token saved, but registry build failed: {e}")
    total_subs = sum(len(subs) for subs in REGISTRY.values())
    return {"ok": True, "message": f"Added app '{name}'", "subs": total_subs}


@app.post("/config/singular/remove")
def remove_singular_token(name: str = Query(..., description="App name to remove")):
    """Remove a Singular control app token."""
    if name not in CONFIG.singular_tokens:
        raise HTTPException(404, f"App '{name}' not found")
    del CONFIG.singular_tokens[name]
    if name in REGISTRY:
        # Remove from ID_TO_KEY
        for sid, (a, k) in list(ID_TO_KEY.items()):
            if a == name:
                del ID_TO_KEY[sid]
        del REGISTRY[name]
    save_config(CONFIG)
    log_event("Token Removed", f"App '{name}'")
    total_subs = sum(len(subs) for subs in REGISTRY.values())
    return {"ok": True, "message": f"Removed app '{name}'", "subs": total_subs}


@app.post("/config/singular")
def set_singular_config(cfg: SingularConfigIn):
    """Legacy endpoint - adds/updates 'Default' app token."""
    CONFIG.singular_tokens["Default"] = cfg.token
    save_config(CONFIG)
    try:
        build_registry_for_app("Default", cfg.token)
    except Exception as e:
        raise HTTPException(400, f"Token saved, but registry build failed: {e}")
    total_subs = sum(len(subs) for subs in REGISTRY.values())
    return {"ok": True, "message": "Singular token updated", "subs": total_subs}


@app.post("/config/tfl")
def set_tfl_config(cfg: TflConfigIn):
    CONFIG.tfl_app_id = cfg.app_id
    CONFIG.tfl_app_key = cfg.app_key
    save_config(CONFIG)
    return {"ok": True, "message": "TfL config updated"}


@app.post("/config/stream")
def set_stream_config(cfg: StreamConfigIn):
    url = cfg.stream_url.strip()
    # Auto-prefix if user just enters the datastream ID
    if url and not url.startswith("http"):
        url = f"https://datastream.singular.live/datastreams/{url}"
    CONFIG.singular_stream_url = url
    save_config(CONFIG)
    return {"ok": True, "message": "Data Stream URL updated", "url": url}


class ModuleToggleIn(BaseModel):
    enabled: bool


@app.post("/config/module/tfl")
def toggle_tfl_module(cfg: ModuleToggleIn):
    CONFIG.enable_tfl = cfg.enabled
    if not cfg.enabled:
        CONFIG.tfl_auto_refresh = False  # Disable auto-refresh when module is disabled
    save_config(CONFIG)
    return {"ok": True, "enabled": CONFIG.enable_tfl}


@app.post("/config/module/tfl/auto-refresh")
def toggle_tfl_auto_refresh(cfg: ModuleToggleIn):
    CONFIG.tfl_auto_refresh = cfg.enabled
    save_config(CONFIG)
    return {"ok": True, "enabled": CONFIG.tfl_auto_refresh}


# ================== TRICASTER MODULE ENDPOINTS ==================

class TriCasterConfigIn(BaseModel):
    host: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None


@app.post("/config/module/tricaster")
def toggle_tricaster_module(cfg: ModuleToggleIn):
    CONFIG.enable_tricaster = cfg.enabled
    save_config(CONFIG)
    return {"ok": True, "enabled": CONFIG.enable_tricaster}


@app.post("/config/tricaster")
def save_tricaster_config(cfg: TriCasterConfigIn):
    if cfg.host is not None:
        CONFIG.tricaster_host = cfg.host if cfg.host else None
    if cfg.user is not None:
        CONFIG.tricaster_user = cfg.user or "admin"
    if cfg.password is not None:
        CONFIG.tricaster_pass = cfg.password if cfg.password else None
    save_config(CONFIG)
    return {"ok": True, "host": CONFIG.tricaster_host}


@app.get("/tricaster/test")
def tricaster_test():
    """Test connection to TriCaster."""
    return tricaster_test_connection()


@app.get("/tricaster/ddr")
def tricaster_ddr():
    """Get DDR status from TriCaster."""
    return tricaster_get_ddr_info()


@app.get("/tricaster/tally")
def tricaster_tally():
    """Get tally status from TriCaster."""
    return tricaster_get_tally()


@app.get("/tricaster/dictionary/{key}")
def tricaster_dictionary(key: str):
    """Get raw dictionary data from TriCaster."""
    return tricaster_get_dictionary(key)


@app.post("/tricaster/shortcut/{name}")
def tricaster_exec_shortcut(name: str, value: Optional[str] = None, index: Optional[int] = None):
    """Execute a TriCaster shortcut command."""
    params = {}
    if value is not None:
        params["value"] = str(value)
    if index is not None:
        params["index"] = str(index)
    return tricaster_shortcut(name, params if params else None)


@app.get("/tricaster/shortcut/{name}")
def tricaster_exec_shortcut_get(name: str, value: Optional[str] = None, index: Optional[int] = None):
    """Execute a TriCaster shortcut command (GET for easy triggering)."""
    params = {}
    if value is not None:
        params["value"] = str(value)
    if index is not None:
        params["index"] = str(index)
    return tricaster_shortcut(name, params if params else None)


# Common TriCaster shortcuts as direct endpoints
@app.get("/tricaster/record/start")
def tricaster_record_start():
    return tricaster_shortcut("record_start")


@app.get("/tricaster/record/stop")
def tricaster_record_stop():
    return tricaster_shortcut("record_stop")


@app.get("/tricaster/record/toggle")
def tricaster_record_toggle():
    return tricaster_shortcut("record_toggle")


@app.get("/tricaster/streaming/start")
def tricaster_streaming_start():
    return tricaster_shortcut("streaming_start")


@app.get("/tricaster/streaming/stop")
def tricaster_streaming_stop():
    return tricaster_shortcut("streaming_stop")


@app.get("/tricaster/streaming/toggle")
def tricaster_streaming_toggle():
    return tricaster_shortcut("streaming_toggle")


@app.get("/tricaster/main/auto")
def tricaster_main_auto():
    return tricaster_shortcut("main_auto")


@app.get("/tricaster/main/take")
def tricaster_main_take():
    return tricaster_shortcut("main_take")


@app.get("/tricaster/ddr/{ddr_num}/play")
def tricaster_ddr_play(ddr_num: int):
    return tricaster_shortcut(f"ddr{ddr_num}_play")


@app.get("/tricaster/ddr/{ddr_num}/stop")
def tricaster_ddr_stop(ddr_num: int):
    return tricaster_shortcut(f"ddr{ddr_num}_stop")


@app.get("/tricaster/macro/{macro_name}")
def tricaster_macro_by_name(macro_name: str):
    return tricaster_shortcut("play_macro_byname", {"value": macro_name})


# ─────────────────────────────────────────────────────────────────────────────
# DDR-to-Singular Timer Sync Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TimerSyncConfigIn(BaseModel):
    singular_token: Optional[str] = None
    round_mode: str = "frames"
    timer_fields: Dict[str, Dict[str, str]] = {}  # {"1": {"min": "...", "sec": "...", "timer": "..."}}


@app.post("/config/tricaster/timer-sync")
def save_timer_sync_config(cfg: TimerSyncConfigIn):
    """Save DDR-to-Singular timer sync configuration."""
    CONFIG.tricaster_singular_token = cfg.singular_token
    CONFIG.tricaster_round_mode = cfg.round_mode
    CONFIG.tricaster_timer_fields = cfg.timer_fields
    save_config(CONFIG)
    # Clear the field map cache when config changes
    _singular_field_map_cache.clear()
    return {"ok": True, "message": "Timer sync configuration saved"}


@app.get("/config/tricaster/timer-sync")
def get_timer_sync_config():
    """Get current DDR-to-Singular timer sync configuration."""
    return {
        "singular_token": CONFIG.tricaster_singular_token,
        "round_mode": CONFIG.tricaster_round_mode,
        "timer_fields": CONFIG.tricaster_timer_fields,
    }


@app.get("/api/singular/apps")
def get_singular_apps():
    """Get list of configured Singular apps (name → token)."""
    return {"apps": CONFIG.singular_tokens}


@app.get("/api/singular/fields/{app_name}")
def get_singular_fields(app_name: str):
    """Get all field IDs for a given Singular app."""
    if app_name not in REGISTRY:
        # Try to build registry if not yet built
        if app_name in CONFIG.singular_tokens:
            build_registry_for_app(app_name, CONFIG.singular_tokens[app_name])

    if app_name not in REGISTRY:
        raise HTTPException(404, f"App '{app_name}' not found")

    fields = []
    for key, sub in REGISTRY[app_name].items():
        sub_name = sub.get("name", key)
        for field_id, field_meta in sub.get("fields", {}).items():
            if field_id:  # Skip empty field IDs
                field_name = field_meta.get("title") or field_meta.get("name") or field_id
                fields.append({
                    "id": field_id,
                    "name": field_name,
                    "subcomposition": sub_name,
                    "type": field_meta.get("type", "unknown")
                })

    # Sort by subcomposition then field name
    fields.sort(key=lambda f: (f["subcomposition"], f["name"]))
    return {"fields": fields, "count": len(fields)}


@app.get("/tricaster/sync/all")
def sync_all_ddrs_endpoint():
    """Sync all configured DDRs to their Singular timer fields."""
    try:
        return sync_all_ddrs_to_singular()
    except Exception as e:
        logger.error("DDR sync all failed: %s", e)
        raise HTTPException(500, f"DDR sync all failed: {str(e)}")


@app.get("/tricaster/sync/{ddr_num}")
def sync_ddr_endpoint(ddr_num: int):
    """Sync a single DDR's duration to its Singular timer fields."""
    try:
        return sync_ddr_to_singular(ddr_num)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("DDR sync failed: %s", e)
        raise HTTPException(500, f"DDR sync failed: {str(e)}")


@app.get("/tricaster/timer/{ddr_num}/start")
def timer_start_endpoint(ddr_num: int):
    """Start the Singular timer for a DDR."""
    try:
        return send_timer_command(ddr_num, "start")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Timer start failed: {str(e)}")


@app.get("/tricaster/timer/{ddr_num}/pause")
def timer_pause_endpoint(ddr_num: int):
    """Pause the Singular timer for a DDR."""
    try:
        return send_timer_command(ddr_num, "pause")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Timer pause failed: {str(e)}")


@app.get("/tricaster/timer/{ddr_num}/reset")
def timer_reset_endpoint(ddr_num: int):
    """Reset the Singular timer for a DDR."""
    try:
        return send_timer_command(ddr_num, "reset")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Timer reset failed: {str(e)}")


@app.get("/tricaster/timer/{ddr_num}/restart")
def timer_restart_endpoint(ddr_num: int):
    """Restart the Singular timer for a DDR (pause + reset, no auto-start)."""
    try:
        return restart_timer(ddr_num)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Timer restart failed: {str(e)}")


@app.get("/tricaster/timer/all/restart")
def timer_restart_all_endpoint():
    """Restart all configured Singular timers."""
    results = []
    errors = []
    for ddr_key in CONFIG.tricaster_timer_fields.keys():
        try:
            ddr_num = int(ddr_key)
            result = restart_timer(ddr_num)
            results.append(result)
        except Exception as e:
            errors.append(f"DDR {ddr_key}: {str(e)}")
    return {"ok": len(errors) == 0, "results": results, "errors": errors if errors else None}


# ================== AUTO-SYNC ENDPOINTS ==================

class AutoSyncConfigIn(BaseModel):
    enabled: bool
    interval: Optional[int] = None  # 2-10 seconds


@app.get("/tricaster/auto-sync/status")
def get_auto_sync_status():
    """Get current auto-sync status and configuration."""
    return {
        "enabled": CONFIG.tricaster_auto_sync,
        "running": _auto_sync_running,
        "interval": CONFIG.tricaster_auto_sync_interval,
        "last_sync": _last_auto_sync_time,
        "error": _auto_sync_error,
        "cached_values": {k: {"minutes": v[0], "seconds": v[1]} for k, v in _last_ddr_values.items()},
    }


@app.post("/tricaster/auto-sync")
async def set_auto_sync(config: AutoSyncConfigIn):
    """Enable or disable auto-sync and configure interval."""
    global _auto_sync_running

    # Update interval if provided (clamp to 2-10 seconds)
    if config.interval is not None:
        CONFIG.tricaster_auto_sync_interval = max(2, min(10, config.interval))

    # Update enabled state
    CONFIG.tricaster_auto_sync = config.enabled
    save_config(CONFIG)

    if config.enabled and not _auto_sync_running:
        # Start auto-sync
        asyncio.create_task(_auto_sync_loop())
        return {
            "ok": True,
            "message": "Auto-sync started",
            "interval": CONFIG.tricaster_auto_sync_interval,
        }
    elif not config.enabled and _auto_sync_running:
        # Stop auto-sync
        stop_auto_sync()
        return {"ok": True, "message": "Auto-sync stopped"}
    else:
        return {
            "ok": True,
            "message": "Auto-sync " + ("enabled" if config.enabled else "disabled"),
            "interval": CONFIG.tricaster_auto_sync_interval,
        }


@app.get("/settings/json")
def get_settings_json():
    return {
        "port": effective_port(),
        "raw_port": CONFIG.port,
        "enable_tfl": CONFIG.enable_tfl,
        "tfl_auto_refresh": CONFIG.tfl_auto_refresh,
        "config_path": str(CONFIG_PATH),
        "theme": CONFIG.theme,
    }


@app.get("/version/check")
def check_version():
    """Check for updates against GitHub releases."""
    current = _runtime_version()
    try:
        resp = requests.get(
            "https://api.github.com/repos/BlueElliott/Singular-Tweaks/releases/latest",
            timeout=5
        )
        if resp.status_code == 404:
            return {
                "current": current,
                "latest": None,
                "up_to_date": True,
                "message": "Repository is private or has no public releases",
            }
        resp.raise_for_status()
        data = resp.json()
        latest = data.get("tag_name", "unknown")
        release_url = data.get("html_url", "")

        # Normalize versions for comparison (remove 'v' prefix if present)
        current_normalized = current.lstrip('v')
        latest_normalized = latest.lstrip('v')
        up_to_date = current_normalized == latest_normalized

        return {
            "current": current,
            "latest": latest,
            "up_to_date": up_to_date,
            "release_url": release_url,
            "message": "You are up to date" if up_to_date else "A newer version is available",
        }
    except requests.RequestException as e:
        logger.error("Version check failed: %s", e)
        return {
            "current": current,
            "latest": None,
            "up_to_date": True,
            "message": f"Version check failed: {str(e)}",
        }


@app.post("/settings")
def update_settings(settings: SettingsIn):
    CONFIG.enable_tfl = settings.enable_tfl
    # Only update port if provided (port config moved to GUI launcher)
    if settings.port is not None:
        CONFIG.port = settings.port
    CONFIG.theme = (settings.theme or "dark")
    save_config(CONFIG)
    return {
        "ok": True,
        "message": "Settings updated.",
        "port": effective_port(),
        "enable_tfl": CONFIG.enable_tfl,
        "theme": CONFIG.theme,
    }


@app.get("/config/export")
def export_config():
    """Export current configuration as JSON for backup."""
    return CONFIG.model_dump()


@app.post("/config/import")
def import_config(config_data: Dict[str, Any]):
    """Import configuration from JSON backup."""
    try:
        # Update CONFIG with imported data
        if "singular_token" in config_data:
            CONFIG.singular_token = config_data["singular_token"]
        if "singular_stream_url" in config_data:
            CONFIG.singular_stream_url = config_data["singular_stream_url"]
        if "tfl_app_id" in config_data:
            CONFIG.tfl_app_id = config_data["tfl_app_id"]
        if "tfl_app_key" in config_data:
            CONFIG.tfl_app_key = config_data["tfl_app_key"]
        if "enable_tfl" in config_data:
            CONFIG.enable_tfl = config_data["enable_tfl"]
        if "tfl_auto_refresh" in config_data:
            CONFIG.tfl_auto_refresh = config_data["tfl_auto_refresh"]
        if "theme" in config_data:
            CONFIG.theme = config_data["theme"]
        if "port" in config_data:
            CONFIG.port = config_data["port"]

        # Save to file
        save_config(CONFIG)

        return {
            "ok": True,
            "message": "Configuration imported successfully. Restart app to apply changes.",
        }
    except Exception as e:
        logger.error("Failed to import config: %s", e)
        raise HTTPException(400, f"Failed to import config: {str(e)}")


@app.get("/events")
def get_events():
    return {"events": COMMAND_LOG[-100:]}


@app.get("/singular/ping")
def singular_ping(app_name: Optional[str] = Query(None, description="App name to ping (optional, pings all if not specified)")):
    """Ping Singular to verify connectivity. Can ping specific app or all apps."""
    if not CONFIG.singular_tokens:
        raise HTTPException(400, "No Singular tokens configured")

    results = {}
    total_subs = 0

    apps_to_ping = {app_name: CONFIG.singular_tokens[app_name]} if app_name and app_name in CONFIG.singular_tokens else CONFIG.singular_tokens

    for name, token in apps_to_ping.items():
        try:
            data = singular_model_fetch(token)
            subs = len(REGISTRY.get(name, {}))
            total_subs += subs
            results[name] = {"ok": True, "subs": subs}
        except Exception as e:
            results[name] = {"ok": False, "error": str(e)}

    all_ok = all(r["ok"] for r in results.values())
    return {
        "ok": all_ok,
        "message": "Connected to Singular" if all_ok else "Some connections failed",
        "apps": results,
        "total_subs": total_subs,
    }


# ================== 7. TfL / DataStream endpoints ==================

@app.get("/health")
def health():
    return {"status": "ok", "version": _runtime_version(), "port": effective_port()}


@app.get("/status")
def status_preview():
    try:
        data = fetch_all_line_statuses()
        log_event("TfL status", f"{len(data)} lines")
        return data
    except Exception as e:
        raise HTTPException(500, str(e))


@app.api_route("/update", methods=["GET", "POST"])
def update_status():
    try:
        data = fetch_all_line_statuses()
        result = send_to_datastream(data)
        log_event("DataStream update", "Sent TfL payload")
        return {"sent_to": "datastream", "payload": data, **result}
    except Exception as e:
        raise HTTPException(500, f"Update failed: {e}")


@app.api_route("/test", methods=["GET", "POST"])
def update_test():
    try:
        keys = list(fetch_all_line_statuses().keys())
        payload = {k: "TEST" for k in keys}
        result = send_to_datastream(payload)
        log_event("DataStream test", "Sent TEST payload")
        return {"sent_to": "datastream", "payload": payload, **result}
    except Exception as e:
        raise HTTPException(500, f"Test failed: {e}")


@app.api_route("/blank", methods=["GET", "POST"])
def update_blank():
    try:
        keys = list(fetch_all_line_statuses().keys())
        payload = {k: "" for k in keys}
        result = send_to_datastream(payload)
        log_event("DataStream blank", "Sent blank payload")
        return {"sent_to": "datastream", "payload": payload, **result}
    except Exception as e:
        raise HTTPException(500, f"Blank failed: {e}")


@app.get("/tfl/lines")
def get_tfl_lines():
    """Return list of all TFL lines for the manual input UI."""
    return {"lines": TFL_LINES}


@app.post("/manual")
def send_manual(payload: Dict[str, str]):
    """Send a manual payload to the datastream."""
    try:
        result = send_to_datastream(payload)
        log_event("DataStream manual", f"Sent manual payload with {len(payload)} lines")
        return {"sent_to": "datastream", "payload": payload, **result}
    except Exception as e:
        raise HTTPException(500, f"Manual send failed: {e}")


# ================== 8. Control app endpoints ==================

@app.post("/singular/control")
def singular_control(items: List[SingularItem], app_name: Optional[str] = Query(None, description="App name to send to")):
    # If app_name not specified, use first available token
    if app_name and app_name in CONFIG.singular_tokens:
        token = CONFIG.singular_tokens[app_name]
    elif CONFIG.singular_tokens:
        token = list(CONFIG.singular_tokens.values())[0]
    else:
        raise HTTPException(400, "No Singular control app tokens configured")
    r = ctrl_patch([i.dict(exclude_none=True) for i in items], token)
    return {"status": r.status_code, "response": r.text}


@app.get("/singular/list")
def singular_list():
    result = {}
    for app_name, subs in REGISTRY.items():
        for k, v in subs.items():
            result[f"{app_name}/{k}"] = {
                "id": v["id"],
                "name": v["name"],
                "app": app_name,
                "fields": list(v["fields"].keys())
            }
    return result


@app.post("/singular/refresh")
def singular_refresh():
    build_registry()
    total = sum(len(subs) for subs in REGISTRY.values())
    return {"ok": True, "count": total, "apps": len(REGISTRY)}


def _field_examples(base: str, key: str, field_id: str, field_meta: dict):
    ftype = (field_meta.get("type") or "").lower()
    examples: Dict[str, str] = {}
    set_url = f"{base}/{key}/set?field={quote(field_id)}&value=VALUE"
    examples["set_url"] = set_url
    if ftype == "timecontrol":
        start = f"{base}/{key}/timecontrol?field={quote(field_id)}&run=true&value=0"
        stop = f"{base}/{key}/timecontrol?field={quote(field_id)}&run=false&value=0"
        examples["timecontrol_start_url"] = start
        examples["timecontrol_stop_url"] = stop
        examples["start_10s_if_supported"] = (
            f"{base}/{key}/timecontrol?field={quote(field_id)}&run=true&value=0&seconds=10"
        )
    return examples


@app.get("/singular/commands")
def singular_commands(request: Request):
    base = _base_url(request)
    catalog: Dict[str, Any] = {}
    for app_name, subs in REGISTRY.items():
        for key, meta in subs.items():
            # Use app_name/key format for unique identification
            full_key = f"{app_name}/{key}"
            sid = meta["id"]
            entry: Dict[str, Any] = {
                "id": sid,
                "name": meta["name"],
                "app_name": app_name,
                "in_url": f"{base}/{app_name}/{key}/in",
                "out_url": f"{base}/{app_name}/{key}/out",
                "fields": {},
            }
            for fid, fmeta in meta["fields"].items():
                if not fid:
                    continue
                entry["fields"][fid] = _field_examples(base, f"{app_name}/{key}", fid, fmeta)
            catalog[full_key] = entry
    return {
        "note": "Most control endpoints support GET for testing, but POST is recommended in automation.",
        "catalog": catalog,
    }


@app.get("/{app_name}/{key}/help")
def singular_commands_for_one(app_name: str, key: str, request: Request):
    found_app, k = kfind(key, app_name)
    base = _base_url(request)
    meta = REGISTRY[found_app][k]
    sid = meta["id"]
    entry: Dict[str, Any] = {
        "id": sid,
        "name": meta["name"],
        "app_name": found_app,
        "in_url": f"{base}/{found_app}/{k}/in",
        "out_url": f"{base}/{found_app}/{k}/out",
        "fields": {},
    }
    for fid, fmeta in meta["fields"].items():
        if not fid:
            continue
        entry["fields"][fid] = _field_examples(base, f"{found_app}/{k}", fid, fmeta)
    return {"commands": entry}


@app.api_route("/{app_name}/{key}/in", methods=["GET", "POST"])
def sub_in(app_name: str, key: str):
    found_app, k = kfind(key, app_name)
    meta = REGISTRY[found_app][k]
    sid = meta["id"]
    token = meta["token"]
    r = ctrl_patch([{"subCompositionId": sid, "state": "In"}], token)
    log_event("IN", f"{found_app}/{k} ({sid})")
    return {"status": r.status_code, "id": sid, "app": found_app, "response": r.text}


@app.api_route("/{app_name}/{key}/out", methods=["GET", "POST"])
def sub_out(app_name: str, key: str):
    found_app, k = kfind(key, app_name)
    meta = REGISTRY[found_app][k]
    sid = meta["id"]
    token = meta["token"]
    r = ctrl_patch([{"subCompositionId": sid, "state": "Out"}], token)
    log_event("OUT", f"{found_app}/{k} ({sid})")
    return {"status": r.status_code, "id": sid, "app": found_app, "response": r.text}


@app.api_route("/{app_name}/{key}/set", methods=["GET", "POST"])
def sub_set(
    app_name: str,
    key: str,
    field: str = Query(..., description="Field id as shown in /singular/list"),
    value: str = Query(..., description="Value to set"),
    asString: int = Query(0, description="Send value strictly as string if 1"),
):
    found_app, k = kfind(key, app_name)
    meta = REGISTRY[found_app][k]
    sid = meta["id"]
    token = meta["token"]
    fields = meta["fields"]
    if field not in fields:
        raise HTTPException(404, f"Field not found on {found_app}/{k}: {field}")
    v = coerce_value(fields[field], value, as_string=bool(asString))
    patch = [{"subCompositionId": sid, "payload": {field: v}}]
    r = ctrl_patch(patch, token)
    log_event("SET", f"{found_app}/{k} ({sid}) field={field} value={value}")
    return {"status": r.status_code, "id": sid, "app": found_app, "sent": patch, "response": r.text}


@app.api_route("/{app_name}/{key}/timecontrol", methods=["GET", "POST"])
def sub_timecontrol(
    app_name: str,
    key: str,
    field: str = Query(..., description="timecontrol field id"),
    run: bool = Query(True, description="True=start, False=stop"),
    value: int = Query(0, description="usually 0"),
    utc: Optional[float] = Query(None, description="override UTC ms; default now()"),
    seconds: Optional[int] = Query(None, description="optional duration for countdowns"),
):
    found_app, k = kfind(key, app_name)
    meta = REGISTRY[found_app][k]
    sid = meta["id"]
    token = meta["token"]
    fields = meta["fields"]
    if field not in fields:
        raise HTTPException(404, f"Field not found on {found_app}/{k}: {field}")
    if (fields[field].get("type") or "").lower() != "timecontrol":
        raise HTTPException(400, f"Field '{field}' is not a timecontrol")
    payload: Dict[str, Any] = {}
    if seconds is not None:
        payload["Countdown Seconds"] = str(seconds)
    payload[field] = {
        "UTC": float(utc if utc is not None else now_ms_float()),
        "isRunning": bool(run),
        "value": int(value),
    }
    r = ctrl_patch([{"subCompositionId": sid, "payload": payload}], token)
    log_event("TIMECONTROL", f"{found_app}/{k} ({sid}) field={field} run={run} seconds={seconds}")
    return {"status": r.status_code, "id": sid, "app": found_app, "sent": payload, "response": r.text}


# ================== 9. HTML Pages ==================

@app.get("/", response_class=HTMLResponse)
def index():
    """Home page - completely rewritten with simple, reliable JS using XMLHttpRequest."""
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html><head>")
    parts.append("<title>Elliott's Singular Controls v" + _runtime_version() + "</title>")
    parts.append(_base_style())
    parts.append("<style>")
    parts.append("  .app-list { margin: 12px 0; }")
    parts.append("  .app-item { display: flex; align-items: center; gap: 8px; padding: 12px; background: #1a1a1a; border: 1px solid #3d3d3d; border-radius: 8px; margin-bottom: 8px; }")
    parts.append("  .app-item .app-name { font-weight: 600; font-size: 14px; min-width: 70px; }")
    parts.append("  .app-item .app-token { flex: 1; font-family: 'SF Mono', Monaco, Consolas, monospace; font-size: 11px; color: #888; background: #252525; padding: 0 12px; height: 32px; line-height: 32px; border-radius: 6px; border: 1px solid #3d3d3d; overflow-x: auto; white-space: nowrap; }")
    parts.append("  .app-item .app-actions { display: flex; align-items: center; gap: 8px; margin-left: auto; flex-shrink: 0; }")
    parts.append("  .app-item .app-status { height: 32px; min-width: 75px; padding: 0 10px; border-radius: 6px; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; justify-content: center; }")
    parts.append("  .app-item .app-status.ok { background: #22c55e; color: #fff; }")
    parts.append("  .app-item .app-status.error { background: #ef4444; color: #fff; }")
    parts.append("  .app-item .app-status.checking { background: #f59e0b; color: #000; }")
    parts.append("  .app-item button { height: 32px; padding: 0 14px; font-size: 12px; margin: 0 !important; }")
    parts.append("  .add-app-form { display: flex; gap: 8px; align-items: flex-end; margin-top: 16px; padding-top: 16px; border-top: 1px solid #3d3d3d; }")
    parts.append("  .add-app-form label { margin: 0; font-size: 12px; }")
    parts.append("  .add-app-form input { margin-top: 4px; height: 32px; }")
    parts.append("  .add-app-form button { height: 32px; margin: 0 !important; }")
    parts.append("</style>")
    parts.append("</head><body>")
    parts.append(_nav_html("Home"))
    parts.append("<h1>Elliott's Singular Controls</h1>")
    parts.append("<p>Mainly used to send <strong>GET</strong> and simple HTTP commands to your Singular Control App.</p>")
    # Multiple tokens management
    parts.append('<fieldset><legend>Singular Control Apps</legend>')
    parts.append('<p style="color: #8b949e; margin-bottom: 16px;">Manage multiple Singular control app tokens. Each app can have its own subcompositions.</p>')
    parts.append('<div id="app-list" class="app-list"><p style="color: #888;">Loading...</p></div>')
    parts.append('<div class="add-app-form">')
    parts.append('<label>App Name <input type="text" id="new-app-name" placeholder="e.g. Main Show" style="width: 150px;" /></label>')
    parts.append('<label style="flex: 1;">Token <input type="text" id="new-app-token" placeholder="Paste Control App Token" style="width: 100%;" /></label>')
    parts.append('<button type="button" id="btn-add">Add App</button>')
    parts.append('<button type="button" id="btn-ping-all" class="secondary">Ping All</button>')
    parts.append('</div>')
    parts.append('</fieldset>')
    parts.append('<fieldset><legend>Event Log</legend>')
    parts.append("<p>Shows recent HTTP commands and updates triggered by this tool.</p>")
    parts.append('<button type="button" id="btn-refresh-log">Refresh Log</button>')
    parts.append('<pre id="log">No events yet.</pre>')
    parts.append("</fieldset>")

    # Completely rewritten JS - inline script at end of body for simplicity
    parts.append("<script>")
    # Global variables
    parts.append("var CONFIG = null;")
    parts.append("")
    # XHR helper - simplest possible
    parts.append("function xhr(method, url, data, callback) {")
    parts.append("  var req = new XMLHttpRequest();")
    parts.append("  req.open(method, url, true);")
    parts.append("  req.onload = function() {")
    parts.append("    var json = null;")
    parts.append("    try { json = JSON.parse(req.responseText); } catch(e) {}")
    parts.append("    callback(req.status, json);")
    parts.append("  };")
    parts.append("  req.onerror = function() { callback(0, null); };")
    parts.append("  if (data) {")
    parts.append("    req.setRequestHeader('Content-Type', 'application/json');")
    parts.append("    req.send(JSON.stringify(data));")
    parts.append("  } else {")
    parts.append("    req.send();")
    parts.append("  }")
    parts.append("}")
    parts.append("")
    # Render apps
    parts.append("function renderApps() {")
    parts.append("  var container = document.getElementById('app-list');")
    parts.append("  if (!CONFIG || !CONFIG.singular || !CONFIG.singular.tokens) {")
    parts.append("    container.innerHTML = '<p style=\"color: #888;\">No apps configured. Add one below.</p>';")
    parts.append("    return;")
    parts.append("  }")
    parts.append("  var tokens = CONFIG.singular.tokens;")
    parts.append("  var names = Object.keys(tokens);")
    parts.append("  if (names.length === 0) {")
    parts.append("    container.innerHTML = '<p style=\"color: #888;\">No apps configured. Add one below.</p>';")
    parts.append("    return;")
    parts.append("  }")
    parts.append("  var html = '';")
    parts.append("  for (var i = 0; i < names.length; i++) {")
    parts.append("    var name = names[i];")
    parts.append("    var token = tokens[name];")
    parts.append("    var shortToken = token.length > 40 ? token.substring(0, 40) + '...' : token;")
    parts.append("    html += '<div class=\"app-item\">';")
    parts.append("    html += '<span class=\"app-name\">' + name + '</span>';")
    parts.append("    html += '<span class=\"app-token\">' + shortToken + '</span>';")
    parts.append("    html += '<div class=\"app-actions\">';")
    parts.append("    html += '<span class=\"app-status checking\" id=\"status-' + name + '\">...</span>';")
    parts.append("    html += '<button onclick=\"pingApp(\\'' + name + '\\')\">Ping</button>';")
    parts.append("    html += '<button class=\"danger\" onclick=\"removeApp(\\'' + name + '\\')\">Remove</button>';")
    parts.append("    html += '</div>';")
    parts.append("    html += '</div>';")
    parts.append("  }")
    parts.append("  container.innerHTML = html;")
    parts.append("}")
    parts.append("")
    # Load config
    parts.append("function loadConfig(callback) {")
    parts.append("  xhr('GET', '/config', null, function(status, data) {")
    parts.append("    if (status === 200 && data) {")
    parts.append("      CONFIG = data;")
    parts.append("      renderApps();")
    parts.append("    }")
    parts.append("    if (callback) callback();")
    parts.append("  });")
    parts.append("}")
    parts.append("")
    # Ping single app
    parts.append("function pingApp(name) {")
    parts.append("  var el = document.getElementById('status-' + name);")
    parts.append("  if (!el) return;")
    parts.append("  el.textContent = '...';")
    parts.append("  el.className = 'app-status checking';")
    parts.append("  xhr('GET', '/singular/ping?app_name=' + encodeURIComponent(name), null, function(status, data) {")
    parts.append("    if (status === 200 && data && data.ok && data.apps && data.apps[name] && data.apps[name].ok) {")
    parts.append("      el.textContent = data.apps[name].subs + ' subs';")
    parts.append("      el.className = 'app-status ok';")
    parts.append("    } else {")
    parts.append("      el.textContent = 'Error';")
    parts.append("      el.className = 'app-status error';")
    parts.append("    }")
    parts.append("  });")
    parts.append("}")
    parts.append("")
    # Ping all
    parts.append("function pingAll() {")
    parts.append("  if (!CONFIG || !CONFIG.singular || !CONFIG.singular.tokens) return;")
    parts.append("  var names = Object.keys(CONFIG.singular.tokens);")
    parts.append("  for (var i = 0; i < names.length; i++) {")
    parts.append("    pingApp(names[i]);")
    parts.append("  }")
    parts.append("}")
    parts.append("")
    # Add app
    parts.append("function addApp() {")
    parts.append("  var nameEl = document.getElementById('new-app-name');")
    parts.append("  var tokenEl = document.getElementById('new-app-token');")
    parts.append("  var name = nameEl.value.trim();")
    parts.append("  var token = tokenEl.value.trim();")
    parts.append("  if (!name) { alert('Please enter an app name.'); return; }")
    parts.append("  if (!token) { alert('Please enter a token.'); return; }")
    parts.append("  xhr('POST', '/config/singular/add', { name: name, token: token }, function(status, data) {")
    parts.append("    if (status === 200) {")
    parts.append("      nameEl.value = '';")
    parts.append("      tokenEl.value = '';")
    parts.append("      loadConfig(function() { pingApp(name); });")
    parts.append("    } else {")
    parts.append("      alert((data && data.detail) || 'Failed to add app');")
    parts.append("    }")
    parts.append("  });")
    parts.append("}")
    parts.append("")
    # Remove app
    parts.append("function removeApp(name) {")
    parts.append("  if (!confirm('Remove app \"' + name + '\"?')) return;")
    parts.append("  xhr('POST', '/config/singular/remove?name=' + encodeURIComponent(name), null, function(status) {")
    parts.append("    if (status === 200) {")
    parts.append("      loadConfig();")
    parts.append("    } else {")
    parts.append("      alert('Failed to remove app');")
    parts.append("    }")
    parts.append("  });")
    parts.append("}")
    parts.append("")
    # Load events
    parts.append("function loadEvents() {")
    parts.append("  xhr('GET', '/events', null, function(status, data) {")
    parts.append("    var el = document.getElementById('log');")
    parts.append("    if (status === 200 && data && data.events) {")
    parts.append("      el.textContent = data.events.join('\\n') || 'No events yet.';")
    parts.append("    } else {")
    parts.append("      el.textContent = 'Failed to load events.';")
    parts.append("    }")
    parts.append("  });")
    parts.append("}")
    parts.append("")
    # Wire up buttons
    parts.append("document.getElementById('btn-add').onclick = addApp;")
    parts.append("document.getElementById('btn-ping-all').onclick = pingAll;")
    parts.append("document.getElementById('btn-refresh-log').onclick = loadEvents;")
    parts.append("")
    # Load data immediately
    parts.append("loadConfig(pingAll);")
    parts.append("loadEvents();")
    parts.append("</script>")
    parts.append("</body></html>")
    return HTMLResponse("".join(parts))


@app.get("/modules", response_class=HTMLResponse)
def modules_page():
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html><head>")
    parts.append("<title>Modules - Elliott's Singular Controls</title>")
    parts.append(_base_style())
    parts.append("<style>")
    parts.append("  .module-card { margin-bottom: 20px; }")
    parts.append("  .module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }")
    parts.append("  .module-title { font-size: 16px; font-weight: 600; margin: 0; }")
    parts.append("  .toggle-switch { position: relative; width: 44px; height: 24px; }")
    parts.append("  .toggle-switch input { opacity: 0; width: 0; height: 0; }")
    parts.append("  .toggle-slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #3d3d3d; border-radius: 24px; transition: 0.2s; }")
    parts.append("  .toggle-slider:before { position: absolute; content: ''; height: 18px; width: 18px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.2s; }")
    parts.append("  .toggle-switch input:checked + .toggle-slider { background: #00bcd4; }")
    parts.append("  .toggle-switch input:checked + .toggle-slider:before { transform: translateX(20px); }")
    parts.append("  @keyframes pulse-warning { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }")
    parts.append("  .disconnect-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.9); display: none; justify-content: center; align-items: center; z-index: 9999; }")
    parts.append("  .disconnect-overlay.active { animation: pulse-warning 1.5s ease-in-out infinite; }")
    parts.append("  .disconnect-modal { background: #2d2d2d; border: 3px solid #ff5252; border-radius: 16px; padding: 40px; text-align: center; max-width: 400px; box-shadow: 0 0 40px rgba(255,82,82,0.3); }")
    parts.append("  .disconnect-icon { font-size: 48px; margin-bottom: 16px; color: #ff5252; }")
    parts.append("  .disconnect-title { font-size: 24px; font-weight: 700; color: #ff5252; margin-bottom: 12px; }")
    parts.append("  .disconnect-message { font-size: 14px; color: #888888; margin-bottom: 20px; }")
    parts.append("  .disconnect-status { font-size: 12px; color: #666666; }")
    # TFL Manual Input styles - matching standalone page (using !important to override base styles)
    parts.append("  .tfl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }")
    parts.append("  .tfl-column h4 { margin: 0 0 16px 0; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #888; }")
    parts.append("  .tfl-row { display: flex; align-items: stretch; margin-bottom: 6px; border-radius: 6px; overflow: hidden; background: #252525; }")
    parts.append("  .tfl-label { width: 140px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; padding: 12px 8px; }")
    parts.append("  .tfl-label span { font-size: 11px; font-weight: 600; text-align: center; line-height: 1.2; }")
    parts.append("  input.tfl-input { flex: 1 !important; padding: 12px 14px !important; font-size: 12px !important; background: #0c6473; color: #fff !important; border: none !important; font-weight: 500 !important; outline: none !important; font-family: inherit !important; width: auto !important; margin: 0 !important; border-radius: 0 !important; }")
    parts.append("  input.tfl-input::placeholder { color: rgba(255,255,255,0.5) !important; }")
    # HTTP Command URL styles
    parts.append("  .cmd-url { display: block; padding: 8px 12px; background: #2d2d2d; border-radius: 4px; font-family: 'Consolas', 'Monaco', monospace; font-size: 11px; color: #4ecdc4; cursor: pointer; transition: all 0.2s; word-break: break-all; }")
    parts.append("  .cmd-url:hover { background: #3d3d3d; color: #fff; }")
    parts.append("</style>")
    parts.append("</head><body>")
    # Disconnect overlay
    parts.append('<div id="disconnect-overlay" class="disconnect-overlay">')
    parts.append('<div class="disconnect-modal">')
    parts.append('<div class="disconnect-icon">&#9888;</div>')
    parts.append('<div class="disconnect-title">Connection Lost</div>')
    parts.append('<div class="disconnect-message">The server has been closed or restarted.<br>Please restart the application to reconnect.</div>')
    parts.append('<div class="disconnect-status" id="disconnect-status">Attempting to reconnect...</div>')
    parts.append('</div>')
    parts.append('</div>')
    parts.append(_nav_html("Modules"))
    parts.append("<h1>Modules</h1>")
    parts.append("<p>Enable and configure optional modules to extend functionality.</p>")

    # TfL Status Module
    tfl_enabled = "checked" if CONFIG.enable_tfl else ""
    auto_refresh = "checked" if CONFIG.tfl_auto_refresh else ""
    stream_url = html_escape(CONFIG.singular_stream_url or "")

    parts.append('<fieldset class="module-card"><legend>TfL Line Status</legend>')
    parts.append('<div class="module-header">')
    parts.append('<p class="module-title">Transport for London - Line Status</p>')
    parts.append('<label class="toggle-switch"><input type="checkbox" id="tfl-enabled" ' + tfl_enabled + ' onchange="toggleModule()" /><span class="toggle-slider"></span></label>')
    parts.append('</div>')
    parts.append('<p style="color: #8b949e; margin: 0;">Fetches current TfL line status and pushes to Singular Data Stream.</p>')

    # TFL Content container (collapsible based on module toggle)
    tfl_display = "block" if CONFIG.enable_tfl else "none"
    parts.append(f'<div id="tfl-content" style="display: {tfl_display};">')

    # Data Stream URL input
    parts.append('<form id="stream-form" style="margin-top: 16px;">')
    parts.append('<label>Data Stream URL (where to push TfL data)')
    parts.append('<input name="stream_url" value="' + stream_url + '" placeholder="https://datastream.singular.live/datastreams/..." autocomplete="off" /></label>')
    parts.append('</form>')

    # Auto-refresh toggle (as toggle switch)
    parts.append('<div style="margin-top: 16px; display: flex; align-items: center; gap: 12px;">')
    parts.append('<span style="font-size: 14px;">Auto-refresh every 60 seconds</span>')
    parts.append('<label class="toggle-switch"><input type="checkbox" id="auto-refresh" ' + auto_refresh + ' onchange="toggleAutoRefresh()" /><span class="toggle-slider"></span></label>')
    parts.append('</div>')

    # Action buttons and status (inline)
    parts.append('<div class="btn-row">')
    parts.append('<button type="button" onclick="saveAndRefresh()">Save & Update</button>')
    parts.append('<button type="button" class="secondary" onclick="refreshTfl()">Update Now</button>')
    parts.append('<button type="button" class="secondary" onclick="previewTfl()">Preview</button>')
    parts.append('<button type="button" class="warning" onclick="testTfl()">Send TEST</button>')
    parts.append('<button type="button" class="danger" onclick="blankTfl()">Send Blank</button>')
    parts.append('<span id="tfl-status" class="status idle">Not updated yet</span>')
    parts.append('</div>')
    parts.append('<pre id="tfl-preview" style="display: none; max-height: 200px; overflow: auto; margin-top: 12px;"></pre>')

    # Manual TFL Input Section - Using CSS classes to match standalone page
    parts.append('<div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #3d3d3d;">')
    parts.append('<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">')
    parts.append('<h3 style="margin: 0; font-size: 16px; font-weight: 600;">Manual Line Status</h3>')
    parts.append('<a href="/tfl/control" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: #3d3d3d; color: #fff; text-decoration: none; border-radius: 6px; font-size: 12px; font-weight: 500; transition: background 0.2s;">Open Standalone <span style="font-size: 10px;">↗</span></a>')
    parts.append('</div>')
    parts.append('<p style="color: #888; margin: 0 0 20px 0; font-size: 13px;">Override individual line statuses. Empty fields default to "Good Service".</p>')
    parts.append('<div class="tfl-grid">')

    # Underground column
    parts.append('<div class="tfl-column">')
    parts.append('<h4>Underground</h4>')
    for line in TFL_UNDERGROUND:
        safe_id = line.replace(" ", "-").replace("&", "and")
        line_colour = TFL_LINE_COLOURS.get(line, "#3d3d3d")
        needs_dark_text = line in ["Circle", "Hammersmith & City", "Waterloo & City"]
        text_colour = "#000" if needs_dark_text else "#fff"
        parts.append(f'<div class="tfl-row">')
        parts.append(f'<div class="tfl-label" style="background: {line_colour};"><span style="color: {text_colour};">{html_escape(line)}</span></div>')
        parts.append(f'<input type="text" class="tfl-input" id="manual-{safe_id}" placeholder="Good Service" oninput="updateStatusColour(this)" />')
        parts.append('</div>')
    parts.append('</div>')

    # Overground column
    parts.append('<div class="tfl-column">')
    parts.append('<h4>Overground & Other</h4>')
    for line in TFL_OVERGROUND:
        safe_id = line.replace(" ", "-").replace("&", "and")
        line_colour = TFL_LINE_COLOURS.get(line, "#3d3d3d")
        parts.append(f'<div class="tfl-row">')
        parts.append(f'<div class="tfl-label" style="background: {line_colour};"><span style="color: #fff;">{html_escape(line)}</span></div>')
        parts.append(f'<input type="text" class="tfl-input" id="manual-{safe_id}" placeholder="Good Service" oninput="updateStatusColour(this)" />')
        parts.append('</div>')
    parts.append('</div>')

    parts.append('</div>')  # Close tfl-grid
    parts.append('<div class="btn-row" style="margin-top: 20px;">')
    parts.append('<button type="button" onclick="sendManual()">Send Manual</button>')
    parts.append('<button type="button" class="secondary" onclick="resetManual()">Reset All</button>')
    parts.append('<span id="manual-status" class="status idle">Not sent yet</span>')
    parts.append('</div>')
    parts.append('</div>')  # Close manual section
    parts.append('</div>')  # Close tfl-content
    parts.append('</fieldset>')  # Close TfL fieldset

    # TriCaster Module
    tricaster_enabled = "checked" if CONFIG.enable_tricaster else ""
    tricaster_host = html_escape(CONFIG.tricaster_host or "")
    tricaster_user = html_escape(CONFIG.tricaster_user or "admin")
    tricaster_display = "block" if CONFIG.enable_tricaster else "none"

    parts.append('<fieldset class="module-card"><legend>TriCaster Control</legend>')
    parts.append('<div class="module-header">')
    parts.append('<p class="module-title">NewTek/Vizrt TriCaster Integration</p>')
    parts.append('<label class="toggle-switch"><input type="checkbox" id="tricaster-enabled" ' + tricaster_enabled + ' onchange="toggleTriCasterModule()" /><span class="toggle-slider"></span></label>')
    parts.append('</div>')
    parts.append('<p style="color: #8b949e; margin: 0;">Connect to TriCaster on your network to control recording, streaming, DDR, and more.</p>')

    # TriCaster content container
    parts.append(f'<div id="tricaster-content" style="display: {tricaster_display};">')

    # Connection settings
    parts.append('<form id="tricaster-form" style="margin-top: 16px;">')
    parts.append('<div style="display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 12px;">')
    parts.append('<div><label>TriCaster IP/Hostname<input name="tricaster_host" value="' + tricaster_host + '" placeholder="192.168.1.100 or tricaster.local" autocomplete="off" /></label></div>')
    parts.append('<div><label>Username<input name="tricaster_user" value="' + tricaster_user + '" placeholder="admin" autocomplete="off" /></label></div>')
    parts.append('<div><label>Password<input name="tricaster_pass" type="password" placeholder="(optional)" autocomplete="off" /></label></div>')
    parts.append('</div>')
    parts.append('</form>')

    # Action buttons
    parts.append('<div class="btn-row" style="margin-top: 16px;">')
    parts.append('<button type="button" onclick="saveTriCasterConfig()">Save Connection</button>')
    parts.append('<button type="button" class="secondary" onclick="testTriCasterConnection()">Test Connection</button>')
    parts.append('<span id="tricaster-status" class="status idle">Not connected</span>')
    parts.append('</div>')

    # DDR-to-Singular Timer Sync Section
    parts.append('<div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #3d3d3d;">')
    parts.append('<h3 style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600;">DDR to Singular Timer Sync</h3>')
    parts.append('<p style="color: #888; margin: 0 0 16px 0; font-size: 13px;">Sync DDR durations to Singular timer controls. Select a Control App and configure field mappings.</p>')

    # Singular App dropdown and Round Mode
    timer_token = CONFIG.tricaster_singular_token or ""
    round_mode = CONFIG.tricaster_round_mode or "frames"
    parts.append('<div style="display: grid; grid-template-columns: 2fr 1fr; gap: 12px; margin-bottom: 16px;">')
    # Build app dropdown from saved tokens
    parts.append('<div><label>Singular Control App')
    parts.append('<select id="timer-sync-app" onchange="onTimerAppChange()">')
    parts.append('<option value="">-- Select Control App --</option>')
    for app_name, token in CONFIG.singular_tokens.items():
        selected = "selected" if token == timer_token else ""
        parts.append(f'<option value="{app_name}" {selected}>{app_name}</option>')
    parts.append('</select>')
    parts.append('</label></div>')
    parts.append(f'<div><label>Round Mode<select id="timer-round-mode"><option value="frames" {"selected" if round_mode == "frames" else ""}>Round to Frames</option><option value="none" {"selected" if round_mode != "frames" else ""}>No Rounding</option></select></label></div>')
    parts.append('</div>')

    # DDR Field Mappings - 4 DDRs with searchable dropdowns
    parts.append('<div style="margin-bottom: 16px;">')
    parts.append('<label style="font-size: 13px; color: #888; margin-bottom: 8px; display: block;">DDR Field Mappings (start typing to search fields)</label>')
    # Hidden datalist populated by JavaScript when app is selected
    parts.append('<datalist id="singular-fields-list"></datalist>')
    parts.append('<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">')
    for ddr_num in range(1, 5):
        ddr_key = str(ddr_num)
        fields = CONFIG.tricaster_timer_fields.get(ddr_key, {})
        min_val = fields.get("min", "")
        sec_val = fields.get("sec", "")
        timer_val = fields.get("timer", "")
        parts.append(f'<div style="background: #252525; padding: 12px; border-radius: 8px;">')
        parts.append(f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">')
        parts.append(f'<span style="font-weight: 600;">DDR {ddr_num}</span>')
        parts.append(f'<span id="ddr{ddr_num}-duration" style="font-size: 11px; color: #888;">--:--</span>')
        parts.append('</div>')
        parts.append(f'<div style="display: grid; gap: 6px;">')
        parts.append(f'<input id="ddr{ddr_num}-min" list="singular-fields-list" value="{min_val}" placeholder="Minutes Field ID (type to search)" style="font-size: 12px; padding: 6px 10px;" />')
        parts.append(f'<input id="ddr{ddr_num}-sec" list="singular-fields-list" value="{sec_val}" placeholder="Seconds Field ID (type to search)" style="font-size: 12px; padding: 6px 10px;" />')
        parts.append(f'<input id="ddr{ddr_num}-timer" list="singular-fields-list" value="{timer_val}" placeholder="Timer Field ID (type to search)" style="font-size: 12px; padding: 6px 10px;" />')
        parts.append('</div>')
        parts.append('</div>')
    parts.append('</div>')
    parts.append('</div>')

    # Save and Sync buttons
    parts.append('<div class="btn-row">')
    parts.append('<button type="button" onclick="saveTimerSyncConfig()">Save Config</button>')
    parts.append('<button type="button" class="secondary" onclick="syncAllDDRs()">Sync All DDRs</button>')
    parts.append('<span id="timer-sync-status" class="status idle">Not synced</span>')
    parts.append('</div>')

    # Auto-sync toggle and interval
    auto_sync_enabled = "checked" if CONFIG.tricaster_auto_sync else ""
    auto_sync_interval = CONFIG.tricaster_auto_sync_interval
    parts.append('<div style="margin-top: 16px; padding: 12px; background: #1a1a1a; border-radius: 8px;">')
    parts.append('<div style="display: flex; align-items: center; justify-content: space-between;">')
    parts.append('<div style="display: flex; align-items: center; gap: 12px;">')
    parts.append('<label class="toggle-switch"><input type="checkbox" id="auto-sync-enabled" ' + auto_sync_enabled + ' onchange="toggleAutoSync()" /><span class="toggle-slider"></span></label>')
    parts.append('<div>')
    parts.append('<span style="font-weight: 600; font-size: 14px;">Auto-Sync</span>')
    parts.append('<p style="margin: 2px 0 0 0; font-size: 11px; color: #888;">Automatically sync DDR durations when clips change</p>')
    parts.append('</div>')
    parts.append('</div>')
    parts.append('<div style="display: flex; align-items: center; gap: 8px;">')
    parts.append('<label style="font-size: 12px; color: #888;">Interval:</label>')
    parts.append(f'<select id="auto-sync-interval" onchange="updateAutoSyncInterval()" style="padding: 4px 8px; font-size: 12px; background: #252525; color: #fff; border: 1px solid #3d3d3d; border-radius: 4px;">')
    for secs in [2, 3, 5, 10]:
        selected = "selected" if secs == auto_sync_interval else ""
        parts.append(f'<option value="{secs}" {selected}>{secs}s</option>')
    parts.append('</select>')
    parts.append('<span id="auto-sync-status" style="font-size: 11px; color: #888;">--</span>')
    parts.append('</div>')
    parts.append('</div>')
    parts.append('</div>')

    # Individual DDR Sync controls
    parts.append('<div style="margin-top: 16px;">')
    parts.append('<label style="font-size: 13px; color: #888; margin-bottom: 8px; display: block;">Individual DDR Controls</label>')
    parts.append('<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">')
    for ddr_num in range(1, 5):
        parts.append(f'<div style="background: #252525; padding: 8px; border-radius: 6px; text-align: center;">')
        parts.append(f'<div style="font-size: 12px; font-weight: 600; margin-bottom: 6px;">DDR {ddr_num}</div>')
        parts.append(f'<div style="display: flex; flex-direction: column; gap: 4px;">')
        parts.append(f'<button type="button" class="secondary" style="padding: 4px 8px; font-size: 11px;" onclick="syncDDR({ddr_num})">Sync Duration</button>')
        parts.append(f'<div style="display: flex; gap: 2px;">')
        parts.append(f'<button type="button" class="success" style="flex: 1; padding: 4px; font-size: 10px;" onclick="timerCmd({ddr_num}, \'start\')">Start</button>')
        parts.append(f'<button type="button" class="warning" style="flex: 1; padding: 4px; font-size: 10px;" onclick="timerCmd({ddr_num}, \'pause\')">Pause</button>')
        parts.append(f'<button type="button" class="danger" style="flex: 1; padding: 4px; font-size: 10px;" onclick="timerCmd({ddr_num}, \'restart\')">Reset</button>')
        parts.append('</div>')
        parts.append('</div>')
        parts.append('</div>')
    parts.append('</div>')
    parts.append('</div>')

    # HTTP Command URLs section - collapsible
    parts.append('<div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #3d3d3d;">')
    parts.append('<div onclick="toggleHttpCommands()" style="cursor: pointer; display: flex; align-items: center; gap: 8px;">')
    parts.append('<span id="http-commands-arrow" style="transition: transform 0.2s;">&#9654;</span>')
    parts.append('<h3 style="margin: 0; font-size: 14px; font-weight: 600;">HTTP Command URLs</h3>')
    parts.append('</div>')
    parts.append('<div id="http-commands-content" style="display: none; margin-top: 12px;">')
    parts.append('<p style="color: #888; margin: 0 0 12px 0; font-size: 12px;">Click any URL to copy. Use these from TriCaster macros or external systems.</p>')
    parts.append('<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 11px;">')

    # Generate command URLs for each DDR
    base_url = f"http://localhost:{effective_port()}"
    for ddr_num in range(1, 5):
        parts.append(f'<div style="background: #1a1a1a; padding: 10px; border-radius: 6px;">')
        parts.append(f'<div style="font-weight: 600; margin-bottom: 6px; color: #4ecdc4;">DDR {ddr_num}</div>')
        parts.append('<div style="display: flex; flex-direction: column; gap: 4px;">')

        # Sync duration
        sync_url = f"{base_url}/tricaster/sync/{ddr_num}"
        parts.append(f'<div style="display: flex; justify-content: space-between; align-items: center;">')
        parts.append(f'<span style="color: #888;">Sync:</span>')
        parts.append(f'<code class="cmd-url" onclick="copyToClipboard(this)" title="Click to copy">{sync_url}</code>')
        parts.append('</div>')

        # Timer start
        start_url = f"{base_url}/tricaster/timer/{ddr_num}/start"
        parts.append(f'<div style="display: flex; justify-content: space-between; align-items: center;">')
        parts.append(f'<span style="color: #888;">Start:</span>')
        parts.append(f'<code class="cmd-url" onclick="copyToClipboard(this)" title="Click to copy">{start_url}</code>')
        parts.append('</div>')

        # Timer pause
        pause_url = f"{base_url}/tricaster/timer/{ddr_num}/pause"
        parts.append(f'<div style="display: flex; justify-content: space-between; align-items: center;">')
        parts.append(f'<span style="color: #888;">Pause:</span>')
        parts.append(f'<code class="cmd-url" onclick="copyToClipboard(this)" title="Click to copy">{pause_url}</code>')
        parts.append('</div>')

        # Timer restart (pause + reset)
        restart_url = f"{base_url}/tricaster/timer/{ddr_num}/restart"
        parts.append(f'<div style="display: flex; justify-content: space-between; align-items: center;">')
        parts.append(f'<span style="color: #888;">Reset:</span>')
        parts.append(f'<code class="cmd-url" onclick="copyToClipboard(this)" title="Click to copy">{restart_url}</code>')
        parts.append('</div>')

        parts.append('</div>')
        parts.append('</div>')

    parts.append('</div>')

    # All DDRs commands
    parts.append('<div style="margin-top: 8px; background: #1a1a1a; padding: 10px; border-radius: 6px;">')
    parts.append('<div style="font-weight: 600; margin-bottom: 6px; color: #4ecdc4;">All DDRs</div>')
    parts.append('<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px; font-size: 11px;">')

    sync_all_url = f"{base_url}/tricaster/sync/all"
    parts.append(f'<div style="display: flex; justify-content: space-between; align-items: center;">')
    parts.append(f'<span style="color: #888;">Sync All:</span>')
    parts.append(f'<code class="cmd-url" onclick="copyToClipboard(this)" title="Click to copy">{sync_all_url}</code>')
    parts.append('</div>')

    restart_all_url = f"{base_url}/tricaster/timer/all/restart"
    parts.append(f'<div style="display: flex; justify-content: space-between; align-items: center;">')
    parts.append(f'<span style="color: #888;">Reset All:</span>')
    parts.append(f'<code class="cmd-url" onclick="copyToClipboard(this)" title="Click to copy">{restart_all_url}</code>')
    parts.append('</div>')

    parts.append('</div>')
    parts.append('</div>')

    parts.append('</div>')  # Close http-commands-content
    parts.append('</div>')  # Close HTTP commands section

    parts.append('</div>')  # Close timer sync section

    parts.append('</div>')  # Close tricaster-content
    parts.append('</fieldset>')  # Close TriCaster fieldset

    # JavaScript - use a list and join with newlines
    js_lines = [
        "<script>",
        "let autoRefreshInterval = null;",
        "",
        "async function postJSON(url, data) {",
        "  const res = await fetch(url, {",
        '    method: "POST",',
        '    headers: { "Content-Type": "application/json" },',
        "    body: JSON.stringify(data),",
        "  });",
        "  return res.json();",
        "}",
        "",
        "function copyToClipboard(el) {",
        "  const text = el.textContent || el.innerText;",
        "  navigator.clipboard.writeText(text).then(() => {",
        "    const orig = el.style.background;",
        '    el.style.background = "#4ecdc4";',
        "    setTimeout(() => { el.style.background = orig; }, 300);",
        "  });",
        "}",
        "",
        "function toggleHttpCommands() {",
        '  const content = document.getElementById("http-commands-content");',
        '  const arrow = document.getElementById("http-commands-arrow");',
        '  if (content.style.display === "none") {',
        '    content.style.display = "block";',
        '    arrow.style.transform = "rotate(90deg)";',
        "  } else {",
        '    content.style.display = "none";',
        '    arrow.style.transform = "rotate(0deg)";',
        "  }",
        "}",
        "",
        "async function toggleModule() {",
        '  const enabled = document.getElementById("tfl-enabled").checked;',
        '  const content = document.getElementById("tfl-content");',
        '  await postJSON("/config/module/tfl", { enabled });',
        "  if (enabled) {",
        '    content.style.display = "block";',
        "  } else {",
        '    content.style.display = "none";',
        "    stopAutoRefresh();",
        "  }",
        "}",
        "",
        "async function toggleAutoRefresh() {",
        '  const enabled = document.getElementById("auto-refresh").checked;',
        '  await postJSON("/config/module/tfl/auto-refresh", { enabled });',
        "  if (enabled) { startAutoRefresh(); } else { stopAutoRefresh(); }",
        "}",
        "",
        "function startAutoRefresh() {",
        "  if (autoRefreshInterval) return;",
        "  autoRefreshInterval = setInterval(refreshTfl, 60000);",
        '  console.log("Auto-refresh started");',
        "}",
        "",
        "function stopAutoRefresh() {",
        "  if (autoRefreshInterval) { clearInterval(autoRefreshInterval); autoRefreshInterval = null; }",
        '  console.log("Auto-refresh stopped");',
        "}",
        "",
        "async function saveAndRefresh() {",
        '  const streamUrl = document.querySelector("[name=stream_url]").value;',
        '  await postJSON("/config/stream", { stream_url: streamUrl });',
        "  await refreshTfl();",
        "}",
        "",
        "async function refreshTfl() {",
        '  const status = document.getElementById("tfl-status");',
        '  status.textContent = "Refreshing...";',
        '  status.className = "status idle";',
        "  try {",
        '    const res = await fetch("/update");',
        "    if (res.ok) {",
        '      status.textContent = "Updated " + new Date().toLocaleTimeString();',
        '      status.className = "status success";',
        "    } else {",
        "      const err = await res.json();",
        '      status.textContent = err.detail || "Error";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        '    status.textContent = "Failed: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "async function previewTfl() {",
        '  const preview = document.getElementById("tfl-preview");',
        '  const status = document.getElementById("tfl-status");',
        '  status.textContent = "Fetching preview...";',
        '  status.className = "status idle";',
        "  try {",
        '    const res = await fetch("/status");',
        "    const data = await res.json();",
        '    preview.textContent = JSON.stringify(data, null, 2);',
        '    preview.style.display = "block";',
        '    status.textContent = "Preview loaded";',
        '    status.className = "status idle";',
        "  } catch (e) {",
        '    status.textContent = "Preview failed: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "async function testTfl() {",
        '  const status = document.getElementById("tfl-status");',
        '  status.textContent = "Sending TEST...";',
        '  status.className = "status idle";',
        "  try {",
        '    const res = await fetch("/test");',
        "    if (res.ok) {",
        '      status.textContent = "TEST sent " + new Date().toLocaleTimeString();',
        '      status.className = "status success";',
        "    } else {",
        "      const err = await res.json();",
        '      status.textContent = err.detail || "Error";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        '    status.textContent = "Failed: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "async function blankTfl() {",
        '  const status = document.getElementById("tfl-status");',
        '  status.textContent = "Sending blank...";',
        '  status.className = "status idle";',
        "  try {",
        '    const res = await fetch("/blank");',
        "    if (res.ok) {",
        '      status.textContent = "Blank sent " + new Date().toLocaleTimeString();',
        '      status.className = "status success";',
        "    } else {",
        "      const err = await res.json();",
        '      status.textContent = err.detail || "Error";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        '    status.textContent = "Failed: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "const TFL_LINES = " + json.dumps(TFL_LINES) + ";",
        "",
        "function updateStatusColour(input) {",
        "  var value = input.value.trim().toLowerCase();",
        '  if (value === "" || value === "good service") {',
        '    input.style.background = "#0c6473";',  # Teal for Good Service
        "  } else {",
        '    input.style.background = "#db422d";',  # Red for anything else
        "  }",
        "}",
        "",
        "function getManualPayload() {",
        "  const payload = {};",
        "  TFL_LINES.forEach(line => {",
        '    const safeId = line.replace(/ /g, "-").replace(/&/g, "and");',
        '    const input = document.getElementById("manual-" + safeId);',
        '    const value = input ? input.value.trim() : "";',
        '    payload[line] = value || "Good Service";',
        "  });",
        "  return payload;",
        "}",
        "",
        "async function sendManual() {",
        '  var status = document.getElementById("manual-status");',
        '  status.textContent = "Sending...";',
        '  status.className = "status idle";',
        "  try {",
        "    var payload = getManualPayload();",
        '    var res = await fetch("/manual", {',
        '      method: "POST",',
        '      headers: { "Content-Type": "application/json" },',
        "      body: JSON.stringify(payload)",
        "    });",
        "    if (res.ok) {",
        '      status.textContent = "Updated " + new Date().toLocaleTimeString();',
        '      status.className = "status success";',
        "    } else {",
        "      var err = await res.json();",
        '      status.textContent = err.detail || "Error";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        '    status.textContent = "Failed: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "function resetManual() {",
        "  TFL_LINES.forEach(line => {",
        '    const safeId = line.replace(/ /g, "-").replace(/&/g, "and");',
        '    const input = document.getElementById("manual-" + safeId);',
        "    if (input) {",
        '      input.value = "";',
        '      input.style.background = "#0c6473";',  # Reset to teal background
        "    }",
        "  });",
        '  document.getElementById("manual-status").textContent = "Reset";',
        '  document.getElementById("manual-status").className = "status idle";',
        "}",
        "",
        "// TriCaster Module Functions",
        "async function toggleTriCasterModule() {",
        '  const enabled = document.getElementById("tricaster-enabled").checked;',
        '  const content = document.getElementById("tricaster-content");',
        '  await postJSON("/config/module/tricaster", { enabled });',
        '  content.style.display = enabled ? "block" : "none";',
        "}",
        "",
        "async function saveTriCasterConfig() {",
        '  const status = document.getElementById("tricaster-status");',
        '  status.textContent = "Saving...";',
        '  status.className = "status idle";',
        "  try {",
        '    const host = document.querySelector("[name=tricaster_host]").value;',
        '    const user = document.querySelector("[name=tricaster_user]").value;',
        '    const pass = document.querySelector("[name=tricaster_pass]").value;',
        '    await postJSON("/config/tricaster", { host, user, password: pass });',
        '    status.textContent = "Saved";',
        '    status.className = "status success";',
        "  } catch (e) {",
        '    status.textContent = "Save failed: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "async function testTriCasterConnection() {",
        '  const status = document.getElementById("tricaster-status");',
        '  status.textContent = "Testing...";',
        '  status.className = "status idle";',
        "  try {",
        "    // Save config first",
        "    await saveTriCasterConfig();",
        '    const res = await fetch("/tricaster/test");',
        "    const data = await res.json();",
        "    if (data.ok) {",
        '      status.textContent = "Connected to " + data.host;',
        '      status.className = "status success";',
        "    } else {",
        '      status.textContent = data.error || "Connection failed";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        '    status.textContent = "Error: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "// Singular field cache for searchable dropdowns",
        "let singularFieldsCache = [];",
        "",
        "async function onTimerAppChange() {",
        '  const appSelect = document.getElementById("timer-sync-app");',
        "  const appName = appSelect.value;",
        "  if (!appName) {",
        "    singularFieldsCache = [];",
        '    document.getElementById("singular-fields-list").innerHTML = "";',
        "    return;",
        "  }",
        "  try {",
        '    const res = await fetch("/api/singular/fields/" + encodeURIComponent(appName));',
        "    const data = await res.json();",
        "    singularFieldsCache = data.fields || [];",
        "    // Populate datalist",
        '    const datalist = document.getElementById("singular-fields-list");',
        '    datalist.innerHTML = singularFieldsCache.map(f => ',
        "      `<option value=\"${f.id}\">${f.name} (${f.subcomposition})</option>`",
        '    ).join("");',
        "  } catch (e) {",
        '    console.error("Failed to load fields:", e);',
        "  }",
        "}",
        "",
        "// Load fields on page load if app already selected",
        "document.addEventListener('DOMContentLoaded', function() {",
        '  const appSelect = document.getElementById("timer-sync-app");',
        "  if (appSelect && appSelect.value) {",
        "    onTimerAppChange();",
        "  }",
        "});",
        "",
        "// DDR-to-Singular Timer Sync Functions",
        "async function saveTimerSyncConfig() {",
        '  const appSelect = document.getElementById("timer-sync-app");',
        "  const appName = appSelect.value;",
        "  // Get the actual token for the selected app",
        '  const appOption = appSelect.options[appSelect.selectedIndex];',
        "  let token = '';",
        "  if (appName) {",
        "    // Fetch the token from the apps endpoint",
        '    const appsRes = await fetch("/api/singular/apps");',
        "    const appsData = await appsRes.json();",
        "    token = appsData.apps[appName] || '';",
        "  }",
        '  const roundMode = document.getElementById("timer-round-mode").value;',
        "  const timerFields = {};",
        "  for (let i = 1; i <= 4; i++) {",
        '    const min = document.getElementById("ddr" + i + "-min").value.trim();',
        '    const sec = document.getElementById("ddr" + i + "-sec").value.trim();',
        '    const timer = document.getElementById("ddr" + i + "-timer").value.trim();',
        "    if (min || sec || timer) {",
        '      timerFields[i.toString()] = { min: min, sec: sec, timer: timer };',
        "    }",
        "  }",
        "  try {",
        '    const res = await postJSON("/config/tricaster/timer-sync", {',
        "      singular_token: token,",
        "      round_mode: roundMode,",
        "      timer_fields: timerFields",
        "    });",
        '    const status = document.getElementById("timer-sync-status");',
        "    if (res.ok) {",
        '      status.textContent = "Config saved";',
        '      status.className = "status success";',
        "    } else {",
        '      status.textContent = res.error || "Save failed";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        '    alert("Error saving config: " + e.message);',
        "  }",
        "}",
        "",
        "function formatDuration(minutes, seconds) {",
        "  const m = Math.floor(minutes);",
        "  const s = seconds.toFixed(2);",
        "  return m + ':' + (s < 10 ? '0' : '') + s;",
        "}",
        "",
        "async function syncAllDDRs() {",
        '  const status = document.getElementById("timer-sync-status");',
        '  status.textContent = "Syncing...";',
        '  status.className = "status idle";',
        "  try {",
        '    const res = await fetch("/tricaster/sync/all");',
        "    const data = await res.json();",
        "    if (data.ok) {",
        "      let synced = 0;",
        "      // Update duration displays for each DDR",
        "      for (const [key, result] of Object.entries(data.results || {})) {",
        "        const ddrNum = key.replace('ddr', '');",
        '        const durEl = document.getElementById("ddr" + ddrNum + "-duration");',
        "        if (durEl && result.ok) {",
        "          durEl.textContent = formatDuration(result.minutes, result.seconds);",
        '          durEl.style.color = "#4ecdc4";',
        "          synced++;",
        "        }",
        "      }",
        '      status.textContent = "Synced " + synced + " DDRs";',
        '      status.className = "status success";',
        "    } else {",
        '      status.textContent = (data.errors && data.errors[0]) || "Sync failed";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        '    status.textContent = "Error: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "async function syncDDR(num) {",
        '  const status = document.getElementById("timer-sync-status");',
        '  const durEl = document.getElementById("ddr" + num + "-duration");',
        "  try {",
        '    const res = await fetch("/tricaster/sync/" + num);',
        "    const data = await res.json();",
        "    if (data.ok) {",
        "      const durText = formatDuration(data.minutes, data.seconds);",
        "      if (durEl) {",
        "        durEl.textContent = durText;",
        '        durEl.style.color = "#4ecdc4";',
        "      }",
        '      status.textContent = "DDR " + num + ": " + durText;',
        '      status.className = "status success";',
        "    } else {",
        "      if (durEl) {",
        '        durEl.textContent = "Error";',
        '        durEl.style.color = "#e74c3c";',
        "      }",
        '      status.textContent = data.detail || data.error || "Sync failed";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        "    if (durEl) {",
        '      durEl.textContent = "Error";',
        '      durEl.style.color = "#e74c3c";',
        "    }",
        '    status.textContent = "Error: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "async function timerCmd(num, cmd) {",
        '  const status = document.getElementById("timer-sync-status");',
        "  try {",
        '    const res = await fetch("/tricaster/timer/" + num + "/" + cmd);',
        "    const data = await res.json();",
        "    if (data.ok) {",
        '      status.textContent = "DDR " + num + " timer: " + cmd;',
        '      status.className = "status success";',
        "    } else {",
        '      status.textContent = data.detail || data.error || "Command failed";',
        '      status.className = "status error";',
        "    }",
        "  } catch (e) {",
        '    status.textContent = "Error: " + e.message;',
        '    status.className = "status error";',
        "  }",
        "}",
        "",
        "// Auto-sync functions",
        "let autoSyncStatusInterval = null;",
        "",
        "async function toggleAutoSync() {",
        '  const enabled = document.getElementById("auto-sync-enabled").checked;',
        '  const interval = parseInt(document.getElementById("auto-sync-interval").value);',
        "  try {",
        '    const res = await postJSON("/tricaster/auto-sync", { enabled: enabled, interval: interval });',
        "    if (res.ok) {",
        "      if (enabled) {",
        "        startAutoSyncStatusPolling();",
        "      } else {",
        "        stopAutoSyncStatusPolling();",
        '        document.getElementById("auto-sync-status").textContent = "--";',
        "      }",
        "    }",
        "  } catch (e) {",
        '    console.error("Auto-sync toggle failed:", e);',
        "  }",
        "}",
        "",
        "async function updateAutoSyncInterval() {",
        '  const enabled = document.getElementById("auto-sync-enabled").checked;',
        '  const interval = parseInt(document.getElementById("auto-sync-interval").value);',
        "  try {",
        '    await postJSON("/tricaster/auto-sync", { enabled: enabled, interval: interval });',
        "  } catch (e) {",
        '    console.error("Auto-sync interval update failed:", e);',
        "  }",
        "}",
        "",
        "async function pollAutoSyncStatus() {",
        "  try {",
        '    const res = await fetch("/tricaster/auto-sync/status");',
        "    const data = await res.json();",
        '    const statusEl = document.getElementById("auto-sync-status");',
        "    if (data.running) {",
        '      statusEl.textContent = data.last_sync ? "Last: " + data.last_sync : "Running...";',
        '      statusEl.style.color = "#4ecdc4";',
        "      // Update DDR duration displays from cached values",
        "      for (const [ddr, vals] of Object.entries(data.cached_values || {})) {",
        '        const durEl = document.getElementById("ddr" + ddr + "-duration");',
        "        if (durEl) {",
        "          durEl.textContent = formatDuration(vals.minutes, vals.seconds);",
        '          durEl.style.color = "#4ecdc4";',
        "        }",
        "      }",
        "    } else if (data.error) {",
        '      statusEl.textContent = "Error";',
        '      statusEl.style.color = "#e74c3c";',
        "    } else {",
        '      statusEl.textContent = "--";',
        '      statusEl.style.color = "#888";',
        "    }",
        "  } catch (e) {",
        '    console.error("Auto-sync status poll failed:", e);',
        "  }",
        "}",
        "",
        "function startAutoSyncStatusPolling() {",
        "  if (autoSyncStatusInterval) return;",
        "  pollAutoSyncStatus();",
        "  autoSyncStatusInterval = setInterval(pollAutoSyncStatus, 2000);",
        "}",
        "",
        "function stopAutoSyncStatusPolling() {",
        "  if (autoSyncStatusInterval) {",
        "    clearInterval(autoSyncStatusInterval);",
        "    autoSyncStatusInterval = null;",
        "  }",
        "}",
        "",
        "// Start polling if auto-sync is enabled on page load",
        "document.addEventListener('DOMContentLoaded', function() {",
        '  if (document.getElementById("auto-sync-enabled") && document.getElementById("auto-sync-enabled").checked) {',
        "    startAutoSyncStatusPolling();",
        "  }",
        "});",
    ]
    parts.append("\n".join(js_lines))

    # Auto-refresh init code - also join with newlines
    init_js = [
        "",
        "// Connection monitoring",
        "let connectionLost = false;",
        "let reconnectAttempts = 0;",
        "",
        "async function checkConnection() {",
        "  try {",
        '    const res = await fetch("/health", { method: "GET", cache: "no-store" });',
        "    if (res.ok) {",
        "      if (connectionLost) {",
        "        // Reconnected - reload page to refresh state",
        "        location.reload();",
        "      }",
        "      reconnectAttempts = 0;",
        "      return true;",
        "    }",
        "  } catch (e) {",
        "    // Connection failed",
        "  }",
        "  return false;",
        "}",
        "",
        "async function monitorConnection() {",
        "  const connected = await checkConnection();",
        "  if (!connected) {",
        "    connectionLost = true;",
        "    reconnectAttempts++;",
        '    const overlay = document.getElementById("disconnect-overlay");',
        '    const status = document.getElementById("disconnect-status");',
        '    overlay.style.display = "flex";',
        '    overlay.classList.add("active");',
        '    status.textContent = "Reconnect attempt " + reconnectAttempts + "...";',
        "  }",
        "}",
        "",
        "// Check connection every 3 seconds",
        "setInterval(monitorConnection, 3000);",
        "",
        "// Start auto-refresh if enabled on page load",
        'const autoRefreshChecked = document.getElementById("auto-refresh").checked;',
        'const tflEnabledChecked = document.getElementById("tfl-enabled").checked;',
        'console.log("Auto-refresh checkbox:", autoRefreshChecked, "TFL enabled:", tflEnabledChecked);',
        'if (autoRefreshChecked && tflEnabledChecked) {',
        '  console.log("Starting auto-refresh on page load");',
        "  startAutoRefresh();",
        "} else {",
        '  console.log("Auto-refresh NOT started - conditions not met");',
        "}",
        "</script>",
    ]
    parts.append("\n".join(init_js))
    parts.append("</body></html>")
    return HTMLResponse("".join(parts))


# Keep old route for backwards compatibility
@app.get("/integrations", response_class=HTMLResponse)
def integrations_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/modules")


@app.get("/tfl/control", response_class=HTMLResponse)
def tfl_manual_standalone():
    """Standalone TFL manual control page for external operators."""
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html><head>")
    parts.append("<title>TfL Line Status Control</title>")
    parts.append('<link rel="icon" type="image/x-icon" href="/static/favicon.ico">')
    parts.append('<link rel="icon" type="image/png" href="/static/esc_icon.png">')
    parts.append("<style>")
    parts.append("  @font-face { font-family: 'ITVReem'; src: url('/static/ITV Reem-Regular.ttf') format('truetype'); }")
    parts.append("  * { box-sizing: border-box; margin: 0; padding: 0; }")
    parts.append("  body { font-family: 'ITVReem', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a1a; color: #fff; min-height: 100vh; padding: 30px; }")
    parts.append("  .container { max-width: 900px; margin: 0 auto; }")
    parts.append("  .header { text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #3d3d3d; }")
    parts.append("  .header h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; }")
    parts.append("  .header p { color: #888; font-size: 14px; }")
    parts.append("  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-bottom: 24px; }")
    parts.append("  .column h2 { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #888; margin-bottom: 16px; }")
    parts.append("  .line-row { display: flex; align-items: stretch; margin-bottom: 6px; border-radius: 6px; overflow: hidden; background: #252525; }")
    parts.append("  .line-label { width: 140px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; padding: 12px 8px; }")
    parts.append("  .line-label span { font-size: 11px; font-weight: 600; text-align: center; line-height: 1.2; }")
    parts.append("  .line-input { flex: 1; padding: 12px 14px; font-size: 12px; background: #0c6473; color: #fff; border: none; font-weight: 500; outline: none; font-family: inherit; }")
    parts.append("  .line-input::placeholder { color: rgba(255,255,255,0.5); }")
    parts.append("  .actions { display: flex; justify-content: center; gap: 12px; padding-top: 20px; border-top: 1px solid #3d3d3d; }")
    parts.append("  button { padding: 14px 32px; font-size: 14px; font-weight: 600; border: none; border-radius: 8px; cursor: pointer; transition: all 0.2s; font-family: inherit; }")
    parts.append("  .btn-primary { background: #00bcd4; color: #fff; }")
    parts.append("  .btn-primary:hover { background: #0097a7; }")
    parts.append("  .btn-secondary { background: #3d3d3d; color: #fff; }")
    parts.append("  .btn-secondary:hover { background: #4d4d4d; }")
    parts.append("  .status { text-align: center; margin-top: 16px; font-size: 13px; color: #888; }")
    parts.append("  .status.success { color: #4caf50; }")
    parts.append("  .status.error { color: #ff5252; }")
    parts.append("</style>")
    parts.append("</head><body>")
    parts.append('<div class="container">')
    parts.append('<div class="header">')
    parts.append("<h1>TfL Line Status Control</h1>")
    parts.append("<p>Update line statuses manually. Empty fields default to \"Good Service\".</p>")
    parts.append("</div>")
    parts.append('<div class="grid">')

    # Underground column
    parts.append('<div class="column">')
    parts.append("<h2>Underground</h2>")
    for line in TFL_UNDERGROUND:
        safe_id = line.replace(" ", "-").replace("&", "and")
        line_colour = TFL_LINE_COLOURS.get(line, "#3d3d3d")
        needs_dark_text = line in ["Circle", "Hammersmith & City", "Waterloo & City"]
        text_colour = "#000" if needs_dark_text else "#fff"
        parts.append(f'<div class="line-row">')
        parts.append(f'<div class="line-label" style="background: {line_colour};"><span style="color: {text_colour};">{html_escape(line)}</span></div>')
        parts.append(f'<input type="text" class="line-input" id="manual-{safe_id}" placeholder="Good Service" oninput="updateColour(this)" />')
        parts.append('</div>')
    parts.append("</div>")

    # Overground column
    parts.append('<div class="column">')
    parts.append("<h2>Overground & Other</h2>")
    for line in TFL_OVERGROUND:
        safe_id = line.replace(" ", "-").replace("&", "and")
        line_colour = TFL_LINE_COLOURS.get(line, "#3d3d3d")
        parts.append(f'<div class="line-row">')
        parts.append(f'<div class="line-label" style="background: {line_colour};"><span style="color: #fff;">{html_escape(line)}</span></div>')
        parts.append(f'<input type="text" class="line-input" id="manual-{safe_id}" placeholder="Good Service" oninput="updateColour(this)" />')
        parts.append('</div>')
    parts.append("</div>")

    parts.append("</div>")  # Close grid
    parts.append('<div class="actions">')
    parts.append('<button class="btn-primary" onclick="sendUpdate()">Send Update</button>')
    parts.append('<button class="btn-secondary" onclick="resetAll()">Reset All</button>')
    parts.append("</div>")
    parts.append('<div class="status" id="status"></div>')
    parts.append("</div>")  # Close container

    # JavaScript
    tfl_lines_js = json.dumps(TFL_UNDERGROUND + TFL_OVERGROUND)
    parts.append("<script>")
    parts.append(f"const TFL_LINES = {tfl_lines_js};")
    parts.append("function updateColour(input) {")
    parts.append("  const val = input.value.trim().toLowerCase();")
    parts.append("  input.style.background = (val === '' || val === 'good service') ? '#0c6473' : '#db422d';")
    parts.append("}")
    parts.append("function getPayload() {")
    parts.append("  const payload = {};")
    parts.append("  TFL_LINES.forEach(line => {")
    parts.append("    const safeId = line.replace(/ /g, '-').replace(/&/g, 'and');")
    parts.append("    const input = document.getElementById('manual-' + safeId);")
    parts.append("    if (input) payload[line] = input.value.trim() || 'Good Service';")
    parts.append("  });")
    parts.append("  return payload;")
    parts.append("}")
    parts.append("async function sendUpdate() {")
    parts.append("  const status = document.getElementById('status');")
    parts.append("  status.textContent = 'Sending...';")
    parts.append("  status.className = 'status';")
    parts.append("  try {")
    parts.append("    const res = await fetch('/manual', {")
    parts.append("      method: 'POST',")
    parts.append("      headers: { 'Content-Type': 'application/json' },")
    parts.append("      body: JSON.stringify(getPayload())")
    parts.append("    });")
    parts.append("    if (res.ok) {")
    parts.append("      status.textContent = 'Update sent successfully';")
    parts.append("      status.className = 'status success';")
    parts.append("    } else {")
    parts.append("      status.textContent = 'Failed to send update';")
    parts.append("      status.className = 'status error';")
    parts.append("    }")
    parts.append("  } catch (e) {")
    parts.append("    status.textContent = 'Error: ' + e.message;")
    parts.append("    status.className = 'status error';")
    parts.append("  }")
    parts.append("}")
    parts.append("function resetAll() {")
    parts.append("  TFL_LINES.forEach(line => {")
    parts.append("    const safeId = line.replace(/ /g, '-').replace(/&/g, 'and');")
    parts.append("    const input = document.getElementById('manual-' + safeId);")
    parts.append("    if (input) { input.value = ''; input.style.background = '#0c6473'; }")
    parts.append("  });")
    parts.append("  document.getElementById('status').textContent = '';")
    parts.append("}")
    parts.append("</script>")
    parts.append("</body></html>")
    return HTMLResponse("".join(parts))


@app.get("/commands", response_class=HTMLResponse)
def commands_page(request: Request):
    base = _base_url(request)
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html><head>")
    parts.append("<title>Commands - Elliott's Singular Controls</title>")
    parts.append(_base_style())
    parts.append("<style>")
    parts.append("  .copyable { cursor: pointer; transition: all 0.2s; padding: 4px 8px; border-radius: 4px; }")
    parts.append("  .copyable:hover { background: #00bcd4; color: #fff; }")
    parts.append("  .copyable.copied { background: #4caf50; color: #fff; }")
    parts.append("  .value-input { width: 100%; padding: 6px 10px; border: 1px solid #30363d; border-radius: 4px; background: #21262d; color: #e6edf3; font-size: 13px; box-sizing: border-box; }")
    parts.append("  .value-input:focus { outline: none; border-color: #00bcd4; box-shadow: 0 0 0 2px rgba(0,188,212,0.2); }")
    parts.append("  .value-input::placeholder { color: #666; }")
    parts.append("  button.play-btn { background: #238636; border: none; color: #fff; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 14px; }")
    parts.append("  button.play-btn:hover { background: #2ea043; }")
    parts.append("</style>")
    parts.append("</head><body>")
    parts.append(_nav_html("Commands"))
    parts.append("<h1>Singular Commands</h1>")
    parts.append("<p>This view focuses on simple <strong>GET</strong> triggers you can use in automation systems.</p>")
    parts.append("<p>Base URL: <code>" + html_escape(base) + "</code></p>")
    parts.append("<fieldset><legend>Discovered Subcompositions</legend>")
    parts.append('<p><button type="button" onclick="loadCommands()">Reload Commands</button>')
    parts.append('<button type="button" onclick="rebuildRegistry()">Rebuild from Singular</button></p>')
    parts.append('<div style="margin-bottom:0.5rem;">')
    parts.append('<label>Filter <input id="cmd-filter" placeholder="Filter by name or key" /></label>')
    parts.append('<label>Sort <select id="cmd-sort">')
    parts.append('<option value="name">Name (A–Z)</option>')
    parts.append('<option value="key">Key (A–Z)</option>')
    parts.append("</select></label></div>")
    parts.append('<div id="commands">Loading...</div>')
    parts.append("</fieldset>")
    # JS
    parts.append("<script>")
    parts.append("let COMMANDS_CACHE = null;")
    parts.append("function renderCommands() {")
    parts.append('  const container = document.getElementById("commands");')
    parts.append("  if (!COMMANDS_CACHE) { container.textContent = 'No commands loaded.'; return; }")
    parts.append('  const filterText = document.getElementById("cmd-filter").value.toLowerCase();')
    parts.append('  const sortMode = document.getElementById("cmd-sort").value;')
    parts.append("  let entries = Object.entries(COMMANDS_CACHE);")
    parts.append("  if (filterText) {")
    parts.append("    entries = entries.filter(([key, item]) => {")
    parts.append("      return key.toLowerCase().includes(filterText) || (item.name || '').toLowerCase().includes(filterText);")
    parts.append("    });")
    parts.append("  }")
    parts.append("  entries.sort(([ka, a], [kb, b]) => {")
    parts.append("    if (sortMode === 'key') { return ka.localeCompare(kb); }")
    parts.append("    return (a.name || '').localeCompare(b.name || '');")
    parts.append("  });")
    parts.append("  if (!entries.length) { container.textContent = 'No matches.'; return; }")
    parts.append("  let html = '';")
    parts.append("  for (const [key, item] of entries) {")
    parts.append("    const appBadge = item.app_name ? '<span style=\"background:#00bcd4;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:8px;\">' + item.app_name + '</span>' : '';")
    parts.append("    html += '<h3>' + item.name + appBadge + ' <small style=\"color:#888;\">(' + key + ')</small></h3>';")
    parts.append("    html += '<table><tr><th>Action</th><th>GET URL</th><th style=\"width:60px;text-align:center;\">Test</th></tr>';")
    parts.append("    html += '<tr><td>IN</td><td><code class=\"copyable\" onclick=\"copyToClipboard(this)\" title=\"Click to copy\">' + item.in_url + '</code></td>' +")
    parts.append("            '<td style=\"text-align:center;\"><a href=\"' + item.in_url + '\" target=\"_blank\" class=\"play-btn\" title=\"Test IN\">▶</a></td></tr>';")
    parts.append("    html += '<tr><td>OUT</td><td><code class=\"copyable\" onclick=\"copyToClipboard(this)\" title=\"Click to copy\">' + item.out_url + '</code></td>' +")
    parts.append("            '<td style=\"text-align:center;\"><a href=\"' + item.out_url + '\" target=\"_blank\" class=\"play-btn\" title=\"Test OUT\">▶</a></td></tr>';")
    parts.append("    html += '</table>';")
    parts.append("    const fields = item.fields || {};")
    parts.append("    const fkeys = Object.keys(fields);")
    parts.append("    if (fkeys.length) {")
    parts.append("      html += '<p><strong>Fields:</strong></p>';")
    parts.append("      html += '<table><tr><th>Field</th><th>Type</th><th>Command URL</th><th style=\"width:200px;\">Test Value</th><th style=\"width:60px;text-align:center;\">Test</th></tr>';")
    parts.append("      for (const fid of fkeys) {")
    parts.append("        const ex = fields[fid];")
    parts.append("        if (ex.timecontrol_start_url) {")
    parts.append("          html += '<tr><td rowspan=\"3\">' + fid + '</td><td rowspan=\"3\">⏱ Timer</td>';")
    parts.append("          html += '<td><code class=\"copyable\" onclick=\"copyToClipboard(this)\" title=\"Click to copy\">' + ex.timecontrol_start_url + '</code></td>';")
    parts.append("          html += '<td></td>';")
    parts.append("          html += '<td style=\"text-align:center;\"><a href=\"' + ex.timecontrol_start_url + '\" target=\"_blank\" class=\"play-btn\" title=\"Start Timer\">▶</a></td></tr>';")
    parts.append("          html += '<tr><td><code class=\"copyable\" onclick=\"copyToClipboard(this)\" title=\"Click to copy\">' + ex.timecontrol_stop_url + '</code></td>';")
    parts.append("          html += '<td></td>';")
    parts.append("          html += '<td style=\"text-align:center;\"><a href=\"' + ex.timecontrol_stop_url + '\" target=\"_blank\" class=\"play-btn\" title=\"Stop Timer\">▶</a></td></tr>';")
    parts.append("          if (ex.start_10s_if_supported) {")
    parts.append("            html += '<tr><td><code class=\"copyable\" onclick=\"copyToClipboard(this)\" title=\"Click to copy\">' + ex.start_10s_if_supported + '</code></td>';")
    parts.append("            html += '<td></td>';")
    parts.append("            html += '<td style=\"text-align:center;\"><a href=\"' + ex.start_10s_if_supported + '\" target=\"_blank\" class=\"play-btn\" title=\"Start 10s\">▶</a></td></tr>';")
    parts.append("          } else {")
    parts.append("            html += '<tr><td colspan=\"3\" style=\"color:#666;\">Duration param not supported</td></tr>';")
    parts.append("          }")
    parts.append("        } else if (ex.set_url) {")
    parts.append("          const fieldId = key + '_' + fid;")
    parts.append("          html += '<tr><td>' + fid + '</td><td>Value</td>';")
    parts.append("          html += '<td><code class=\"copyable\" onclick=\"copyToClipboard(this)\" title=\"Click to copy\">' + ex.set_url + '</code></td>';")
    parts.append("          html += '<td><input type=\"text\" id=\"val_' + fieldId + '\" class=\"value-input\" placeholder=\"Enter value...\" data-base-url=\"' + ex.set_url + '\" /></td>';")
    parts.append("          html += '<td style=\"text-align:center;\"><button type=\"button\" class=\"play-btn\" onclick=\"testValue(\\'' + fieldId + '\\')\" title=\"Send Value\">▶</button></td></tr>';")
    parts.append("        }")
    parts.append("      }")
    parts.append("      html += '</table>';")
    parts.append("    }")
    parts.append("  }")
    parts.append("  container.innerHTML = html;")
    parts.append("}")
    parts.append("async function loadCommands() {")
    parts.append('  const container = document.getElementById("commands");')
    parts.append("  container.textContent = 'Loading...';")
    parts.append("  try {")
    parts.append('    const res = await fetch("/singular/commands");')
    parts.append("    if (!res.ok) { container.textContent = 'Failed to load commands: ' + res.status; return; }")
    parts.append("    const data = await res.json();")
    parts.append("    COMMANDS_CACHE = data.catalog || {};")
    parts.append("    if (!Object.keys(COMMANDS_CACHE).length) {")
    parts.append("      container.textContent = 'No subcompositions discovered. Set token on Home and refresh registry.';")
    parts.append("      return;")
    parts.append("    }")
    parts.append("    renderCommands();")
    parts.append("  } catch (e) { container.textContent = 'Error: ' + e; }")
    parts.append("}")
    parts.append("async function rebuildRegistry() {")
    parts.append('  const container = document.getElementById("commands");')
    parts.append("  container.textContent = 'Rebuilding from Singular...';")
    parts.append("  try {")
    parts.append('    const res = await fetch("/singular/refresh", { method: "POST" });')
    parts.append("    const data = await res.json();")
    parts.append("    if (data.count !== undefined) {")
    parts.append("      container.textContent = 'Rebuilt: ' + data.count + ' subcompositions found. Reloading...';")
    parts.append("      setTimeout(loadCommands, 500);")
    parts.append("    } else { container.textContent = 'Rebuild failed'; }")
    parts.append("  } catch (e) { container.textContent = 'Error: ' + e; }")
    parts.append("}")
    parts.append("function copyToClipboard(el) {")
    parts.append("  const text = el.textContent || el.innerText;")
    parts.append("  navigator.clipboard.writeText(text).then(() => {")
    parts.append("    el.classList.add('copied');")
    parts.append("    const original = el.textContent;")
    parts.append("    el.setAttribute('data-original', original);")
    parts.append("    el.textContent = 'Copied!';")
    parts.append("    setTimeout(() => {")
    parts.append("      el.textContent = el.getAttribute('data-original');")
    parts.append("      el.classList.remove('copied');")
    parts.append("    }, 1500);")
    parts.append("  });")
    parts.append("}")
    parts.append("async function testValue(fieldId) {")
    parts.append("  const input = document.getElementById('val_' + fieldId);")
    parts.append("  if (!input) { alert('Input not found'); return; }")
    parts.append("  const value = input.value.trim();")
    parts.append("  if (!value) { alert('Please enter a value to test'); return; }")
    parts.append("  const baseUrl = input.getAttribute('data-base-url');")
    parts.append("  const url = baseUrl.replace('VALUE', encodeURIComponent(value));")
    parts.append("  try {")
    parts.append("    input.style.borderColor = '#00bcd4';")
    parts.append("    const res = await fetch(url);")
    parts.append("    if (res.ok) {")
    parts.append("      input.style.borderColor = '#4caf50';")
    parts.append("      setTimeout(() => { input.style.borderColor = ''; }, 2000);")
    parts.append("    } else {")
    parts.append("      input.style.borderColor = '#f44336';")
    parts.append("      alert('Request failed: ' + res.status);")
    parts.append("      setTimeout(() => { input.style.borderColor = ''; }, 2000);")
    parts.append("    }")
    parts.append("  } catch (e) {")
    parts.append("    input.style.borderColor = '#f44336';")
    parts.append("    alert('Error: ' + e.message);")
    parts.append("    setTimeout(() => { input.style.borderColor = ''; }, 2000);")
    parts.append("  }")
    parts.append("}")
    parts.append("document.addEventListener('DOMContentLoaded', () => {")
    parts.append('  document.getElementById("cmd-filter").addEventListener("input", renderCommands);')
    parts.append('  document.getElementById("cmd-sort").addEventListener("change", renderCommands);')
    parts.append("});")
    parts.append("loadCommands();")
    parts.append("</script>")
    parts.append("</body></html>")
    return HTMLResponse("".join(parts))


@app.get("/settings", response_class=HTMLResponse)
def settings_page():
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html><head>")
    parts.append("<title>Settings - Elliott's Singular Controls</title>")
    parts.append(_base_style())
    parts.append("</head><body>")
    parts.append(_nav_html("Settings"))
    parts.append("<h1>Settings</h1>")
    # Theme toggle styles
    parts.append("<style>")
    parts.append("  .theme-toggle { display: flex; align-items: center; gap: 12px; margin: 16px 0; }")
    parts.append("  .theme-toggle-label { font-size: 14px; min-width: 50px; }")
    parts.append("  .toggle-switch { position: relative; width: 50px; height: 26px; }")
    parts.append("  .toggle-switch input { opacity: 0; width: 0; height: 0; }")
    parts.append("  .toggle-slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #30363d; border-radius: 26px; transition: 0.3s; }")
    parts.append("  .toggle-slider:before { position: absolute; content: ''; height: 20px; width: 20px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.3s; }")
    parts.append("  .toggle-switch input:checked + .toggle-slider { background: #00bcd4; }")
    parts.append("  .toggle-switch input:checked + .toggle-slider:before { transform: translateX(24px); }")
    parts.append("</style>")
    # General
    parts.append("<fieldset><legend>General</legend>")
    is_light = CONFIG.theme == 'light'
    parts.append('<div class="theme-toggle">')
    parts.append('<span class="theme-toggle-label">Dark</span>')
    parts.append('<label class="toggle-switch"><input type="checkbox" id="theme-toggle" ' + ('checked' if is_light else '') + ' onchange="toggleTheme()" /><span class="toggle-slider"></span></label>')
    parts.append('<span class="theme-toggle-label">Light</span>')
    parts.append('</div>')
    parts.append("<p><strong>Server Port:</strong> <code>" + str(effective_port()) + "</code> (change via GUI launcher)</p>")
    parts.append("<p><strong>Version:</strong> <code>" + _runtime_version() + "</code></p>")
    parts.append("<p><strong>Config file:</strong> <code>" + html_escape(str(CONFIG_PATH)) + "</code></p>")
    parts.append("</fieldset>")
    # Config Import/Export
    parts.append("<fieldset><legend>Config Backup</legend>")
    parts.append("<p>Export your current configuration or import a previously saved config.</p>")
    parts.append('<button type="button" onclick="exportConfig()">Export Config</button>')
    parts.append('<input type="file" id="import-file" accept=".json" style="display:none;" onchange="importConfig()" />')
    parts.append('<button type="button" onclick="document.getElementById(\'import-file\').click()">Import Config</button>')
    parts.append('<pre id="import-output"></pre>')
    parts.append("</fieldset>")
    # Updates
    parts.append("<fieldset><legend>Updates</legend>")
    parts.append("<p>Current version: <code>" + _runtime_version() + "</code></p>")
    parts.append('<button type="button" onclick="checkUpdates()">Check GitHub for latest release</button>')
    parts.append('<pre id="update-output">Not checked yet.</pre>')
    parts.append("</fieldset>")
    # JS
    parts.append("<script>")
    parts.append("async function postJSON(url, data) {")
    parts.append("  const res = await fetch(url, {")
    parts.append('    method: "POST",')
    parts.append('    headers: { "Content-Type": "application/json" },')
    parts.append("    body: JSON.stringify(data),")
    parts.append("  });")
    parts.append("  return res.json();")
    parts.append("}")
    parts.append("async function toggleTheme() {")
    parts.append('  const isLight = document.getElementById("theme-toggle").checked;')
    parts.append('  const theme = isLight ? "light" : "dark";')
    parts.append('  await postJSON("/settings", { theme });')
    parts.append("  location.reload();")
    parts.append("}")
    parts.append("async function checkUpdates() {")
    parts.append('  const out = document.getElementById("update-output");')
    parts.append('  out.textContent = "Checking for updates...";')
    parts.append("  try {")
    parts.append('    const res = await fetch("/version/check");')
    parts.append("    const data = await res.json();")
    parts.append("    let msg = 'Current version: ' + data.current;")
    parts.append("    if (data.latest) {")
    parts.append("      msg += '\\nLatest release: ' + data.latest;")
    parts.append("    }")
    parts.append("    msg += '\\n\\n' + data.message;")
    parts.append("    if (data.release_url && !data.up_to_date) {")
    parts.append("      msg += '\\n\\nDownload: ' + data.release_url;")
    parts.append("    }")
    parts.append("    out.textContent = msg;")
    parts.append("  } catch (e) {")
    parts.append("    out.textContent = 'Version check failed: ' + e;")
    parts.append("  }")
    parts.append("}")
    parts.append("async function exportConfig() {")
    parts.append("  try {")
    parts.append('    const res = await fetch("/config/export");')
    parts.append("    const config = await res.json();")
    parts.append("    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });")
    parts.append("    const url = URL.createObjectURL(blob);")
    parts.append("    const a = document.createElement('a');")
    parts.append("    a.href = url;")
    parts.append("    a.download = 'esc_config.json';")
    parts.append("    a.click();")
    parts.append("    URL.revokeObjectURL(url);")
    parts.append('    document.getElementById("import-output").textContent = "Config exported successfully!";')
    parts.append("  } catch (e) {")
    parts.append('    document.getElementById("import-output").textContent = "Export failed: " + e;')
    parts.append("  }")
    parts.append("}")
    parts.append("async function importConfig() {")
    parts.append('  const fileInput = document.getElementById("import-file");')
    parts.append("  const file = fileInput.files[0];")
    parts.append("  if (!file) return;")
    parts.append("  try {")
    parts.append("    const text = await file.text();")
    parts.append("    const config = JSON.parse(text);")
    parts.append('    const res = await fetch("/config/import", {')
    parts.append('      method: "POST",')
    parts.append('      headers: { "Content-Type": "application/json" },')
    parts.append("      body: JSON.stringify(config),")
    parts.append("    });")
    parts.append("    const data = await res.json();")
    parts.append('    document.getElementById("import-output").textContent = data.message || "Config imported!";')
    parts.append("    setTimeout(() => location.reload(), 2000);")
    parts.append("  } catch (e) {")
    parts.append('    document.getElementById("import-output").textContent = "Import failed: " + e;')
    parts.append("  }")
    parts.append("}")
    parts.append("checkUpdates();")
    parts.append("</script>")
    parts.append("</body></html>")
    return HTMLResponse("".join(parts))


@app.get("/help")
def help_index():
    return {
        "docs": "/docs",
        "note": "Most control endpoints support GET for quick triggering but POST is recommended for automation.",
        "examples": {
            "list_subs": "/singular/list",
            "all_commands_json": "/singular/commands",
            "commands_for_one": "/<key>/help",
            "trigger_in": "/<key>/in",
            "trigger_out": "/<key>/out",
            "set_field": "/<key>/set?field=Top%20Line&value=Hello",
            "timecontrol": "/<key>/timecontrol?field=Countdown%20Start&run=true&value=0&seconds=10",
        },
    }


# ================== 10. MAIN ENTRY POINT ==================

def main():
    """Main entry point for the application."""
    import uvicorn
    port = effective_port()
    logger.info(
        "Starting Elliott's Singular Controls v%s on http://localhost:%s (binding 0.0.0.0)",
        _runtime_version(),
        port
    )
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()