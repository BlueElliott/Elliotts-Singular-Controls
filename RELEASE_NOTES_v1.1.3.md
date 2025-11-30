# Elliott's Singular Controls v1.1.3 - UI Polish & Counter Control

Enhanced UI consistency and added full support for Singular counter control nodes.

## 🆕 New Features

### Counter Control Support
Control Singular counter assets (like Take counters) via HTTP API with increment/decrement functionality.

**Key Features:**
- ⬆️ **Increment/Decrement** - Increase or decrease counter values via HTTP GET
- 🎯 **Direct Set** - Set counter to specific value
- 🔄 **Read-Modify-Write** - Smart handling using Singular API current state
- 🌐 **Generic Implementation** - Works with any counter control node in your compositions

**Counter Endpoints:**
- `GET /singular/counter/control?control_node_id=Take&action=increment&subcomposition_name=Clock` - Increment counter
- `GET /singular/counter/control?control_node_id=Take&action=decrement&subcomposition_name=Clock` - Decrement counter
- `GET /singular/counter/control?control_node_id=Take&action=set&value=10&subcomposition_name=Clock` - Set to specific value

### All Singular Control Types Supported
Full support for every Singular control node type:
- 🔢 **Counter** - Increment/decrement/set operations
- 🔘 **Button** - Execute button triggers
- ☑️ **Checkbox** - ON/OFF toggles
- 🎨 **Color** - Hex, RGBA, and named color values
- 📋 **Selection** - Dropdown/list selection options
- ⏱ **Timecontrol** - Start/stop/duration controls
- 🖼 **Image** - Image URL updates
- 🔊 **Audio** - Audio URL updates
- 🔢 **Number** - Numeric values with constraints

## ✨ UI Improvements

### Unified Button Styling
All command buttons now use consistent house style:
- 🎨 **Cyan Theme** - Unified #00bcd4 color (was mixed green/cyan)
- 🖱 **Hover Effects** - Consistent hover (#0097a7) and active (#00838f) states
- ✨ **Visual Polish** - Professional, cohesive appearance

### Direct Command Execution
Buttons now fire commands in-page instead of opening new tabs:
- ⚡ **Instant Execution** - Click button to trigger command immediately
- ✅ **Visual Feedback** - Shows loading (...), success (✓), or error (✗) states
- 📋 **URL Copying** - Click code elements to copy URLs for automation
- 🚫 **No Tab Spam** - Clean, modern UX without browser tab clutter

### Enhanced Commands Page
- 🎯 **Smart Buttons** - All control buttons provide real-time feedback
- 📊 **Type-Specific UI** - Each control type displays with appropriate interface
- 🏷 **Field Type Icons** - Visual indicators for counter, button, checkbox, color, etc.
- 🔄 **Live Updates** - Immediate response with status indicators

## 🐛 Bug Fixes

- Fixed GUI launcher window height - quit button no longer cut off
- Removed unnecessary scrollbar on token input fields
- Improved token display with ellipsis for long values

## 📦 Installation

No installation needed - this is a portable executable!

1. Download `ElliottsSingularControls.exe` below
2. Run the executable
3. Access at `http://localhost:3113`
4. Configure your Singular tokens and start controlling!

## 🎯 What's Included

All features from previous versions plus new counter controls:

- **Singular Controls** - IN/OUT triggers and full control node support
- **TfL Line Status** - Live Transport for London updates
- **TriCaster Control** - DDR timer sync and control
- **Cuez Automator** - Full rundown control and navigation
- **Cuez-to-CueiT Bridge** - Automatic script synchronization
- **iNews Cleaner** - Remove formatting grommets

## 🔧 Requirements

- Windows 10 or later
- No Python installation required - fully standalone!

## 📖 Documentation

Full documentation in [SESSION_SUMMARY.md](https://github.com/BlueElliott/Elliotts-Singular-Controls/blob/main/SESSION_SUMMARY.md)

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
