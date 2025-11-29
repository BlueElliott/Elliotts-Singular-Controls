# Elliott's Singular Controls v1.1.2

Major new module: **Cuez-to-CueiT Bridge** for automatic script synchronization from Cuez Automator to CueiT teleprompter!

## 🆕 New Features

### Cuez-to-CueiT Bridge Module

Automatically sync scripts from Cuez Automator to CueiT teleprompter with zero manual intervention.

**Key Features:**
- 🔄 **Automatic Script Synchronization** - Monitors Cuez and pushes scripts to CueiT in real-time
- 🔌 **Independent Cuez Connection** - Separate host/port settings (can use different Cuez instance)
- 📁 **File Browser** - Easy output path selection with browse button
- ⚡ **Smart Change Detection** - MD5 hashing prevents unnecessary updates
- 🎛️ **Configurable Polling** - 1-30 second intervals (default: 3 seconds)
- 📝 **Format Support** - RTF (recommended) or plain text output
- 🌐 **Standalone Page** - `/cuez-to-cueit/control` for external operators
- 📊 **Real-Time Status** - Live display of episode, story count, and sync status

**How It Works:**
1. User loads episode in Cuez Automator
2. Module detects change within 3 seconds (configurable)
3. Script formatted with CueiT sluglines (`[#] Slugline`)
4. File saved to configured location
5. CueiT auto-reloads - Done!

**API Endpoints:**
- `GET /cuez-to-cueit/status` - Current status
- `GET /cuez-to-cueit/config` - Get configuration
- `POST /cuez-to-cueit/config` - Update settings
- `POST /cuez-to-cueit/sync/now` - Manual sync
- `POST /cuez-to-cueit/sync/enable` - Start auto-sync
- `POST /cuez-to-cueit/sync/disable` - Stop auto-sync

## 📦 Installation

No installation needed - this is a portable executable!

1. Download `ElliottsSingularControls.exe` below
2. Run the executable
3. Access at `http://localhost:3113`
4. Go to `/modules` and enable "Cuez-to-CueiT Bridge"

## 🎯 What's Included

All previous features from v1.1.1 plus the new Cuez-to-CueiT Bridge:

- **TfL Line Status** - Live Transport for London updates
- **TriCaster Control** - DDR timer sync and control
- **Cuez Automator** - Full rundown control and navigation
- **iNews Cleaner** - Remove formatting grommets
- **Cuez-to-CueiT Bridge** - NEW! Automatic script sync

## 🔧 Requirements

- Windows 10 or later
- No Python installation required - fully standalone!

## 📖 Documentation

Full documentation in [SESSION_SUMMARY.md](https://github.com/BlueElliott/Elliotts-Singular-Controls/blob/main/SESSION_SUMMARY.md)

## 🐛 Bug Fixes

- Improved Cuez blocks display handling
- Fixed FastAPI import issues

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
