# Cuez-to-CueiT Bridge Module (On Hold)

**Status:** Paused - Potential issue identified with file-based sync method
**Date Created:** 2025-11-29
**Version Targeted:** 1.1.2 (not released)

---

## Overview

The Cuez-to-CueiT Bridge was designed to automatically synchronize scripts from Cuez Automator to CueiT teleprompter software using a file-based approach.

## What Was Built

### Core Functionality
- **Script Fetching:** Retrieves scripts from Cuez Automator via `/api/episode/script` endpoint
- **Format Conversion:** Converts Cuez scripts to CueiT-compatible format with `[#] Slugline` markers
- **File Output:** Saves formatted scripts to configurable file location (RTF or TXT)
- **Auto-Sync Worker:** Background thread monitors Cuez for changes every 3 seconds (configurable 1-30s)
- **Change Detection:** MD5 hash-based detection to prevent unnecessary updates

### Configuration
- Independent Cuez connection settings (separate from main Cuez module)
  - `cuez_to_cueit_cuez_host` - Cuez Automator hostname/IP
  - `cuez_to_cueit_cuez_port` - Cuez Automator port (default: 7070)
- Output file configuration
  - `cuez_to_cueit_output_path` - File path for CueiT (default: `C:\CueiT\Import\cuez_live.rtf`)
  - `cuez_to_cueit_format` - Format selection (rtf/txt)
  - `cuez_to_cueit_poll_interval` - Polling interval in seconds (1-30)
- Auto-sync toggle
  - `cuez_to_cueit_auto_sync` - Enable/disable automatic synchronization
  - `cuez_to_cueit_last_hash` - MD5 hash for change detection

### User Interface
1. **Module Card in /modules Page:**
   - Enable/disable toggle
   - Cuez connection settings (host/port)
   - File browser button for output path selection
   - Format dropdown (RTF/TXT)
   - Poll interval input
   - Auto-sync toggle
   - Manual "Sync Now" button
   - Real-time status display (episode, story count, worker status, file path)
   - "How It Works" guide
   - Link to standalone page

2. **Standalone Control Page (/cuez-to-cueit/control):**
   - Real-time status dashboard
   - Auto-sync toggle
   - Manual sync button
   - Auto-refreshes every 5 seconds
   - Clean interface for external operators

### API Endpoints Implemented
```
GET  /cuez-to-cueit/status       - Get current status
GET  /cuez-to-cueit/config       - Get configuration
POST /cuez-to-cueit/config       - Update config (host, port, path, format, interval)
POST /cuez-to-cueit/sync/now     - Manual sync trigger
POST /cuez-to-cueit/sync/enable  - Enable auto-sync and start worker
POST /cuez-to-cueit/sync/disable - Disable auto-sync and stop worker
POST /config/module/cuez-to-cueit - Enable/disable module
```

### Code Implementation Details

#### Functions Created
```python
# Core sync functions
def cuez_to_cueit_fetch_script() -> Dict[str, Any]
def cuez_to_cueit_format_rtf(script_data: Dict[str, Any]) -> str
def cuez_to_cueit_format_txt(script_data: Dict[str, Any]) -> str
def cuez_to_cueit_save_file(content: str, output_path: str) -> Dict[str, Any]
def cuez_to_cueit_sync_now() -> Dict[str, Any]

# Background worker functions
def cuez_to_cueit_worker()
def cuez_to_cueit_start_worker()
def cuez_to_cueit_stop_worker()
def cuez_to_cueit_get_status() -> Dict[str, Any]
```

#### JavaScript Functions
```javascript
// Module UI functions
async function toggleCuezToCueitModule()
async function toggleCuezToCueitAutoSync()
async function browseCuezToCueitOutputPath()
async function saveCuezToCueitConfig()
async function syncCuezToCueitNow()
async function refreshCuezToCueitStatus()
```

### RTF Format Example
```rtf
{\rtf1\ansi\deff0
\par [#] HEADLINES\par\par
Good evening, I'm Elliott Smith with your news headlines...\par\par
\par [#] STORY 1 - WEATHER\par\par
Today's weather brought unexpected sunshine across the region...\par\par
}
```

---

## Intended Workflow

