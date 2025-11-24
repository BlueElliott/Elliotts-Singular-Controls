# Elliott's Singular Controls - Session Summary

## Project Overview
**Name:** Elliott's Singular Controls (formerly Singular Tweaks)
**Version:** 1.1.1
**Repository:** https://github.com/BlueElliott/Elliotts-Singular-Controls

A premium desktop application for controlling Singular.live graphics with TfL and TriCaster integration.

---

## What's New in v1.1.1

### TriCaster Module - Full Implementation

1. **TriCaster Connection**
   - Connect to any TriCaster on the network via HTTP API
   - Configurable host, username, and password
   - Test connection functionality with version display

2. **DDR to Singular Timer Sync**
   - Read DDR durations from TriCaster (`/v1/dictionary?key=ddr_timecode`)
   - Sync durations to Singular timer controls (minutes + seconds fields)
   - Support for 4 DDRs with configurable field mappings
   - Frame-accurate rounding option (rounds to frame boundaries based on clip FPS)
   - Timer controls: Start, Pause, Reset, Restart (pause + reset)
   - Searchable field ID dropdowns (type to filter available fields)
   - Control App dropdown populated from saved apps on Home page

3. **Auto-Sync Feature** (NEW)
   - Toggle switch to enable automatic DDR duration syncing
   - Configurable interval: 2s, 3s, 5s, or 10s
   - Smart change detection - only syncs when clip duration actually changes
   - Background polling with cached value comparison
   - Real-time status display showing last sync time
   - Auto-updates DDR duration displays in UI

4. **HTTP Command URLs**
   - Collapsible section showing all command URLs
   - Click-to-copy functionality with visual feedback
   - Perfect for TriCaster macros or external automation
   - Commands for: Sync, Start, Pause, Reset per DDR + All DDRs

5. **Configuration**
   - `tricaster_host` - TriCaster IP/hostname
   - `tricaster_user` - Username (default: "admin")
   - `tricaster_pass` - Password
   - `tricaster_singular_token` - Singular Control App token for timer sync
   - `tricaster_timer_fields` - DDR-to-field mappings
   - `tricaster_round_mode` - "frames" or "none"
   - `tricaster_auto_sync` - Enable/disable auto-sync
   - `tricaster_auto_sync_interval` - Polling interval (2-10 seconds)

6. **API Endpoints**
   ```
   POST /config/module/tricaster      - Enable/disable module
   POST /config/tricaster             - Save connection settings
   GET  /tricaster/test               - Test connection
   GET  /config/tricaster/timer-sync  - Get timer sync config
   POST /config/tricaster/timer-sync  - Save timer sync config
   GET  /tricaster/sync/{ddr_num}     - Sync single DDR to Singular
   GET  /tricaster/sync/all           - Sync all configured DDRs
   GET  /tricaster/timer/{ddr}/start  - Start timer
   GET  /tricaster/timer/{ddr}/pause  - Pause timer
   GET  /tricaster/timer/{ddr}/reset  - Reset timer
   GET  /tricaster/timer/{ddr}/restart - Restart (pause + reset)
   GET  /tricaster/timer/all/restart  - Restart all timers
   GET  /tricaster/auto-sync/status   - Get auto-sync status
   POST /tricaster/auto-sync          - Enable/disable auto-sync
   GET  /api/singular/apps            - Get saved Control Apps
   GET  /api/singular/fields/{app}    - Get field IDs for an app
   ```

### UI Improvements
- Removed "(click to expand)" text from HTTP Commands header
- Changed "DDR-to-Singular" to "DDR to Singular" (cleaner)
- Changed "Preview loaded (not sent)" to "Preview loaded" (fits on one line)
- Fixed port number display in HTTP command URLs

---

## What's in v1.1.0

### Major Improvements

1. **Smooth Animated Pulse Indicator**
   - Replaced Tkinter canvas with PIL-rendered anti-aliased graphics
   - 4x supersampling with LANCZOS downscaling for smooth circles
   - Rippling outward animation (center -> inner ring -> outer ring)
   - True 0-100% opacity fade using background color blending
   - Phase-offset sine wave animation (90 degree offsets)

