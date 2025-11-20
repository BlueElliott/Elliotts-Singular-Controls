"""
GUI Launcher for Singular Tweaks with system tray support.
"""
import os
import sys
import threading
import webbrowser
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
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        # Modern dark theme colors (inspired by CUEZ Automator)
        self.bg_dark = "#1e1e1e"
        self.bg_medium = "#2b2b2b"
        self.accent_teal = "#00bcd4"
        self.text_light = "#ffffff"
        self.text_gray = "#b0b0b0"
        self.button_blue = "#3f51b5"
        self.button_green = "#4caf50"
        self.button_red = "#f44336"
        self.button_gray = "#424242"

        self.root.configure(bg=self.bg_dark)

        # Icon for system tray
        self.icon = None
        self.server_thread = None
        self.server_running = False
        self.console_visible = False

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

    def setup_ui(self):
        """Setup the main UI with modern dark theme."""
        # Top section with branding
        top_frame = tk.Frame(self.root, bg=self.bg_dark, height=120)
        top_frame.pack(fill=tk.X, padx=0, pady=0)
        top_frame.pack_propagate(False)

        # Branding text (simple text logo like CUEZ)
        brand_label = tk.Label(
            top_frame,
            text="SINGULAR\nTWEAKS",
            font=("Arial", 20, "bold"),
            bg=self.bg_dark,
            fg=self.text_light,
            justify=tk.LEFT
        )
        brand_label.place(x=30, y=25)

        # Version badge
        version_label = tk.Label(
            top_frame,
            text=f"v{_runtime_version()}",
            font=("Arial", 9),
            bg=self.bg_medium,
            fg=self.text_gray,
            padx=8,
            pady=4
        )
        version_label.place(x=30, y=90)

        # Main content area
        content_frame = tk.Frame(self.root, bg=self.bg_dark)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Port configuration section (softened edges with relief)
        port_frame = tk.Frame(content_frame, bg=self.accent_teal, height=80, relief=tk.FLAT, bd=0)
        port_frame.pack(fill=tk.X, pady=(0, 20))
        port_frame.pack_propagate(False)

        # Port display and change button
        port_container = tk.Frame(port_frame, bg=self.accent_teal)
        port_container.pack(expand=True)

        self.port_label = tk.Label(
            port_container,
            text=str(effective_port()),
            font=("Arial", 24, "bold"),
            bg=self.accent_teal,
            fg=self.text_light
        )
        self.port_label.pack(side=tk.LEFT, padx=20)

        self.port_change_btn = tk.Button(
            port_container,
            text="Change port",
            command=self.change_port,
            bg=self.button_blue,
            fg=self.text_light,
            font=("Arial", 11),
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            bd=0,
            highlightthickness=0
        )
        self.port_change_btn.pack(side=tk.LEFT, padx=10)

        # Status message
        self.status_label = tk.Label(
            content_frame,
            text="Running all interfaces on port " + str(effective_port()),
            font=("Arial", 11),
            bg=self.bg_dark,
            fg=self.text_light
        )
        self.status_label.pack(pady=(0, 5))

        self.url_label = tk.Label(
            content_frame,
            text=f"e.g. http://127.0.0.1:{effective_port()}/",
            font=("Arial", 10),
            bg=self.bg_dark,
            fg=self.text_gray
        )
        self.url_label.pack(pady=(0, 20))

        # Action buttons row
        btn_frame = tk.Frame(content_frame, bg=self.bg_dark)
        btn_frame.pack(pady=20)

        # Open GUI Button
        self.launch_btn = tk.Button(
            btn_frame,
            text="Open GUI",
            command=self.launch_browser,
            bg=self.button_blue,
            fg=self.text_light,
            font=("Arial", 11),
            width=12,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED,
            bd=0,
            highlightthickness=0
        )
        self.launch_btn.grid(row=0, column=0, padx=10)

        # Open Console Button
        self.console_toggle_btn = tk.Button(
            btn_frame,
            text="Open Console",
            command=self.toggle_console,
            bg=self.button_gray,
            fg=self.text_light,
            font=("Arial", 11),
            width=12,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
            highlightthickness=0
        )
        self.console_toggle_btn.grid(row=0, column=1, padx=10)

        # Hide Button
        self.hide_btn = tk.Button(
            btn_frame,
            text="Hide",
            command=self.minimize_to_tray,
            bg=self.button_gray,
            fg=self.text_light,
            font=("Arial", 11),
            width=12,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
            highlightthickness=0
        )
        self.hide_btn.grid(row=0, column=2, padx=10)

        # Quit Button
        self.quit_btn = tk.Button(
            btn_frame,
            text="Quit",
            command=self.on_closing,
            bg=self.button_red,
            fg=self.text_light,
            font=("Arial", 11),
            width=12,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
            highlightthickness=0
        )
        self.quit_btn.grid(row=0, column=3, padx=10)

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

    def toggle_console(self):
        """Toggle console window visibility."""
        if self.console_window is None or not tk.Toplevel.winfo_exists(self.console_window):
            # Create console window
            self.console_window = tk.Toplevel(self.root)
            self.console_window.title("Console Output")
            self.console_window.geometry("800x400")
            self.console_window.configure(bg=self.bg_dark)

            # Console output
            console_text = scrolledtext.ScrolledText(
                self.console_window,
                bg="#1e1e1e",
                fg="#d4d4d4",
                font=("Consolas", 9),
                relief=tk.FLAT
            )
            console_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Redirect stdout to console
            sys.stdout = ConsoleRedirector(console_text)
            sys.stderr = ConsoleRedirector(console_text)

            self.console_toggle_btn.config(text="Close Console")
            self.console_visible = True
        else:
            # Close console window
            self.console_window.destroy()
            self.console_window = None
            self.console_toggle_btn.config(text="Open Console")
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
                format='%(levelname)s: %(message)s',
                force=True
            )

            # Configure uvicorn with custom logging to avoid formatter errors
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=effective_port(),
                log_level="info",
                access_log=False,  # Disable access log to reduce console noise
                log_config=None  # Disable default log config
            )
            server = uvicorn.Server(config)
            server.run()
        except Exception as e:
            print(f"Error starting server: {e}")
            import traceback
            traceback.print_exc()

    def _server_started(self):
        """Update UI after server starts."""
        port = effective_port()
        self.server_running = True
        self.status_label.config(text=f"Running all interfaces on port {port}")
        self.url_label.config(text=f"e.g. http://127.0.0.1:{port}/")
        self.launch_btn.config(state=tk.NORMAL)

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
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        self.buffer.write(message)

    def flush(self):
        pass


def main():
    """Entry point for GUI launcher."""
    app = SingularTweaksGUI()
    app.run()


if __name__ == "__main__":
    main()
