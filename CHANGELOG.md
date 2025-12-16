# Elliott's Singular Controls - Complete Changelog & Timeline

## Project History

**Original Name:** Singular Tweaks
**Current Name:** Elliott's Singular Controls
**Repository:** https://github.com/BlueElliott/Elliotts-Singular-Controls
**First Commit:** 2025-11-10

---

## Release Timeline

| Version | Date | Type |
|---------|------|------|
| v1.0.0 | 2025-11-10 | Initial Release |
| v1.0.1 | 2025-11-10 | Feature Update |
| v1.0.2 | 2025-11-10 | Bug Fix |
| v1.0.3 | 2025-11-10 | Bug Fix |
| v1.0.4 | 2025-11-10 | Bug Fix |
| v1.0.5 | 2025-11-14 | Bug Fix |
| v1.0.6 | 2025-11-14 | Bug Fix |
| v1.0.7 | 2025-11-14 | Bug Fix |
| v1.0.8 | 2025-11-15 | Maintenance |
| v1.0.9 | 2025-11-19 | Feature Update |
| v1.0.10 | 2025-11-20 | Feature Update |
| v1.0.11 | 2025-11-20 | Bug Fix |
| v1.0.12 | 2025-11-20 | Bug Fix |
| v1.0.13 | 2025-11-20 | Feature Update |
| v1.0.14 | 2025-11-22 | Major Rebrand |
| v1.0.15 | 2025-11-23 | Bug Fix |
| v1.1.0 | 2025-11-23 | Major Update |
| v1.1.1 | 2025-11-29 | Feature Update |
| v1.1.2 | N/A | On Hold |
| v1.1.3 | 2025-12-16 | Feature Update |
| v1.1.4 | 2025-12-16 | Bug Fix |
| v1.1.5 | 2025-12-16 | Feature Update |

---

## Detailed Changelog

### 2025-12-16

#### v1.1.5 - CasparCG Control Module
- `3bbc41c` - Add CasparCG control module (v1.1.5)
  - AMCP protocol integration for CasparCG Server
  - Graphics template control (CG ADD, CG PLAY, CG STOP, CG REMOVE)
  - Media playback control (PLAY, STOP, PAUSE)
  - Channel and layer management
  - Server connection monitoring
  - Standalone control page at `/casparcg/control`
  - Configuration settings (host, port)
  - Test connection functionality

#### v1.1.4 - TfL Fixes & Cuez Shortcuts
- `acee540` - Fix TfL standalone page input color changes and add Cuez keyboard shortcuts (v1.1.4)
  - Fixed TfL standalone page input background color changes
  - Input fields now correctly turn red for non-"Good Service" status
  - Added keyboard shortcuts for Cuez Automator navigation
  - Improved operator efficiency with quick controls

#### v1.1.3 - Counter Control & UI Unification
- `e1c12ce` - Add Singular counter control and unified button UI (v1.1.3)
  - Singular counter field control functionality
  - Increment/decrement operations
  - Reset functionality
  - Direct value setting
  - Unified button styling across all modules
  - Consistent UI design and spacing

#### Repository Maintenance
- `3fb54dd` - Tidy repository and update .gitignore
- `04d4685` - Move Cuez-to-CueiT Bridge to future_projects (on hold)

---

### 2025-11-29

#### v1.1.2 (Not Released - On Hold)
- `69f9a05` - Update SESSION_SUMMARY.md and version to 1.1.2
- `45755e1` - Add Cuez-to-CueiT Bridge module for automatic script synchronization
  - Complete implementation of automatic script sync from Cuez to CueiT
  - File-based approach with RTF/TXT format support
  - Background worker with configurable polling (1-30s)
  - MD5 hash-based change detection
  - Standalone control page at `/cuez-to-cueit/control`
  - **Status: On hold due to file-based sync reliability concerns**

#### v1.1.1 - Major Feature Release
- `0c014aa` - Update SESSION_SUMMARY.md with v1.1.2 features
- `99d019d` - Add Cuez Automator and iNews Cleaner modules, dynamic network IP display
  - **Cuez Automator Module:**
    - Full integration with Cuez Automator HTTP API
    - Button control (fire, set ON/OFF states)
    - Macro execution
    - Navigation controls (next/previous item and trigger)
    - Rundown content viewing (items and blocks)
    - Trigger specific blocks by ID
    - Standalone control page at `/cuez/control`
    - Click-to-copy UUIDs for automation
  - **iNews Cleaner Module:**
    - Remove formatting grommets from iNews exports
    - Regex pattern matching for grommet removal
    - Two-column layout (input/output)
    - Copy output to clipboard
    - Standalone page at `/inews/control`
  - **Dynamic Network IP Display:**
    - Smart URL detection based on access method
    - Desktop GUI shows clickable network IP
    - All HTTP command URLs adapt to access method
