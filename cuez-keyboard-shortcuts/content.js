// Cuez Keyboard Shortcuts Extension
// Adds custom keyboard shortcuts to Cuez.live

console.log('Cuez Keyboard Shortcuts extension loaded');

// Listen for keyboard events
document.addEventListener('keydown', function(event) {
    // Ignore if user is typing in an input field
    if (event.target.tagName === 'INPUT' ||
        event.target.tagName === 'TEXTAREA' ||
        event.target.isContentEditable) {
        return;
    }

    const key = event.key.toLowerCase();
    const ctrl = event.ctrlKey;
    const shift = event.shiftKey;
    const alt = event.altKey;

    console.log('Key pressed:', { key, ctrl, shift, alt });

    // Define keyboard shortcuts
    // Ctrl+Right Arrow - Next cue
    if (ctrl && key === 'arrowright') {
        event.preventDefault();
        console.log('Next cue shortcut triggered');
        clickButton('next', 'forward', 'cue-next');
    }

    // Ctrl+Left Arrow - Previous cue
    if (ctrl && key === 'arrowleft') {
        event.preventDefault();
        console.log('Previous cue shortcut triggered');
        clickButton('previous', 'back', 'cue-previous');
    }

    // Ctrl+Up Arrow - First/Top
    if (ctrl && key === 'arrowup') {
        event.preventDefault();
        console.log('First/Top shortcut triggered');
        clickButton('first', 'top', 'cue-first');
    }

    // Ctrl+Down Arrow - Last/Bottom
    if (ctrl && key === 'arrowdown') {
        event.preventDefault();
        console.log('Last/Bottom shortcut triggered');
        clickButton('last', 'bottom', 'cue-last');
    }

    // Space - Start/Stop timer
    if (key === ' ' && !ctrl && !shift && !alt) {
        event.preventDefault();
        console.log('Start/Stop timer shortcut triggered');
        clickButton('timer', 'play', 'pause', 'start', 'stop');
    }

    // Ctrl+Shift+R - Reset timer
    if (ctrl && shift && key === 'r') {
        event.preventDefault();
        console.log('Reset timer shortcut triggered');
        clickButton('reset');
    }
});

// Function to find and click a button based on text content or aria-label
function clickButton(...searchTerms) {
    console.log('Searching for button with terms:', searchTerms);

    // Try to find button by text content
    const buttons = document.querySelectorAll('button, [role="button"], .button, .btn');

    for (const button of buttons) {
        const text = button.textContent.toLowerCase();
        const ariaLabel = (button.getAttribute('aria-label') || '').toLowerCase();
        const title = (button.getAttribute('title') || '').toLowerCase();
        const className = (button.className || '').toLowerCase();

        for (const term of searchTerms) {
            const searchTerm = term.toLowerCase();
            if (text.includes(searchTerm) ||
                ariaLabel.includes(searchTerm) ||
                title.includes(searchTerm) ||
                className.includes(searchTerm)) {
                console.log('Found button:', button);
                button.click();
                showNotification(`Triggered: ${term}`);
                return true;
            }
        }
    }

    // Try finding by icon/svg
    const icons = document.querySelectorAll('svg, i, .icon');
    for (const icon of icons) {
        const parent = icon.closest('button, [role="button"], .button, .btn');
        if (parent) {
            const ariaLabel = (parent.getAttribute('aria-label') || '').toLowerCase();
            for (const term of searchTerms) {
                if (ariaLabel.includes(term.toLowerCase())) {
                    console.log('Found button by icon:', parent);
                    parent.click();
                    showNotification(`Triggered: ${term}`);
                    return true;
                }
            }
        }
    }

    console.log('Button not found');
    showNotification('Button not found', true);
    return false;
}

// Show a notification to the user
function showNotification(message, isError = false) {
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${isError ? '#f44336' : '#00bcd4'};
        color: white;
        border-radius: 6px;
        font-family: -apple-system, sans-serif;
        font-size: 14px;
        font-weight: 600;
        z-index: 999999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

console.log('Cuez Keyboard Shortcuts ready!');
console.log('Available shortcuts:');
console.log('- Ctrl+Right: Next cue');
console.log('- Ctrl+Left: Previous cue');
console.log('- Ctrl+Up: First cue');
console.log('- Ctrl+Down: Last cue');
console.log('- Space: Start/Stop timer');
console.log('- Ctrl+Shift+R: Reset timer');