2. **UI Consistency Fixes**
   - Fixed button/status alignment on Modules page (40px height)
   - Fixed Home page layout with right-aligned action buttons
   - Standardized element sizing across all pages
   - Removed visual artifacts from rounded rectangles (outline=fill fix)

3. **TfL Manual Input Fix**
   - Fixed background color not updating on modules page
   - Input fields now correctly turn red for non-"Good Service" values

4. **Desktop GUI Polish**
   - Removed seam lines on port card rounded rectangles
   - Pulse indicator now seamlessly blends with background
   - Added bd=0 and highlightthickness=0 to eliminate borders

---

## Repository Structure

```
Elliotts-Singular-Controls/
├── .github/workflows/      # GitHub Actions (build.yml)
├── docs/                   # Developer documentation
│   └── STYLING_GUIDE.md
├── scripts/                # Build scripts
│   └── installer.nsi
├── elliotts_singular_controls/  # Main Python package
│   ├── __init__.py         # Version defined here (1.1.1)
│   ├── __main__.py         # Entry point
│   ├── core.py             # FastAPI app, all HTML/CSS/JS embedded
│   └── gui_launcher.py     # Desktop GUI with PIL pulse animation
├── static/                 # Static assets (fonts, icons)
│   ├── esc_icon.ico
│   ├── esc_icon.png
│   ├── favicon.ico
│   └── ITV Reem-*.ttf      # Font family
├── ElliottsSingularControls.spec  # PyInstaller spec (MUST be in root!)
├── .gitignore
├── MANIFEST.in
├── pyproject.toml
├── README.md               # Updated with usage guides
├── requirements.txt
└── SESSION_SUMMARY.md      # This file
```

---

## Critical Technical Details

### TriCaster API Integration
The TriCaster module uses the TriCaster HTTP API:

```python
# Dictionary endpoint for DDR timecodes
GET http://{host}/v1/dictionary?key=ddr_timecode

# Response XML contains DDR info:
# <ddr index="1" file_duration="00:01:30.00" clip_framerate="29.97" ...>

# Version endpoint for connection test
GET http://{host}/v1/version
```

### DDR Duration Parsing
```python
def _timecode_to_seconds(timecode: str) -> float:
    # Handles: "HH:MM:SS.ff", "MM:SS.ff", or raw seconds

def _split_minutes_seconds(total_seconds: float, fps: float) -> Tuple[int, float]:
    # Optionally rounds to frame boundaries
    if round_mode == "frames" and fps > 0:
        total_seconds = round(total_seconds * fps) / fps
```

### Auto-Sync Implementation
```python
# Background task polls TriCaster and syncs changed values
async def _auto_sync_loop():
    while _auto_sync_running and CONFIG.tricaster_auto_sync:
        for ddr_num_str, fields in CONFIG.tricaster_timer_fields.items():
            duration, fps = _get_ddr_duration_and_fps(ddr_num)
            mins, secs = _split_minutes_seconds(duration, fps)
            current_val = (mins, round(secs, 2))

            # Only sync if value changed
            if _last_ddr_values.get(ddr_num_str) != current_val:
                _last_ddr_values[ddr_num_str] = current_val
                sync_ddr_to_singular(ddr_num)

        await asyncio.sleep(CONFIG.tricaster_auto_sync_interval)
```

### Singular Timer Sync
```python
# Field mappings per DDR:
tricaster_timer_fields = {
    "1": {"min": "SVR A Duration Time Minutes",
          "sec": "SVR A Start Duration Seconds",
          "timer": "SVR A Start Timer"},
    "2": {...},
}

# Sync patches Singular Control App:
PATCH /controlapps/{token}/control
[{"subCompositionId": "...", "payload": {"field_id": value}}]
```

### PyInstaller Spec File Location
**IMPORTANT:** The `ElliottsSingularControls.spec` file MUST be in the repository root directory.

### PIL Anti-Aliased Pulse Animation
```python
# Draw at 4x resolution
big_size = 40 * 4  # 160 pixels
img = Image.new('RGB', (big_size, big_size), bg_color)
draw = ImageDraw.Draw(img)
draw.ellipse([...], outline=color, width=ring_width)
img = img.resize((40, 40), Image.LANCZOS)
```

### CSS Specificity for TFL Inputs
- **modules page:** `.tfl-input { background: #0c6473; }` - NO `!important`
- **standalone page:** `.line-input { background: #0c6473; }` - NO `!important`

