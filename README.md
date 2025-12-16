# Elliott's Singular Controls

> **A premium desktop application for controlling Singular.live graphics with TfL integration**

[![Build Status](https://github.com/BlueElliott/Elliotts-Singular-Controls/actions/workflows/build.yml/badge.svg)](https://github.com/BlueElliott/Elliotts-Singular-Controls/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A helper UI and HTTP API that makes it easy to control Singular.live compositions via simple HTTP GET requests. Perfect for integration with automation systems, OBS, vMix, Companion, and other broadcast tools.

## Features

- **Web-based Control Panel** - Configure and test your Singular compositions
- **Simple HTTP API** - Trigger compositions with GET requests
- **TfL Integration** - Fetch and display London transport statuses with official branding
- **TriCaster Control** - DDR-to-Singular timer sync with auto-sync
- **Cuez Automator** - Full rundown control, navigation, and macro execution
- **CasparCG Control** - Complete AMCP protocol integration for graphics and media
- **iNews Cleaner** - Remove formatting grommets from iNews exports
- **Data Stream Support** - Send data to Singular's Data Stream
- **Multi-Token Support** - Manage multiple Singular Control App tokens
- **Desktop GUI** - Native Windows application with system tray support
- **Connection Monitoring** - Auto-reconnect overlay when server connection is lost

## Installation

### Windows (Recommended)

**Portable Executable (Easiest)**
1. Download `ElliottsSingularControls.exe` from [Releases](https://github.com/BlueElliott/Elliotts-Singular-Controls/releases)
2. Double-click to run - no installation needed!
3. The application runs from the system tray

### Python (All Platforms)

```bash
# Install via pip
pip install elliotts-singular-controls

# Run with GUI
python -m elliotts_singular_controls.gui_launcher

# Or run server only
python -m elliotts_singular_controls
```

### From Source

```bash
git clone https://github.com/BlueElliott/Elliotts-Singular-Controls.git
cd Elliotts-Singular-Controls
pip install -r requirements.txt
python -m elliotts_singular_controls.gui_launcher
```

## Quick Start

1. **Start the application**
   - Windows: Run `ElliottsSingularControls.exe`
   - Python: Run `python -m elliotts_singular_controls.gui_launcher`

2. **Open the web interface**
   - Click "Open Web GUI" in the desktop app, or
   - Navigate to `http://localhost:3113`

3. **Configure Singular**
   - Go to Settings page
   - Enter your Singular Control App Token
   - Click "Save"

4. **Control your compositions**
   - Visit the Commands page to see all available controls
   - Use the provided URLs in your automation system

## Web Interface Pages

| Page | URL | Description |
|------|-----|-------------|
| Home | `http://localhost:3113/` | Overview with quick actions and token status |
| Modules | `http://localhost:3113/modules` | TfL line status controls with manual input |
| TfL Control | `http://localhost:3113/tfl/control` | Standalone TfL page for external operators |
| Commands | `http://localhost:3113/commands` | All available Singular control commands |
| Settings | `http://localhost:3113/settings` | Configure tokens, ports, and preferences |

## TfL Integration

### How It Works

1. **Automatic Fetch** - Click "Fetch Live TfL Status" to get real-time data from TfL API
2. **Manual Input** - Override any line's status with custom text
3. **Visual Feedback** - Input fields turn red when status isn't "Good Service"
4. **Data Stream** - Send status data to Singular.live Data Stream for overlay display

### Supported Lines

**Underground:** Bakerloo, Central, Circle, District, Hammersmith & City, Jubilee, Metropolitan, Northern, Piccadilly, Victoria, Waterloo & City

**Overground & Other:** Liberty, Lioness, Mildmay, Suffragette, Weaver, Windrush, DLR, Elizabeth line, Tram

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface home |
| `/modules` | GET | TfL modules page |
| `/commands` | GET | List all available commands |
| `/settings` | GET | Application settings |
| `/health` | GET | Health check (for monitoring) |

### Singular Control Endpoints

```bash
# Animate composition IN
GET http://localhost:3113/{composition-key}/in

# Animate composition OUT
GET http://localhost:3113/{composition-key}/out

# Set a field value
GET http://localhost:3113/{composition-key}/set?field=Name&value=John%20Smith
```

### TfL Endpoints

```bash
# Get current TfL statuses
GET http://localhost:3113/status

# Send data to Data Stream
POST http://localhost:3113/update

# Manual status update
POST http://localhost:3113/manual
```

## Desktop Application

The desktop GUI provides:

- **Server Status** - Visual pulse indicator shows server health
- **Runtime Display** - See how long the server has been running
- **Port Configuration** - Change the server port (default: 3113)
- **Console View** - Toggle server logs for debugging
- **System Tray** - Minimize to tray for background operation

### Keyboard Shortcuts

- Click "Open Web GUI" to launch browser
- Click "Open Console" to view server logs
- Click "Restart Server" to restart without closing the app
- Click "Hide to Tray" to minimize to system tray

## Configuration

Settings are saved to `elliotts_singular_controls_config.json`:

```json
{
  "singular_tokens": ["token1", "token2"],
  "singular_stream_url": "https://...",
  "enable_datastream": true,
  "port": 3113
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SINGULAR_CONTROLS_PORT` | Server port | 3113 |

## Troubleshooting

**Port already in use?**
- Change the port in Settings, or
- Click "Change Port" in the desktop app

**Can't connect to Singular?**
- Verify your Control App Token is correct
- Check your internet connection
- Try refreshing the command list

**TfL data not updating?**
- Check your internet connection
- Manual input will override automatic fetch

**Connection Lost overlay appears?**
- The server may have crashed - check the console
- Click "Restart Server" in the desktop app

## Development

### Setup Development Environment

```bash
git clone https://github.com/BlueElliott/Elliotts-Singular-Controls.git
cd Elliotts-Singular-Controls
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Project Structure

```
Elliotts-Singular-Controls/
├── elliotts_singular_controls/
│   ├── __init__.py          # Version and exports
│   ├── __main__.py           # Entry point
│   ├── core.py               # FastAPI app, all HTML/CSS/JS
│   └── gui_launcher.py       # Desktop GUI with system tray
├── static/                   # Icons and fonts
├── .github/workflows/        # CI/CD
├── ElliottsSingularControls.spec  # PyInstaller config
└── requirements.txt
```

### Build Executable

```bash
pyinstaller ElliottsSingularControls.spec
# Output: dist/ElliottsSingularControls-1.1.5.exe
```

## Version History

### v1.1.5 (Current)
- CasparCG control module with AMCP protocol support
- Complete graphics template and media playback control
- Standalone CasparCG control page

### v1.1.4
- Fixed TfL standalone page input color changes
- Added Cuez keyboard shortcuts for navigation

### v1.1.3
- Singular counter control functionality
- Unified button UI across all modules

### v1.1.1
- TriCaster module with DDR-to-Singular timer sync
- Auto-sync feature with smart change detection
- Cuez Automator full integration
- iNews Cleaner module

### v1.1.0
- Improved desktop GUI with smooth animated pulse indicator
- Fixed TfL manual input background color on modules page
- Enhanced UI consistency across all pages

### v1.0.x
- Initial release with core functionality
- Web interface for Singular.live control
- TfL integration with Data Stream support
- Multi-token management

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

- **Issues**: [GitHub Issues](https://github.com/BlueElliott/Elliotts-Singular-Controls/issues)
- **Discussions**: [GitHub Discussions](https://github.com/BlueElliott/Elliotts-Singular-Controls/discussions)

---

**Made with care by BlueElliott**