- `9c63caa` - Add TriCaster auto-sync and UI improvements (v1.1.1)
  - **TriCaster Module:**
    - TriCaster connection settings (host, user, password)
    - DDR-to-Singular timer sync functionality
    - Read DDR durations from TriCaster API
    - Sync durations to Singular timer controls
    - Frame-accurate rounding option
    - Timer controls: Start, Pause, Reset, Restart
    - Configurable field mappings for 4 DDRs
    - Auto-sync feature with configurable intervals (2-10s)
    - Smart change detection to prevent unnecessary syncs
    - HTTP Command URLs for external triggering

---

### 2025-11-23

#### v1.1.0 - UI Polish & Smooth Pulse Indicator
- `753664a` - Release v1.1.0 - UI polish and smooth pulse indicator
  - Smooth anti-aliased pulse indicator using PIL rendering
  - 4x supersampling with LANCZOS downscaling
  - Rippling outward animation (center -> inner -> outer)
  - True 0-100% opacity fade using background color blending
  - Fixed button/status alignment on Modules page (40px height)
  - Fixed Home page layout with right-aligned action buttons
  - Removed visual artifacts from rounded rectangles
  - Updated README with comprehensive usage guide

#### v1.0.15 - TfL Manual Input Fix
- `39e84aa` - Update SESSION_SUMMARY.md with comprehensive v1.0.15 documentation
- `ebc922c` - Move spec file back to root directory for PyInstaller compatibility
- `4bdcb86` - Fix SPECPATH usage in PyInstaller spec file
- `e753591` - Fix PyInstaller spec file to use absolute paths from repo root
- `59c3628` - Fix PyInstaller path resolution in GitHub Actions workflow
- `b8cf45c` - Fix TFL manual input background color not updating on modules page
  - Input fields now correctly turn red for non-"Good Service" values
  - Matches behavior of standalone TFL control page

---

### 2025-11-22

#### v1.0.14 - Elliott's Singular Controls Rebrand
- `2dfc904` - Rename package from singular_tweaks to elliotts_singular_controls
  - Complete rebrand from "Singular Tweaks" to "Elliott's Singular Controls"
  - New package name: `elliotts_singular_controls`
  - New executable name: `ElliottsSingularControls.exe`
- `838aace` - Add SESSION_SUMMARY.md back to repo for cross-PC sync
- `9a4e201` - Reorganize repository structure for cleaner root
- `6987750` - Add version number to executable filename
- `9239f2c` - Fix GitHub Actions workflow for new exe name
- `a301332` - Release v1.0.14 - Elliott's Singular Controls
- `65ca7ef` - Update session summary for TFL manual input and disconnect warning
- `475104d` - Add TFL manual input with line colours and disconnect warning
  - Manual line status input with TfL brand colours
  - Connection lost/disconnect warning overlay
  - Auto-reconnect functionality

---

### 2025-11-21

#### GUI Redesign
- `525f246` - Redesign GUI with modern rounded buttons and fix console logging
  - Modern rounded button styling
  - Improved console logging
  - Better visual consistency

---

### 2025-11-20

