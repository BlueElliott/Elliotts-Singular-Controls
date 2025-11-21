"""
GUI Launcher for Singular Tweaks with system tray support.
"""
import os
import sys
import time
import threading
import webbrowser
import logging
import tkinter as tk
from tkinter import scrolledtext, messagebox
from pathlib import Path
import socket
import psutil
import pystray
from PIL import Image, ImageDraw
from io import StringIO

# Import needed functions
from singular_tweaks.core import effective_port, _runtime_version


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def kill_process_on_port(port: int) -> bool:
    """Kill any process using the specified port."""
    killed = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    print(f"Killing process {proc.info['name']} (PID: {proc.info['pid']}) on port {port}")
                    proc.kill()
                    killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return killed


class SingularTweaksGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Singular Tweaks")
        self.root.geometry("750x550")
        self.root.resizable(False, False)

        # Modern dark theme colors (inspired by CUEZ Automator)
        self.bg_dark = "#0a0a0a"
        self.bg_medium = "#1a1a1a"
        self.bg_card = "#1e1e1e"
        self.accent_teal = "#00bcd4"
        self.accent_teal_dark = "#0097a7"
        self.text_light = "#ffffff"
        self.text_gray = "#888888"
        self.button_blue = "#2196f3"
        self.button_green = "#4caf50"
        self.button_red = "#ff5252"
        self.button_gray = "#2a2a2a"

        self.root.configure(bg=self.bg_dark)

        # Icon for system tray
        self.icon = None
        self.server_thread = None
        self.server_running = False
        self.console_visible = False
        self.console_text = None
        self.log_handler = None

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_icon_image(self):
        """Create a simple icon for the system tray."""
        # Create a 64x64 image with teal colored circle
        width = 64
        height = 64

        image = Image.new('RGB', (width, height), self.bg_dark)
        dc = ImageDraw.Draw(image)
        dc.ellipse((8, 8, 56, 56), fill=self.accent_teal)
        dc.text((22, 22), "ST", fill=self.bg_dark)
        return image

    def create_rounded_rectangle(self, canvas, x1, y1, x2, y2, radius=15, **kwargs):
        """Draw a rounded rectangle on a canvas."""
        points = [
            x1+radius, y1,
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def create_rounded_button(self, parent, text, command, bg_color, width=180, height=50, state=tk.NORMAL):
        """Create a modern rounded button using canvas."""
        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=self.bg_dark,
            highlightthickness=0,
            bd=0
        )

        # Draw rounded rectangle
        radius = 12
        canvas.create_oval(0, 0, radius*2, radius*2, fill=bg_color, outline="")
        canvas.create_oval(width-radius*2, 0, width, radius*2, fill=bg_color, outline="")
        canvas.create_oval(0, height-radius*2, radius*2, height, fill=bg_color, outline="")
        canvas.create_oval(width-radius*2, height-radius*2, width, height, fill=bg_color, outline="")
        canvas.create_rectangle(radius, 0, width-radius, height, fill=bg_color, outline="")
        canvas.create_rectangle(0, radius, width, height-radius, fill=bg_color, outline="")

        # Add text
        text_id = canvas.create_text(
            width/2, height/2,
            text=text,
            fill=self.text_light if state == tk.NORMAL else self.text_gray,
            font=("Arial", 11, "bold")
        )

        # Bind click event
        if state == tk.NORMAL:
            canvas.bind("<Button-1>", lambda e: command())
            canvas.bind("<Enter>", lambda e: canvas.configure(cursor="hand2"))
            canvas.bind("<Leave>", lambda e: canvas.configure(cursor=""))

        canvas.button_state = state
        return canvas

    def setup_ui(self):
        """Setup the main UI with modern dark theme."""
        # Top section with branding
        top_frame = tk.Frame(self.root, bg=self.bg_dark, height=100)
        top_frame.pack(fill=tk.X, padx=0, pady=0)
        top_frame.pack_propagate(False)

        # Branding text (simple text logo like CUEZ)
        brand_label = tk.Label(
            top_frame,
            text="SINGULAR TWEAKS",
            font=("Arial", 24, "bold"),
            bg=self.bg_dark,
            fg=self.text_light,
            justify=tk.LEFT
        )
        brand_label.place(x=40, y=30)

        # Version badge (circular style)
        version_frame = tk.Frame(top_frame, bg=self.bg_medium)
        version_label = tk.Label(
            version_frame,
            text=f"v{_runtime_version()}",
            font=("Arial", 9),
            bg=self.bg_medium,
            fg=self.text_gray,
            padx=12,
            pady=6
        )
        version_label.pack()
        version_frame.place(x=40, y=70)

        # Main content area
        content_frame = tk.Frame(self.root, bg=self.bg_dark)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=(10, 30))

        # Port card with rounded corners
        port_card = tk.Frame(content_frame, bg=self.bg_card, height=120)
        port_card.pack(fill=tk.X, pady=(0, 25))
        port_card.pack_propagate(False)

        # Port display section
        port_display_frame = tk.Frame(port_card, bg=self.bg_card)
        port_display_frame.pack(pady=20)

        tk.Label(
            port_display_frame,
            text="SERVER PORT",
            font=("Arial", 9, "bold"),
            bg=self.bg_card,
            fg=self.text_gray
        ).pack()

        # Port number with teal highlight
        port_number_frame = tk.Frame(port_display_frame, bg=self.accent_teal)
        self.port_label = tk.Label(
            port_number_frame,
            text=str(effective_port()),
            font=("Arial", 32, "bold"),
            bg=self.accent_teal,
            fg=self.text_light,
            padx=30,
            pady=10
        )
        self.port_label.pack()
        port_number_frame.pack(pady=8)

        # Change port button (small, rounded)
        change_btn_canvas = tk.Canvas(
            port_display_frame,
            width=120,
            height=32,
            bg=self.bg_card,
            highlightthickness=0
        )
        radius = 16
        change_btn_canvas.create_oval(0, 0, radius*2, radius*2, fill=self.bg_medium, outline="")
        change_btn_canvas.create_oval(120-radius*2, 0, 120, radius*2, fill=self.bg_medium, outline="")
        change_btn_canvas.create_oval(0, 32-radius*2, radius*2, 32, fill=self.bg_medium, outline="")
        change_btn_canvas.create_oval(120-radius*2, 32-radius*2, 120, 32, fill=self.bg_medium, outline="")
        change_btn_canvas.create_rectangle(radius, 0, 120-radius, 32, fill=self.bg_medium, outline="")
        change_btn_canvas.create_rectangle(0, radius, 120, 32-radius, fill=self.bg_medium, outline="")
        change_btn_canvas.create_text(60, 16, text="Change Port", fill=self.text_gray, font=("Arial", 9))
        change_btn_canvas.bind("<Button-1>", lambda e: self.change_port())
        change_btn_canvas.bind("<Enter>", lambda e: change_btn_canvas.configure(cursor="hand2"))
        change_btn_canvas.bind("<Leave>", lambda e: change_btn_canvas.configure(cursor=""))
        change_btn_canvas.pack(pady=5)

        # Status message
        self.status_label = tk.Label(
            content_frame,
            text="● Server running on all interfaces",
            font=("Arial", 10),
            bg=self.bg_dark,
            fg=self.accent_teal
        )
        self.status_label.pack(pady=(0, 3))

        self.url_label = tk.Label(
            content_frame,
            text=f"http://127.0.0.1:{effective_port()}/",
            font=("Arial", 10),
            bg=self.bg_dark,
            fg=self.text_gray
        )
        self.url_label.pack(pady=(0, 30))

        # Action buttons (2x2 grid with better spacing)
        btn_container = tk.Frame(content_frame, bg=self.bg_dark)
        btn_container.pack()

        # Row 1
        row1 = tk.Frame(btn_container, bg=self.bg_dark)
        row1.pack(pady=8)

        self.launch_btn = self.create_rounded_button(
            row1, "Open Web GUI", self.launch_browser,
            self.button_blue, width=290, height=55, state=tk.DISABLED
        )
        self.launch_btn.pack(side=tk.LEFT, padx=8)

        self.console_toggle_btn = self.create_rounded_button(
            row1, "Open Console", self.toggle_console,
            self.button_gray, width=290, height=55
        )
        self.console_toggle_btn.pack(side=tk.LEFT, padx=8)

        # Row 2
        row2 = tk.Frame(btn_container, bg=self.bg_dark)
        row2.pack(pady=8)

        self.hide_btn = self.create_rounded_button(
            row2, "Hide to Tray", self.minimize_to_tray,
            self.button_gray, width=290, height=55
        )
        self.hide_btn.pack(side=tk.LEFT, padx=8)

        self.quit_btn = self.create_rounded_button(
            row2, "Quit Server", self.on_closing,
            self.button_red, width=290, height=55
        )
        self.quit_btn.pack(side=tk.LEFT, padx=8)

        # Console output (hidden by default, will be shown in new window)
        self.console_window = None

        # Auto-start server on launch
        self.root.after(500, self.start_server)

    def change_port(self):
        """Open dialog to change port."""
        from tkinter import simpledialog
        new_port = simpledialog.askinteger(
            "Change Port",
            "Enter new port number:",
            initialvalue=effective_port(),
            minvalue=1024,
            maxvalue=65535
        )
        if new_port and new_port != effective_port():
            # Update config
            from singular_tweaks.core import CONFIG, save_config
            CONFIG.port = new_port
            save_config(CONFIG)

            # Update UI
            self.port_label.config(text=str(new_port))
            self.url_label.config(text=f"e.g. http://127.0.0.1:{new_port}/")

            messagebox.showinfo(
                "Port Changed",
                f"Port changed to {new_port}. Please restart the application for changes to take effect."
            )

    def update_button_text(self, canvas, new_text):
        """Update text on a canvas button."""
        for item in canvas.find_all():
            if canvas.type(item) == "text":
                canvas.itemconfig(item, text=new_text)
                break

    def toggle_console(self):
        """Toggle console window visibility."""
        try:
            window_exists = self.console_window is not None and self.console_window.winfo_exists()
        except:
            window_exists = False

        if not window_exists:
            # Create console window
            self.console_window = tk.Toplevel(self.root)
            self.console_window.title("Console Output")
            self.console_window.geometry("800x400")
            self.console_window.configure(bg=self.bg_dark)

            # Console output
            self.console_text = scrolledtext.ScrolledText(
                self.console_window,
                bg="#1e1e1e",
                fg="#d4d4d4",
                font=("Consolas", 9),
                relief=tk.FLAT,
                wrap=tk.WORD
            )
            self.console_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Add initial status message
            port = effective_port()
            self.console_text.insert(tk.END, f"Singular Tweaks v{_runtime_version()}\n")
            self.console_text.insert(tk.END, "=" * 60 + "\n")
            if self.server_running:
                self.console_text.insert(tk.END, f"✓ Server running on http://0.0.0.0:{port}\n")
                self.console_text.insert(tk.END, f"  Access at: http://localhost:{port}\n")
            else:
                self.console_text.insert(tk.END, "⚠ Server not running\n")
            self.console_text.insert(tk.END, "=" * 60 + "\n\n")
            self.console_text.insert(tk.END, "Console output will appear here...\n\n")

            # Redirect stdout to console
            sys.stdout = ConsoleRedirector(self.console_text)
            sys.stderr = ConsoleRedirector(self.console_text)

            # Set up logging handler for the root logger
            self.log_handler = TkinterLogHandler(self.console_text)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
            self.log_handler.setFormatter(formatter)
            logging.getLogger().addHandler(self.log_handler)
            logging.getLogger().setLevel(logging.INFO)

            # Write a test message
            print(f"[Console] Console window opened at {time.strftime('%H:%M:%S')}")

            self.update_button_text(self.console_toggle_btn, "Close Console")
            self.console_visible = True
        else:
            # Close console window
            if self.log_handler:
                logging.getLogger().removeHandler(self.log_handler)
                self.log_handler = None
            self.console_window.destroy()
            self.console_window = None
            self.console_text = None
            self.update_button_text(self.console_toggle_btn, "Open Console")
            self.console_visible = False

    def start_server(self):
        """Start the server in a background thread."""
        port = effective_port()

        # Check if port is in use and kill it
        if is_port_in_use(port):
            response = messagebox.askyesno(
                "Port In Use",
                f"Port {port} is already in use (possibly another instance).\n\n"
                "Do you want to close it and start a new instance?"
            )
            if response:
                kill_process_on_port(port)
            else:
                return

        self.status_label.config(text=f"Starting server on port {port}...")

        # Start server in background thread
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        # Update UI after short delay
        self.root.after(2000, self._server_started)

    def _run_server(self):
        """Run the server (called in background thread)."""
        try:
            import uvicorn
            import logging
            from singular_tweaks.core import app, effective_port

            # Configure basic logging to avoid uvicorn formatter errors
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S',
                force=True
            )

            # Configure uvicorn with custom logging and access log enabled
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=effective_port(),
                log_level="info",
                access_log=True,  # Enable access log to see HTTP requests
                log_config=None  # Disable default log config
            )
            server = uvicorn.Server(config)
            print(f"[Server] Starting uvicorn server on port {effective_port()}")
            server.run()
        except Exception as e:
            print(f"[Server] Error starting server: {e}")
            import traceback
            traceback.print_exc()

    def enable_canvas_button(self, canvas, bg_color):
        """Enable a canvas button."""
        canvas.button_state = tk.NORMAL
        # Recreate the button with proper colors
        canvas.delete("all")
        width = int(canvas['width'])
        height = int(canvas['height'])
        radius = 12
        canvas.create_oval(0, 0, radius*2, radius*2, fill=bg_color, outline="")
        canvas.create_oval(width-radius*2, 0, width, radius*2, fill=bg_color, outline="")
        canvas.create_oval(0, height-radius*2, radius*2, height, fill=bg_color, outline="")
        canvas.create_oval(width-radius*2, height-radius*2, width, height, fill=bg_color, outline="")
        canvas.create_rectangle(radius, 0, width-radius, height, fill=bg_color, outline="")
        canvas.create_rectangle(0, radius, width, height-radius, fill=bg_color, outline="")
        canvas.create_text(width/2, height/2, text="Open Web GUI", fill=self.text_light, font=("Arial", 11, "bold"))
        canvas.bind("<Button-1>", lambda e: self.launch_browser())
        canvas.bind("<Enter>", lambda e: canvas.configure(cursor="hand2"))
        canvas.bind("<Leave>", lambda e: canvas.configure(cursor=""))

    def _server_started(self):
        """Update UI after server starts."""
        port = effective_port()
        self.server_running = True
        self.status_label.config(text=f"● Server running on all interfaces")
        self.url_label.config(text=f"http://127.0.0.1:{port}/")
        self.enable_canvas_button(self.launch_btn, self.button_blue)

    def launch_browser(self):
        """Open the web GUI in default browser."""
        port = effective_port()
        webbrowser.open(f"http://localhost:{port}")

    def minimize_to_tray(self):
        """Minimize window to system tray."""
        self.root.withdraw()
        if not self.icon:
            image = self.create_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem("Show Window", self.show_window),
                pystray.MenuItem("Launch GUI", self.launch_browser),
                pystray.MenuItem("Quit", self.quit_app)
            )
            self.icon = pystray.Icon("SingularTweaks", image, "Singular Tweaks", menu)
            threading.Thread(target=self.icon.run, daemon=True).start()

    def show_window(self):
        """Restore window from system tray."""
        self.root.deiconify()
        if self.icon:
            self.icon.stop()
            self.icon = None

    def on_closing(self):
        """Handle window close event."""
        if messagebox.askokcancel("Quit", "Do you want to quit? Server will stop."):
            self.quit_app()

    def quit_app(self):
        """Quit the application."""
        if self.icon:
            self.icon.stop()
        self.root.quit()
        sys.exit(0)

    def run(self):
        """Start the GUI main loop."""
        print(f"Singular Tweaks v{_runtime_version()}")
        print("GUI Launcher started. Click 'Start Server' to begin.")
        self.root.mainloop()


class ConsoleRedirector:
    """Redirect stdout/stderr to a Text widget."""

    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = StringIO()

    def write(self, message):
        try:
            self.text_widget.insert(tk.END, message)
            self.text_widget.see(tk.END)
        except:
            pass  # Widget may be destroyed
        self.buffer.write(message)

    def flush(self):
        pass


class TkinterLogHandler(logging.Handler):
    """Custom logging handler that writes to a Tkinter Text widget."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        try:
            msg = self.format(record) + '\n'
            self.text_widget.insert(tk.END, msg)
            self.text_widget.see(tk.END)
        except:
            pass  # Widget may be destroyed


def main():
    """Entry point for GUI launcher."""
    app = SingularTweaksGUI()
    app.run()


if __name__ == "__main__":
    main()
