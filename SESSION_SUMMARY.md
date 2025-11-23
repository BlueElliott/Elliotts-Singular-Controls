# Elliott's Singular Controls - Session Summary

## Project Overview
**Name:** Elliott's Singular Controls (formerly Singular Tweaks)
**Version:** 1.1.0
**Repository:** https://github.com/BlueElliott/Elliotts-Singular-Controls

A premium desktop application for controlling Singular.live graphics with TfL integration.

---

## What's New in v1.1.0

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
│   ├── __init__.py         # Version defined here (1.1.0)
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

### PyInstaller Spec File Location
**IMPORTANT:** The `ElliottsSingularControls.spec` file MUST be in the repository root directory.

PyInstaller resolves relative paths from the spec file's location. The GitHub Actions workflow runs:
```yaml
pyinstaller ElliottsSingularControls.spec
```

### PIL Anti-Aliased Pulse Animation
The pulse indicator uses PIL for smooth graphics:

```python
# Draw at 4x resolution
big_size = 40 * 4  # 160 pixels

# Create image and draw circles
img = Image.new('RGB', (big_size, big_size), bg_color)
draw = ImageDraw.Draw(img)
draw.ellipse([...], outline=color, width=ring_width)

# Resize with anti-aliasing
img = img.resize((40, 40), Image.LANCZOS)

# Convert to PhotoImage for Tkinter
self.pulse_image = ImageTk.PhotoImage(img)
```

Key: Background color must match exactly (#1a1a1a = rgb(26, 26, 26))

### Ripple Animation Logic
```python
# Phase offsets create outward ripple effect
center_phase = self.pulse_angle
inner_phase = self.pulse_angle - 90   # 90 degree delay
outer_phase = self.pulse_angle - 180  # 180 degree delay

# Opacity calculated from sine wave (0 to 1)
opacity = (math.sin(math.radians(phase)) + 1) / 2

# Color blending simulates transparency
color = blend(bg_color, blue_color, opacity)
```

### CSS Specificity for TFL Inputs
- **modules page:** `.tfl-input { background: #0c6473; }` - NO `!important`
- **standalone page:** `.line-input { background: #0c6473; }` - NO `!important`

JavaScript changes background to `#db422d` (red) for non-"Good Service" values.

### Version Bumping
Version is defined in `elliotts_singular_controls/__init__.py`:
```python
__version__ = "1.1.0"
```

Also update fallback version in `ElliottsSingularControls.spec`.

---

## Key Files and Their Purposes

### `elliotts_singular_controls/core.py`
- **Lines 1-150:** Imports, constants, TFL line definitions and colours
- **Lines 500-600:** Base CSS styles (`_base_style()` function)
- **Lines 780-850:** TFL/DataStream API endpoints
- **Lines 1000-1110:** Home page (`/`)
- **Lines 1112-1500:** Modules page (`/modules`)
- **Lines 1508-1632:** Standalone TFL control page (`/tfl/control`)
- **Lines 1635-1770:** Commands page (`/commands`)
- **Lines 1771-1890:** Settings page (`/settings`)

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
- Attempts PyPI publish (requires `PYPI_API_TOKEN` secret)

---

## How to Build Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m elliotts_singular_controls.gui_launcher

# Build standalone executable
pyinstaller ElliottsSingularControls.spec
# Output: dist/ElliottsSingularControls-1.1.0.exe
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
   git tag v1.1.0
   git push origin v1.1.0
   ```
7. **Monitor GitHub Actions:** https://github.com/BlueElliott/Elliotts-Singular-Controls/actions

---

## Web Interface URLs

When running locally on port 3113:
- **Home:** http://localhost:3113/
- **Modules (TFL):** http://localhost:3113/modules
- **Standalone TFL Control:** http://localhost:3113/tfl/control
- **Commands:** http://localhost:3113/commands
- **Settings:** http://localhost:3113/settings

---

## Common Issues and Solutions

### Issue: TFL input background not changing color
**Solution:** Check that CSS for `.tfl-input` doesn't have `!important` on background.

### Issue: PyInstaller can't find `__main__.py`
**Solution:** Ensure `ElliottsSingularControls.spec` is in repository ROOT.

### Issue: Pulse indicator has visible box/border
**Solution:** Background color in PIL must match exactly: rgb(26, 26, 26). Label needs `bd=0, highlightthickness=0`.

### Issue: Rounded rectangles have seam lines
**Solution:** Use `outline=fill` for all canvas shapes to eliminate gaps.

### Issue: GitHub Actions build fails
**Solution:** Check error in Actions log. Common issues:
- Spec file path wrong
- Missing dependencies in requirements.txt
- Version import failing

---

## Desktop GUI Features

### Pulse Indicator
- **Running:** Blue rippling animation (3 elements)
- **Stopped:** Static gray circles
- **Animation:** 40ms refresh rate, 8 degree increments

### Port Card
- Displays current server port
- Click "Change Port" to modify
- Rounded rectangle with smooth edges

### Buttons
- **Open Web GUI** - Blue, launches browser
- **Open Console** - Gray, shows server logs
- **Restart Server** - Orange, restarts without closing
- **Hide to Tray** - Gray, minimizes to system tray
- **Quit Server** - Red, closes application

---

## Version History

### v1.1.0 (Current)
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