---

## Key Files and Their Purposes

### `elliotts_singular_controls/core.py`
- **Lines 1-210:** Imports, constants, AppConfig (includes TriCaster + auto-sync settings)
- **Lines 875-975:** Auto-sync background task and state management
- **Lines 470-700:** DDR-to-Singular timer sync functions
- **Lines 1440-1570:** TriCaster API endpoints + auto-sync endpoints
- **Lines 2170-2400:** TriCaster UI on Modules page (including auto-sync toggle)
- **Lines 2500-3000:** TriCaster JavaScript functions (including auto-sync)

### `elliotts_singular_controls/gui_launcher.py`
- System tray application using pystray
- PIL-based anti-aliased pulse indicator
- Uvicorn server management
- Console window for logs
- Port configuration dialog

### `.github/workflows/build.yml`
- Triggered on tag push (`v*.*.*`)
- Builds Windows executable with PyInstaller
- Creates GitHub Release with the exe

---

## How to Build Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m elliotts_singular_controls.gui_launcher

# Build standalone executable
pyinstaller ElliottsSingularControls.spec
# Output: dist/ElliottsSingularControls-1.1.1.exe
```

---

## How to Release

1. **Make changes and test locally**
2. **Bump version** in `elliotts_singular_controls/__init__.py`
3. **Update spec fallback** in `ElliottsSingularControls.spec`
4. **Commit changes:**
   ```bash
   git add -A
   git commit -m "Description of changes"
   ```
5. **Push to main:**
   ```bash
   git push origin main
   ```
6. **Create and push tag:**
   ```bash
   git tag v1.1.1
   git push origin v1.1.1
   ```
7. **Monitor GitHub Actions:** https://github.com/BlueElliott/Elliotts-Singular-Controls/actions

---

## Web Interface URLs

When running locally on port 3113:
- **Home:** http://localhost:3113/
- **Modules (TFL + TriCaster):** http://localhost:3113/modules
- **Standalone TFL Control:** http://localhost:3113/tfl/control
- **Commands:** http://localhost:3113/commands
- **Settings:** http://localhost:3113/settings

---

## Common Issues and Solutions

### Issue: TriCaster connection fails
**Solution:** Check that:
- TriCaster is on and network accessible
- IP address is correct
- Credentials are correct (default: admin with no password)
- TriCaster HTTP API is enabled

### Issue: DDR sync shows "duration not found"
**Solution:** Ensure the DDR has a clip loaded. The API only returns duration for loaded clips.

### Issue: Singular timer not updating
**Solution:** Verify:
- Control App token is correct
- Field IDs match exactly (case-sensitive)
- Singular composition is published and running

### Issue: Auto-sync not detecting changes
**Solution:** Ensure:
- TriCaster connection is working (test first)
- DDR field mappings are configured for min/sec fields
- Singular Control App token is set
- Clip is loaded in the DDR

### Issue: TFL input background not changing color
**Solution:** Check that CSS for `.tfl-input` doesn't have `!important` on background.

### Issue: PyInstaller can't find `__main__.py`
**Solution:** Ensure `ElliottsSingularControls.spec` is in repository ROOT.

---

## Version History

### v1.1.1 (Current)
- TriCaster module with DDR-to-Singular timer sync
- Auto-sync feature with smart change detection
- HTTP Command URLs section (collapsible, click-to-copy)
- Searchable field ID dropdowns
- Control App dropdown from saved apps
- UI text improvements

### v1.1.0
- Smooth anti-aliased pulse indicator using PIL
- Fixed UI alignment issues across all pages
- Fixed TfL manual input background color
- Removed visual artifacts from desktop GUI
- Updated README with comprehensive usage guide

### v1.0.15
- Fixed TfL manual input on modules page
- Moved spec file back to root for PyInstaller

### v1.0.0 - v1.0.14
- Initial development releases
- Core functionality established
- Web interface and API endpoints
- TfL integration with Data Stream support

---

## Package Naming

- **Python package:** `elliotts_singular_controls`
- **PyPI package:** `elliotts-singular-controls`
- **Executable:** `ElliottsSingularControls-{VERSION}.exe`
- **Repository:** `Elliotts-Singular-Controls`
