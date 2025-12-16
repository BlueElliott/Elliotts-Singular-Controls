# Elliott's Singular Controls v1.1.6

Major improvements to error handling, user feedback, and update notifications!

## 🆕 New Features

### Comprehensive Error Handling System

**Standardized Error Responses**
- Consistent error format across all API endpoints
- Structured error details with type, module, timestamp, and context
- Automatic crash logging for unexpected errors

**Smart HTTP Retry Logic**
- Automatic retry with exponential backoff (3 attempts: 0.3s, 0.6s, 1.2s)
- Handles transient network failures gracefully
- Prevents unnecessary error notifications for recoverable issues

**Toast Notification System**
- Non-intrusive notifications in top-right corner
- 4 notification types: success, error, warning, info
- Auto-dismiss after 4 seconds or manual close
- Smooth slide-in/fade-out animations
- Click-to-close functionality

**Connection Health Tracking**
- Per-module health monitoring (TfL, TriCaster, Cuez, Singular, CasparCG)
- Track success/failure rates and last error messages
- Health status API endpoints
- Real-time connection status visibility

### Visual Update Notifications

**Smart Update Banner**
- Purple gradient banner at top of page when updates are available
- Displays new version number with direct download link
- Auto-checks version on page load
- localStorage persistence - dismiss notifications per version
- Won't show again for dismissed versions
- Automatically reappears for newer versions

**Version Check Improvements**
- Fixed GitHub repository URL in version check endpoint
- Better version comparison logic
- Clear "up to date" vs "update available" messaging

## ✨ Improvements

### Updated All API Modules
All HTTP requests now use the new error handling system:
- **TfL Module** - Improved line status fetching with retry logic
- **TriCaster Module** - Better connection error messages
- **Cuez Module** - Enhanced request handling and error context
- **Singular API** - All 7+ functions updated with safe HTTP wrapper
- **CasparCG Module** - Robust AMCP command error handling

### User Experience
- Better error messages with actionable context
- Visual feedback for all user actions
- No more silent failures
- Professional error handling without intrusive dialogs

### API Enhancements
New health monitoring endpoints:
- `GET /health/modules` - Get connection health for all modules
- `GET /health/modules?module=tfl` - Get health for specific module
- `POST /health/modules/{module}/clear` - Clear health tracking

## 🐛 Bug Fixes

- Fixed GitHub repository URL in version check (was pointing to old "Singular-Tweaks")
- Improved error handling for network timeouts
- Better handling of malformed API responses
- Fixed edge cases in version comparison logic

## 📦 Installation

No installation needed - this is a portable executable!

1. Download `ElliottsSingularControls-1.1.6.exe` below
2. Run the executable
3. Access at `http://localhost:3113`
4. Enjoy improved error handling and update notifications!

## 🎯 What's Included

All previous features from v1.1.5 plus comprehensive error handling:

- **Singular Controls** - IN/OUT triggers and full control node support
- **TfL Line Status** - Live Transport for London updates
- **TriCaster Control** - DDR timer sync and control
- **Cuez Automator** - Full rundown control and navigation
- **CasparCG Control** - AMCP protocol graphics and media control
- **iNews Cleaner** - Remove formatting grommets
- **Enhanced Error Handling** - NEW! Toast notifications and retry logic
- **Update Notifications** - NEW! Visual banner when updates available

## 🔧 Requirements

- Windows 10 or later
- No Python installation required - fully standalone!

## 📖 Documentation

Full documentation in [SESSION_SUMMARY.md](https://github.com/BlueElliott/Elliotts-Singular-Controls/blob/main/SESSION_SUMMARY.md)

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
