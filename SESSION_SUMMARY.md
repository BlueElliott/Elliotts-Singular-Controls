# Elliott's Singular Controls - Session Summary

## Project Overview
**Name:** Elliott's Singular Controls (formerly Singular Tweaks)
**Version:** 1.0.14
**Repository:** https://github.com/BlueElliott/Elliotts-Singular-Controls

A premium desktop application for controlling Singular.live graphics with TfL integration.

---

## What Was Done (v1.0.14)

### 1. TFL Manual Input Redesign
- Fixed CSS specificity issues where base styles were overriding custom `.tfl-input` styles
- Added `!important` to all TFL input CSS properties to ensure proper styling
- The TFL manual input section now has uniform styling matching the standalone page
- Input fields have teal background (#0c6473), proper padding, and consistent appearance

### 2. Click-to-Copy for HTTP Commands
- Added `.copyable` CSS class for command URLs
- Implemented `copyToClipboard()` JavaScript function
- Users can now click any command URL to copy it to clipboard
- Visual feedback on hover (cursor: pointer, underline)

### 3. Standalone TFL Control Page
- Created new endpoint `/tfl/control` for external operators
- Clean, self-contained interface without main app navigation
- Professional dark theme with TfL branding colours
- Direct access URL: `http://localhost:3113/tfl/control`

### 4. "Open Standalone" Button
- Added button in TFL module section on the modules page
- Opens `/tfl/control` in a new tab
- Styled consistently with the rest of the UI

### 5. Rebranding
- Renamed from "Singular Tweaks" to "Elliott's Singular Controls"
- Updated all files: `__init__.py`, `pyproject.toml`, `installer.nsi`, `SingularTweaks.spec`
- Package name: `elliotts-singular-controls`
- Executable name: `ElliottsSingularControls-{VERSION}.exe`

### 6. Versioned Executable
- Exe filename now includes version number (e.g., `ElliottsSingularControls-1.0.14.exe`)
- Makes it easy for users to identify which version they have installed

### 7. Custom Application Icon
- Added `static/esc_icon.ico` for the executable
- Professional branding in Windows taskbar and file explorer

### 8. Repository Organization
- Moved build files to `scripts/` folder: `SingularTweaks.spec`, `installer.nsi`
- Moved dev docs to `docs/` folder: `STYLING_GUIDE.md`, `requirements-dev.txt`
- Removed SESSION_SUMMARY.md from git tracking (local dev file only)
- Cleaner root directory with only essential files

---

## Repository Structure (Clean)

```
Elliotts-Singular-Controls/
├── .github/workflows/     # GitHub Actions (build.yml)
├── docs/                  # Developer documentation
│   ├── STYLING_GUIDE.md
│   └── requirements-dev.txt
├── scripts/               # Build configuration
│   ├── SingularTweaks.spec
│   └── installer.nsi
├── singular_tweaks/       # Main Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── core.py
│   └── gui_launcher.py
├── static/                # Static assets (fonts, icons)
├── .gitignore
├── MANIFEST.in
├── pyproject.toml
├── README.md
└── requirements.txt
```

---

## Key Technical Details

### CSS Specificity Fix
The TFL input styling wasn't applying because base styles `input, select { width: 100%; ... }` were overriding custom classes. Fixed by using:
```css
input.tfl-input {
  flex: 1 !important;
  padding: 12px 14px !important;
  /* ... all properties with !important */
}
```

### Server Restart Required
When making changes to `core.py`, the FastAPI server must be restarted for changes to appear. The development server doesn't auto-reload embedded HTML/CSS.

### GitHub Actions Workflow
- Builds Windows executable using PyInstaller
- Creates GitHub Release with versioned exe
- Publishes to PyPI (if token configured)
- Release notes auto-generated from commits

---

## Files Modified in v1.0.14

1. `singular_tweaks/core.py` - TFL styling, click-to-copy, /tfl/control endpoint
2. `singular_tweaks/__init__.py` - Version bump, new name
3. `scripts/SingularTweaks.spec` - Versioned exe name, icon
4. `scripts/installer.nsi` - New branding
5. `pyproject.toml` - Package name update
6. `.github/workflows/build.yml` - Updated paths and exe name pattern
7. `.gitignore` - Added SESSION_SUMMARY.md

---

## How to Build

```bash
# Install dependencies
pip install -r requirements.txt

# Build standalone executable
pyinstaller scripts/SingularTweaks.spec

# Output: dist/ElliottsSingularControls-1.0.14.exe
```

---

## Next Steps (Potential)
- Add more TfL data integrations
- Implement additional Singular.live control features
- Create macOS/Linux builds
- Add automated testing