#### v1.0.13 - Teal Theme & Port Config
- `ccf71fc` - Improve console window with initial status and output capture
- `e86b589` - Fix console window and settings page bugs
- `107cfac` - Bump version to 1.0.13
- `bbd0905` - Update UI styling with teal theme and move port config to launcher
  - New teal/cyan color scheme (#00bcd4)
  - Port configuration moved to desktop launcher
  - Improved visual consistency

#### v1.0.12 - Uvicorn Logging Fix
- `8a3e075` - Fix uvicorn logging errors and add versioned executable naming

#### v1.0.11 - Console Window Fix
- `3429eb1` - Fix GUI launcher: hide console window and resolve uvicorn logging error

#### v1.0.10 - GUI Launcher
- `4bbb63f` - Add GUI launcher, config import/export, and version improvements
  - Desktop GUI with system tray support
  - Config import/export functionality
  - Version display improvements

---

### 2025-11-19

#### v1.0.9 - Version Check & Portable EXE
- `1e4ace0` - v1.0.9: Add version check & simplify to portable EXE only
  - GitHub release version checking
  - Simplified to portable executable only (no installer)
- `390b195` - Fix PyInstaller imports for newer versions
- `571cf89` - Fix build issues and make PyPI publish optional
- `f4130de` - Tidy installer setup and add missing build files

---

### 2025-11-15

#### v1.0.8 - Build Cleanup
- `090ac35` - Remove PyInstaller spec file and build artifacts
- `e6eb13d` - Bump version to 1.0.8
- `654d0f6` - Add cleaned build workflow and pyproject config

---

### 2025-11-14

#### v1.0.7 - UI Refinements
- `b53ced3` - Fix nav HTML f-string for PyInstaller
- `3326e98` - Refine UI, add settings, logging and persisted config
  - Settings page
  - Persistent configuration
  - Improved logging
- `dd14a1c` - Fix version import and ensure server loads on localhost

#### v1.0.6 - NSIS Installer Fix
- `daba5a8` - Fix NSIS path in workflow
- `df86f27` - Fix NSIS path in workflow

#### v1.0.5 - NSIS Installer
- `908b0a9` - Add NSIS installer build
  - Windows installer using NSIS
  - Start menu shortcuts
  - Uninstaller

---

### 2025-11-13

#### Build Infrastructure
- Initial NSIS installer setup

---

### 2025-11-10

#### v1.0.4, v1.0.3, v1.0.2 - Initial Bug Fixes
- Various bug fixes for initial release

#### v1.0.1 - Settings & Update Check
- `d602664` - Add ZIP packaging to release workflow
- `3ccd14f` - v1.0.1: settings page, port display, update check
  - Settings page
  - Port display
  - Update check against GitHub releases

#### v1.0.0 - Initial Release
- `70b6154` - Merge branch 'main'
- `c13f3b1` - v1.0.0 + cleanup
- `0adfad0` - Add GitHub Actions workflow for EXE builds
- `f6156a2` - Add requirements.txt for CI build
- `f32639e` - Clean repo: ignore build artifacts and venv
- `0407f33` - Fix typo in README.md
- `68336ab` - Version 1.0.0
- `1f93274` - Initial commit

**Initial Features:**
- FastAPI-based HTTP server
- Singular.live Control App integration
- TfL line status fetching
- Data Stream support
- Web-based control panel
- HTTP API for automation

---

## Feature Evolution

### Core Features (v1.0.0)
- HTTP server on configurable port
- Singular.live API integration
- TfL line status fetching
- Data Stream push
- Basic web interface

### v1.0.1-v1.0.4
- Settings page
- Port configuration
- GitHub release update checking
- ZIP packaging

### v1.0.5-v1.0.8
- NSIS Windows installer
- Build workflow improvements
- UI refinements
- Persistent configuration

### v1.0.9-v1.0.13
- Desktop GUI launcher
- System tray support
- Console window for logs
- Config import/export
- Teal theme redesign
- Version check

### v1.0.14
- Complete rebrand to "Elliott's Singular Controls"
- TfL manual input with brand colours
- Connection lost warning overlay
- Auto-reconnect

### v1.0.15
- TfL input background color fix

### v1.1.0
- PIL-based smooth pulse indicator
- Anti-aliased graphics (4x supersampling)
- UI alignment fixes
- Comprehensive documentation

### v1.1.5
- CasparCG control module
- AMCP protocol integration
- Template and media control

### v1.1.4
- TfL standalone page fixes
- Cuez keyboard shortcuts

### v1.1.3
- Singular counter control
- Unified button UI

### v1.1.1
- TriCaster module
- Cuez Automator integration
- iNews Cleaner
- Dynamic network IP display

---

## Statistics

- **Total Commits:** 51+
- **Total Releases:** 20 (v1.1.2 on hold)
- **Development Period:** 2025-11-10 to 2025-12-16 (36 days)
- **Major Versions:** 2 (v1.0.x, v1.1.x)

---

## Contributors

- **BlueElliott** - Primary developer
- **Claude** - AI pair programmer (Co-Authored commits)
