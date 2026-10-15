"""Interactive Windows desktop backend. Must run in the logged-in session."""

import os
import subprocess
import time
from pathlib import Path

import psutil
import win32api
import win32con
import win32gui
import win32process

from .bindings import bindings_match, install_bindings
from .control import ControlError


class WindowsBackend:
    def __init__(self, executable):
        self.executable = Path(executable).resolve(strict=True)
        if self.executable.name.lower() != "plex htpc.exe":
            raise ValueError("Select Plex HTPC.exe, not Plex Media Server or another app")

        self.binding_path = Path(os.environ["LOCALAPPDATA"]) / "Plex HTPC" / "inputmaps" / "keyboard.json"
        install_bindings(self.binding_path)

    def input_ready(self):
        if not bindings_match(self.binding_path):
            return False
        # File mtime survives server restarts and setup.py updates. Plex caches its
        # map at launch; a process older than the installed profile must restart.
        installed_at = self.binding_path.stat().st_mtime
        return all(p.create_time() >= installed_at for p in self.processes())

    def processes(self):
        expected = os.path.normcase(str(self.executable))
        found = []
        for process in psutil.process_iter(["exe"]):
            try:
                if process.info["exe"] and os.path.normcase(process.info["exe"]) == expected:
                    found.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return found

    def running(self):
        return bool(self.processes())

    def windows(self):
        pids = {p.pid for p in self.processes()}
        windows = []

        def collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] in pids:
                windows.append(hwnd)

        win32gui.EnumWindows(collect, None)
        return windows

    def start(self):
        if not self.running():
            subprocess.Popen([str(self.executable)], cwd=str(self.executable.parent))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.windows():
                self.focus()
                return
            time.sleep(0.2)
        raise ControlError("Plex did not open a window within 15 seconds")

    def close(self):
        processes = self.processes()
        if not processes:
            return
        # WM_CLOSE only targets visible windows owned by the configured executable.
        for hwnd in self.windows():
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        _, alive = psutil.wait_procs(processes, timeout=5)
        # Windows terminate applies only to the previously identified Plex processes.
        for process in alive:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(alive, timeout=3)
        if alive or self.running():
            raise ControlError("Plex could not be closed")

    def focus(self):
        windows = self.windows()
        if not windows:
            raise ControlError("No Plex window; unlock the interactive Windows session")
        hwnd = max(windows, key=lambda w: self._area(w))
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        current_thread = win32api.GetCurrentThreadId()
        foreground_thread = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[0]
        attached = False
        try:
            if foreground_thread and foreground_thread != current_thread:
                win32process.AttachThreadInput(current_thread, foreground_thread, True)
                attached = True
            win32gui.SetForegroundWindow(hwnd)
        except Exception as exc:
            raise ControlError("Windows denied focus; activate Plex locally and retry") from exc
        finally:
            if attached:
                win32process.AttachThreadInput(current_thread, foreground_thread, False)
        time.sleep(0.05)
        self._check_focus()

    @staticmethod
    def _area(hwnd):
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return (right - left) * (bottom - top)

    def _check_focus(self):
        pid = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1]
        if pid not in {p.pid for p in self.processes()}:
            raise ControlError("Plex is not foreground; refusing to send keys")

    def press(self, keys):
        self._check_focus()
        # Do not combine injected keys with physically held modifiers.
        if any(win32api.GetAsyncKeyState(k) & 0x8000 for k in (0x10, 0x11, 0x12, 0x5B, 0x5C)):
            raise ControlError("Release keyboard modifiers before using the remote")
        pressed = []
        try:
            for key in keys:
                flags = win32con.KEYEVENTF_EXTENDEDKEY if key in (0x25, 0x26, 0x27, 0x28) else 0
                win32api.keybd_event(key, 0, flags, 0)
                pressed.append((key, flags))
            time.sleep(0.025)
        finally:
            for key, flags in reversed(pressed):
                win32api.keybd_event(key, 0, flags | win32con.KEYEVENTF_KEYUP, 0)