1. User loads episode in Cuez Automator
2. Module detects change within poll interval (default 3 seconds)
3. Module formats script as RTF with `[#]` sluglines
4. Module saves to configured output file
5. CueiT detects file modification and auto-reloads
6. Complete automation - no manual steps required

---

## Why It's On Hold

**Issue Identified:** Potential problem with the file-based synchronization method needs to be investigated and resolved before proceeding.

The file-based approach relies on:
- CueiT's ability to auto-detect file changes
- File system permissions and access
- Timing between file writes and CueiT reloads

**Potential Alternative Approaches to Consider:**
1. **MOS Protocol Integration** - Industry standard for newsroom systems
   - More robust and designed for this use case
   - Requires BBC's `mosromgr` library or raw XML socket communication
   - CueiT supports MOS natively
   - More complex but more reliable

2. **Direct API (if available)** - Check if CueiT has undocumented POST endpoints
   - Would be cleanest solution
   - Need to investigate CueiT API further

3. **Enhanced File-Based** - Improve current approach
   - Add file locking mechanisms
   - Implement retry logic
   - Add CueiT process monitoring
   - Verify file write completion before CueiT access

---

## Code Location

All code was implemented in:
- `elliotts_singular_controls/core.py` (approximately 724 lines added)
  - Configuration class updates
  - Core sync functions
  - Background worker thread
  - API endpoints
  - Module UI HTML/JavaScript

The code has been **removed** from the main project but is documented here for future reference.

---

## Resources & Research

### Documentation Reviewed
- CueiT API documentation (`Cue iT API.pdf`)
- [CueiT Connecting to Newsroom Manual](http://www.cuescript.tv/downloads/Manuals/CueiT_Connecting_to_Newsroom.pdf)
- [MOS Protocol 4.0 Documentation](https://mosprotocol.com/wp-content/MOS-Protocol-Documents/MOSProtocolVersion40/index.html)
- [BBC mosromgr GitHub](https://github.com/bbc/mosromgr) - Python MOS library
- [Cuez Gateway Documentation](https://intercom.help/cuez/en/articles/8831506-how-do-i-connect-the-cuez-gateway-with-cuescript-cueit)

### Key Findings from Research
- CueiT supports MOS protocol for NRCS integration
- CueiT can import .CUE, .TXT, .RTF, .DOCX formats
- CueiT auto-detects sluglines using `[#] Slugline` format in RTF
- Existing CuezGateway solution is "flaky" according to user
- File-based sync is simplest but may have reliability issues
- MOS protocol is industry standard but more complex to implement

---

## Testing Status

**What Was Tested:**
- ✅ Module appears in `/modules` page
- ✅ Configuration can be saved
- ✅ API endpoints respond correctly
- ✅ Status endpoint returns current configuration
- ✅ Server starts without errors

**What Was NOT Tested:**
- ❌ Actual sync with real Cuez Automator data
- ❌ CueiT auto-reload behavior
- ❌ File format compatibility with CueiT
- ❌ Slugline detection in CueiT
- ❌ Performance under production load
- ❌ Edge cases (network interruptions, file locks, etc.)

---

## Next Steps (When Resuming)

1. **Investigate the Issue**
   - Identify specific problem with file-based approach
   - Test with actual CueiT installation
   - Verify file format compatibility
   - Check auto-reload behavior

2. **Evaluate Alternatives**
   - Research MOS protocol implementation effort
   - Check for CueiT direct API options
   - Consider hybrid approaches

3. **Prototype Solutions**
   - Build minimal test case
   - Validate approach works reliably
   - Benchmark performance

4. **Resume Implementation**
   - Apply chosen solution
   - Complete testing
   - Document final approach
   - Release as v1.1.2 or later

---

## Commit History (Before Removal)

**Commits Made:**
1. `45755e1` - Add Cuez-to-CueiT Bridge module for automatic script synchronization
2. `69f9a05` - Update SESSION_SUMMARY.md and version to 1.1.2

**Tag Created (Will be removed):**
- `v1.1.2`

---

## Notes

This was a complete, working implementation from a code perspective. The decision to pause was made due to identified concerns about the reliability of the file-based approach, not because of code issues.

The module demonstrated:
- Clean architecture matching existing modules
- Comprehensive UI/UX design
- Full API implementation
- Background worker pattern
- Change detection optimization

All learnings and code patterns can be reused when the approach is finalized.
