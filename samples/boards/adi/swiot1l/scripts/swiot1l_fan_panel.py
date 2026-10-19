#!/usr/bin/env python3
"""
Standalone re-implementation of the SWIOT1LPanel from RPI_T1LPSE/main_app.py
(adi-innersource/datax-industrial-demo), to drive the AD-SWIOT1L-SL fan over
the network (libiio/IIOD) exactly the same way that app does - without the
rest of the Tk UI.

Connect sequence (identical to main_app.py's SWIOT1LPanel._connect):
    swiot.mode = "config"
    swiot.ch0_device = "max14906"
    swiot.ch0_function = "output"
    swiot.ch0_enable = 1
    swiot.mode = "runtime"
    max14906 = adi.max14906(uri)        # here: ctx.find_device("max14906")

PWM (identical to main_app.py's SWIOT1LPanel._pwm_loop): no real PWM
peripheral is involved - this script just bit-bangs the "raw" attribute of
max14906 channel "voltage0" (D1, the fan) on/off over the network, with the
same PWM_PERIOD = 0.01s (10 ms) and on/off timing split by duty cycle.

Needs the libiio C library and its Python bindings (pip install pylibiio).
The swiot/max14906 device, channel and attribute names are plain IIO
objects, so pyadi-iio is not needed.

Usage:
    python swiot1l_fan_panel.py [--ip 192.168.97.40]
    Then at the "duty% > " prompt: enter 0-100, or "stop", or "quit".
"""
import argparse
import sys
import threading
import time

# On Windows, pylibiio 1.0.0 calls ctypes.util.find_library("c"), which
# returns None there (there is no POSIX libc to find by that name). Point it
# at msvcrt.dll before importing iio. Not needed on Linux.
if sys.platform == "win32":
    import ctypes.util

    _orig_find_library = ctypes.util.find_library

    def _patched_find_library(name):
        if name == "c":
            return "msvcrt.dll"
        return _orig_find_library(name)

    ctypes.util.find_library = _patched_find_library

import iio  # noqa: E402  (import must follow the patch above)

PWM_PERIOD = 0.01  # seconds - same constant as RPI_T1LPSE/main_app.py
FAN_CHANNEL = "voltage0"  # D1, same as main_app.py's channel["voltage0"]


class Swiot1lFanPanel:
    """Mirrors SWIOT1LPanel's connect()/_set_pwm()/_stop_pwm()/cleanup()."""

    def __init__(self, uri):
        self.uri = uri
        self.ctx = None
        self.max14906 = None
        self.fan_chn = None
        self.duty_cycle = 0.0
        self.pwm_running = False
        self._pwm_thread = None

    def connect(self):
        print(f"Connecting to {self.uri} ...")
        self.ctx = iio.Context(self.uri)
        print(f"  context: {self.ctx.description}")

        swiot = self.ctx.find_device("swiot")
        if swiot is None:
            raise RuntimeError("No swiot device found")

        swiot.attrs["mode"].value = "config"
        swiot.attrs["ch0_device"].value = "max14906"
        swiot.attrs["ch0_function"].value = "output"
        swiot.attrs["ch0_enable"].value = "1"
        swiot.attrs["mode"].value = "runtime"

        # Same shape as main_app.py's third adi.swiot(uri) re-open after
        # mode = "runtime": it also opens ad74413r internally. We don't
        # need its channels for the fan, but open it too so a stub-missing
        # device would be caught here, same as in the real app.
        ad74413r = self.ctx.find_device("ad74413r")
        if ad74413r is None:
            raise RuntimeError("No ad74413r device found")

        self.max14906 = self.ctx.find_device("max14906")
        if self.max14906 is None:
            raise RuntimeError("No max14906 device found")

        self.fan_chn = self.max14906.find_channel(FAN_CHANNEL, is_output=True)
        if self.fan_chn is None:
            raise RuntimeError(f"No {FAN_CHANNEL} channel found on max14906")

        print("Connected - ready for PWM")

    def _set_raw(self, val):
        self.fan_chn.attrs["raw"].value = str(val)

    def _pwm_loop(self):
        while self.pwm_running:
            duty = self.duty_cycle
            try:
                if duty <= 0:
                    self._set_raw(0)
                    time.sleep(PWM_PERIOD)
                elif duty >= 100:
                    self._set_raw(1)
                    time.sleep(PWM_PERIOD)
                else:
                    on_time = PWM_PERIOD * duty / 100.0
                    off_time = PWM_PERIOD - on_time
                    self._set_raw(1)
                    time.sleep(on_time)
                    self._set_raw(0)
                    time.sleep(off_time)
            except Exception as e:
                print(f"PWM loop error: {e}")
                break

    def set_duty(self, duty):
        duty = max(0.0, min(100.0, duty))
        self.duty_cycle = duty
        print(f"Duty cycle set to {duty:.0f}%")
        if not self.pwm_running:
            self.pwm_running = True
            self._pwm_thread = threading.Thread(target=self._pwm_loop, daemon=True)
            self._pwm_thread.start()

    def stop(self):
        self.pwm_running = False
        self.duty_cycle = 0.0
        if self._pwm_thread:
            self._pwm_thread.join(timeout=1)
        try:
            self._set_raw(0)
        except Exception:
            pass
        print("PWM stopped")

    def cleanup(self):
        self.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", default="192.168.97.40", help="AD-SWIOT1L-SL IP address")
    args = parser.parse_args()

    panel = Swiot1lFanPanel(f"ip:{args.ip}")
    try:
        panel.connect()
    except Exception as e:
        print(f"Connection failed: {type(e).__name__}: {e}")
        sys.exit(1)

    print()
    print("Enter a duty cycle 0-100, 'stop', or 'quit'/Ctrl-C to exit.")
    try:
        while True:
            raw = input("duty% > ").strip().lower()
            if raw in ("quit", "exit", "q"):
                break
            if raw == "stop":
                panel.stop()
                continue
            try:
                duty = float(raw)
            except ValueError:
                print("Not a number (or 'stop'/'quit')")
                continue
            panel.set_duty(duty)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        panel.cleanup()


if __name__ == "__main__":
    main()
