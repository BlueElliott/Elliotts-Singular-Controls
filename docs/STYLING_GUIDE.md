# Singular Tweaks - Styling Guide

This guide explains how to customize the look and feel of Singular Tweaks. The application has two main interfaces: the **GUI Launcher** (desktop window) and the **Web Interface** (browser-based).

---

## 🎨 Color Scheme

Both interfaces use a consistent teal and dark theme:

```
Teal Accent:     #00bcd4
Dark Background: #1e1e1e
Medium Gray:     #2b2b2b
Border Gray:     #424242
Light Text:      #f5f5f5
Gray Text:       #b0b0b0

Buttons:
- Blue:   #3f51b5
- Green:  #4caf50
- Red:    #f44336
- Gray:   #424242
```

---

## 🖥️ GUI Launcher Styling

**File:** `singular_tweaks/gui_launcher.py`

### Quick Color Changes

Find the `__init__` method around line 43-58:

```python
# Modern dark theme colors (inspired by CUEZ Automator)
self.bg_dark = "#1e1e1e"        # Main window background
self.bg_medium = "#2b2b2b"      # Card backgrounds
self.accent_teal = "#00bcd4"    # Port display box, highlights
self.text_light = "#ffffff"     # Main text color
self.text_gray = "#b0b0b0"      # Secondary text
self.button_blue = "#3f51b5"    # Action buttons
self.button_green = "#4caf50"   # Success buttons
self.button_red = "#f44336"     # Quit/danger buttons
self.button_gray = "#424242"    # Neutral buttons
```

**To change colors:** Simply replace the hex color codes with your preferred values.

### Common Tweaks

#### Change the port display box color:
```python
self.accent_teal = "#YOUR_COLOR"  # Line ~52
```

#### Change window size:
```python
self.root.geometry("700x500")  # Line 46 - format: "WIDTHxHEIGHT"
```

#### Change branding text:
```python
text="SINGULAR\nTWEAKS",  # Lines 93-94
```

#### Change version badge appearance:
```python
# Line 102-111
version_label = tk.Label(
    top_frame,
    text=f"v{_runtime_version()}",
    font=("Arial", 9),
    bg=self.bg_medium,
    fg=self.text_gray,
    padx=8,
    pady=4
)
```

---

## 🌐 Web Interface Styling

**File:** `singular_tweaks/core.py`

### Quick Color Changes

Find the `_base_style()` function around line 373-379:

```python
def _base_style() -> str:
    theme = CONFIG.theme or "dark"
    if theme == "light":
        bg = "#f5f5f5"; fg = "#111"; card_bg = "#fff"; border = "#ccc"; accent = "#00bcd4"
    else:
        # Teal theme matching ITN interface
        bg = "#1e1e1e"; fg = "#f5f5f5"; card_bg = "#2b2b2b"; border = "#424242"; accent = "#00bcd4"
```

**Variables:**
- `bg` - Page background color
- `fg` - Main text color
- `card_bg` - Background for cards/fieldsets
- `border` - Border colors
- `accent` - Links, buttons, table headers

**To change colors:** Replace the hex values in either the `light` or `dark` theme section.

### Common Tweaks

#### Change accent color (buttons, links, table headers):
```python
accent = "#YOUR_COLOR"  # Line 379 for dark theme, 376 for light
```

#### Change background colors:
```python
bg = "#YOUR_BACKGROUND"      # Main page background
card_bg = "#YOUR_CARD_BG"    # Fieldset/card backgrounds
```

#### Adjust fonts:
Around line 389:
```python
"  body { font-family: 'ITVReem', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;"
```

#### Button styling:
Around line 403:
```python
f"  button {{ margin-top:0.75rem; padding:0.4rem 0.8rem; cursor:pointer;"
f" background:{accent}; color:#fff; border:none; border-radius: 3px; }}"
```

---

## 📝 Simple Workflow for Customization

### Option 1: Edit Colors Yourself
1. Open the file in a text editor
2. Find the color section using the line numbers above
3. Replace hex codes (`#00bcd4`) with your colors
4. Save the file
5. Restart the application

### Option 2: Describe Changes to Claude
Create a simple text file with your desired changes:

```
STYLING_CHANGES.txt
===================
- Change teal accent to purple: #9c27b0
- Make background lighter: #2d2d2d
- Change button color to orange: #ff5722
- Make text slightly dimmer: #e0e0e0
```

Then give this to Claude with the instruction: "Update the styling using these colors from STYLING_CHANGES.txt"

---

## 🔍 Finding Elements

### GUI Launcher Elements

- **Window title**: Line 45 - `self.root.title("Singular Tweaks")`
- **Branding**: Lines 91-99 - `brand_label`
- **Version badge**: Lines 102-111 - `version_label`
- **Port display**: Lines 152-159 - `self.port_label`
- **Buttons**: Lines 200-267 - Button definitions

### Web Interface Elements

- **Navigation**: Line 361-370 - `_nav_html()`
- **Page styles**: Line 373-425 - `_base_style()`
- **Version badge**: Look for `.version-badge` around line 410
- **Tables**: Lines 417-419 - Table styling
- **Forms**: Lines 398-404 - Input and button styling

---

## ⚠️ Important Notes

1. **Always backup files** before editing
2. **Test changes** by running the application after edits
3. **Hex colors** must start with `#` followed by 6 characters (e.g., `#00bcd4`)
4. **Restart required** for changes to take effect
5. **Git status** - Check `git status` to see what you've changed

---

## 🆘 If Something Breaks

1. Check for **typos** in hex codes
2. Make sure **quotes match** (`"` or `'`)
3. Verify **indentation** in Python files (use spaces, not tabs)
4. Restore from git: `git checkout -- filename.py`

---

## 📚 Additional Resources

- **Color picker**: Use Windows Color Picker (Win + Shift + C on Windows 11) or visit https://htmlcolorcodes.com/
- **Tkinter docs**: https://docs.python.org/3/library/tkinter.html
- **CSS reference**: For web styling - https://developer.mozilla.org/en-US/docs/Web/CSS

---

**Created:** 2025-11-20
**Version:** 1.0.12
