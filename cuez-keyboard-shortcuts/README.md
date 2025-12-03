# Cuez Keyboard Shortcuts Extension

A Chrome/Edge browser extension that adds custom keyboard shortcuts to Cuez.live for cueing and timing control.

## Installation

1. Open Chrome or Edge browser
2. Go to `chrome://extensions/` (or `edge://extensions/`)
3. Enable "Developer mode" in the top right
4. Click "Load unpacked"
5. Select the `cuez-keyboard-shortcuts` folder

## Keyboard Shortcuts

- **Ctrl + Right Arrow**: Next cue
- **Ctrl + Left Arrow**: Previous cue
- **Ctrl + Up Arrow**: First cue
- **Ctrl + Down Arrow**: Last cue
- **Space**: Start/Stop timer
- **Ctrl + Shift + R**: Reset timer

## Testing

1. Install the extension
2. Open https://app.cuez.live/project/episodes
3. Open browser console (F12) to see debug messages
4. Try the keyboard shortcuts
5. You'll see notifications in the top-right when shortcuts are triggered

## How It Works

The extension injects JavaScript into Cuez.live pages that:
- Listens for keyboard shortcuts
- Finds the appropriate buttons in the Cuez interface
- Clicks them programmatically
- Shows visual feedback

## Customization

To change the keyboard shortcuts, edit the `content.js` file and look for the key detection logic around line 20-50.
