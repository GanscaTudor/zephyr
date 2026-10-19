#!/usr/bin/env python3
"""
Small Tkinter app for checking the AD-SWIOT1L-SL bring-up: a T1L ping
status panel plus the same fan (D1) duty-cycle control as
RPI_T1LPSE/main_app.py's SWIOT1LPanel - reusing Swiot1lFanPanel from
swiot1l_fan_panel.py for the actual libiio/IIOD connect+PWM logic, so both
scripts share one implementation of that sequence.

Usage:
    python swiot1l_app.py [--ip 192.168.97.40]
"""
import argparse
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from swiot1l_fan_panel import Swiot1lFanPanel

PING_INTERVAL_S = 2.0

STATUS_COLORS = {
    "ok": "#1a7f37",
    "warn": "#9a6700",
    "error": "#cf222e",
    "idle": "#6e7781",
}


class PingPanel(ttk.LabelFrame):
    """Background-pings the board's T1L address and shows reachability."""

    def __init__(self, parent, ip):
        super().__init__(parent, text="T1L Link", padding=10)
        self.ip = ip
        self._stop = False

        ttk.Label(self, text=f"Target: {ip}").pack(anchor="w")

        self.status_label = ttk.Label(self, text="checking...",
                                      font=("Segoe UI", 11, "bold"))
        self.status_label.pack(anchor="w", pady=(4, 0))

        self.detail_label = ttk.Label(self, text="")
        self.detail_label.pack(anchor="w")

        ttk.Button(self, text="Ping now", command=self.ping_once).pack(anchor="w", pady=(6, 0))

        threading.Thread(target=self._loop, daemon=True).start()

    def _ping(self):
        try:
            out = subprocess.run(
                (["ping", "-n", "1", "-w", "800", self.ip] if sys.platform == "win32"
                 else ["ping", "-c", "1", "-W", "1", self.ip]),
                capture_output=True, text=True, timeout=2,
            )
            ok = out.returncode == 0 and "ttl=" in out.stdout.lower()
            latency = ""
            if ok:
                for part in out.stdout.replace(",", " ").split():
                    if part.lower().startswith("time"):
                        latency = part
                        break
            return ok, latency
        except Exception:
            return False, ""

    def _loop(self):
        while not self._stop:
            ok, latency = self._ping()
            self.after(0, self._update, ok, latency)
            time.sleep(PING_INTERVAL_S)

    def _update(self, ok, latency):
        if ok:
            self.status_label.config(text="REACHABLE", foreground=STATUS_COLORS["ok"])
            self.detail_label.config(text=latency)
        else:
            self.status_label.config(text="UNREACHABLE", foreground=STATUS_COLORS["error"])
            self.detail_label.config(text="")

    def ping_once(self):
        def worker():
            ok, latency = self._ping()
            self.after(0, self._update, ok, latency)
        threading.Thread(target=worker, daemon=True).start()

    def stop(self):
        self._stop = True


class FanPanel(ttk.LabelFrame):
    """Connect/duty-cycle control for the D1 fan, via Swiot1lFanPanel."""

    def __init__(self, parent, ip):
        super().__init__(parent, text="SWIOT1L Fan (D1 / voltage0)", padding=10)
        self.backend = Swiot1lFanPanel(f"ip:{ip}")
        self.connected = False
        self._running = False
        self._phase = 0

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.status_label = ttk.Label(top, text="Disconnected", foreground=STATUS_COLORS["idle"])
        self.status_label.pack(side="left")
        self.connect_btn = ttk.Button(top, text="Connect", command=self.connect)
        self.connect_btn.pack(side="right")

        dc_row = ttk.Frame(self)
        dc_row.pack(fill="x", pady=(10, 0))
        ttk.Label(dc_row, text="Duty (%)").pack(side="left")
        self.duty_var = tk.StringVar(value="0")
        ttk.Entry(dc_row, textvariable=self.duty_var, width=6).pack(side="left", padx=6)
        ttk.Button(dc_row, text="Set", command=self.set_duty).pack(side="left")
        ttk.Button(dc_row, text="Stop", command=self.stop_duty).pack(side="left", padx=(4, 0))

        self.canvas = tk.Canvas(self, width=56, height=56, highlightthickness=0)
        self.canvas.pack(pady=10)
        self._dot = self.canvas.create_oval(8, 8, 48, 48, fill=STATUS_COLORS["idle"], width=0)

        self.log_box = tk.Text(self, height=7, width=46, state="disabled", wrap="word")
        self.log_box.pack(fill="both", expand=True)

        self._tick()

    def log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def connect(self):
        self.status_label.config(text="Connecting...", foreground=STATUS_COLORS["warn"])
        self.connect_btn.config(state="disabled")

        def worker():
            try:
                self.backend.connect()
                self.after(0, self._on_connected)
            except Exception as e:
                self.after(0, self._on_connect_error, f"{type(e).__name__}: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _on_connected(self):
        self.connected = True
        self.status_label.config(text="Connected", foreground=STATUS_COLORS["ok"])
        self.connect_btn.config(state="normal", text="Reconnect")
        self.log("Connected - ready for PWM")

    def _on_connect_error(self, err):
        self.status_label.config(text="Error", foreground=STATUS_COLORS["error"])
        self.connect_btn.config(state="normal")
        self.log(f"Connection failed: {err}")

    def set_duty(self):
        if not self.connected:
            self.log("Not connected")
            return
        try:
            duty = float(self.duty_var.get())
        except ValueError:
            self.log("Invalid duty cycle")
            return
        duty = max(0.0, min(100.0, duty))
        self.backend.set_duty(duty)
        self._running = duty > 0
        self.log(f"Duty cycle set to {duty:.0f}%")

    def stop_duty(self):
        if self.connected:
            self.backend.stop()
        self._running = False
        self.duty_var.set("0")
        self.log("PWM stopped")

    def _tick(self):
        # Purely cosmetic: pulses while PWM is running, grey when stopped.
        # Not a tachometer reading - same caveat main_app.py's FanIndicator
        # has, there's no real feedback from the fan.
        if self._running:
            self._phase = (self._phase + 1) % 2
            color = "#1a7f37" if self._phase == 0 else "#2da44e"
        else:
            color = STATUS_COLORS["idle"]
        self.canvas.itemconfig(self._dot, fill=color)
        self.after(200, self._tick)

    def cleanup(self):
        if self.connected:
            self.backend.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", default="192.168.97.40", help="AD-SWIOT1L-SL IP address")
    args = parser.parse_args()

    root = tk.Tk()
    root.title("AD-SWIOT1L-SL check")
    root.geometry("380x560")

    ping_panel = PingPanel(root, args.ip)
    ping_panel.pack(fill="x", padx=10, pady=10)

    fan_panel = FanPanel(root, args.ip)
    fan_panel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def on_close():
        ping_panel.stop()
        fan_panel.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
