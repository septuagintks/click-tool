import ctypes
from ctypes import wintypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import pydirectinput

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_QUIT = 0x0012
HC_ACTION = 0
VK_ESCAPE = 0x1B


PROCESS_PER_MONITOR_DPI_AWARE = 2
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)


def enable_dpi_awareness() -> None:
    try:
        user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
    except (AttributeError, OSError):
        pass


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


LowLevelMouseProc = ctypes.WINFUNCTYPE(
    wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    LowLevelMouseProc,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.CallNextHookEx.restype = wintypes.LPARAM
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


class PositionCapture:
    """Installs WH_MOUSE_LL on a dedicated thread until a left-click or right-click."""

    def __init__(self, on_captured, on_canceled) -> None:
        self._on_captured = on_captured
        self._on_canceled = on_canceled
        self._thread_id = 0
        self._thread: threading.Thread | None = None
        self._callback_ref = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

    def _run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        state = {"done": False, "canceled": False, "x": 0, "y": 0}

        def proc(n_code, w_param, l_param):
            if n_code == HC_ACTION and not state["done"]:
                if w_param == WM_LBUTTONDOWN:
                    info = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT))[0]
                    state["done"] = True
                    state["x"] = info.pt.x
                    state["y"] = info.pt.y
                    user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
                    return 1
                if w_param == WM_RBUTTONDOWN:
                    state["done"] = True
                    state["canceled"] = True
                    user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
                    return 1
            return user32.CallNextHookEx(None, n_code, w_param, l_param)

        self._callback_ref = LowLevelMouseProc(proc)
        hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._callback_ref, kernel32.GetModuleHandleW(None), 0
        )
        if not hook:
            self._on_canceled()
            return

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnhookWindowsHookEx(hook)

        if state["canceled"] or not state["done"]:
            self._on_canceled()
        else:
            self._on_captured(state["x"], state["y"])


class ClickerApp:
    def __init__(self) -> None:
        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.title("Mouse Click Tool")
        self.root.resizable(False, False)

        self.interval_var = tk.StringVar(value="500")
        self.status_var = tk.StringVar(value="Ready")
        self._positions: list[tuple[int, int]] = []
        self._stop_event = threading.Event()
        self._click_thread: threading.Thread | None = None
        self._escape_thread: threading.Thread | None = None
        self._capture: PositionCapture | None = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="Interval (ms)").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.interval_var, width=12).grid(
            row=0, column=1, padx=(8, 0), sticky="w"
        )

        ttk.Label(frame, text="Positions (clicked in order)").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )

        list_frame = ttk.Frame(frame)
        list_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.position_list = tk.Listbox(
            list_frame, height=8, width=34, activestyle="dotbox"
        )
        self.position_list.grid(row=0, column=0)
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.position_list.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.position_list.config(yscrollcommand=scrollbar.set)

        edit_row = ttk.Frame(frame)
        edit_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.capture_button = ttk.Button(
            edit_row, text="Add by click", command=self.begin_capture
        )
        self.capture_button.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(edit_row, text="Remove", command=self.remove_position).grid(
            row=0, column=1, padx=6
        )
        ttk.Button(
            edit_row, text="Up", width=4, command=lambda: self.move_position(-1)
        ).grid(row=0, column=2, padx=(6, 0))
        ttk.Button(
            edit_row, text="Down", width=5, command=lambda: self.move_position(1)
        ).grid(row=0, column=3, padx=(4, 0))
        ttk.Button(edit_row, text="Clear", command=self.clear_positions).grid(
            row=0, column=4, padx=(6, 0)
        )

        run_row = ttk.Frame(frame)
        run_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.start_button = ttk.Button(
            run_row, text="Start", command=self.start_clicking
        )
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(
            run_row, text="Stop", command=self.stop_clicking, state="disabled"
        )
        self.stop_button.grid(row=0, column=1)

        ttk.Label(frame, textvariable=self.status_var, foreground="#333333").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )
        ttk.Label(
            frame,
            text="Left-click captures a position. Right-click cancels capture. Esc stops clicking.",
            foreground="#666666",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def begin_capture(self) -> None:
        if self._capture is not None:
            return
        self.capture_button.config(state="disabled")
        self.start_button.config(state="disabled")
        self.status_var.set("Left-click to capture, right-click or Esc to cancel.")
        self.root.bind_all("<Escape>", self._cancel_capture)
        self._capture = PositionCapture(
            on_captured=self._on_position_captured,
            on_canceled=self._on_capture_canceled,
        )
        self._capture.start()

    def _cancel_capture(self, _event=None) -> None:
        if self._capture is not None:
            self._capture.cancel()

    def _on_position_captured(self, x: int, y: int) -> None:
        self.root.after(0, lambda: self._apply_captured(x, y))

    def _on_capture_canceled(self) -> None:
        self.root.after(0, lambda: self._end_capture("Capture canceled"))

    def _apply_captured(self, x: int, y: int) -> None:
        self._positions.append((x, y))
        self._refresh_list()
        self._end_capture(f"Captured ({x}, {y})")

    def _end_capture(self, status: str) -> None:
        self.capture_button.config(state="normal")
        self.start_button.config(state="normal")
        self.status_var.set(status)
        try:
            self.root.unbind_all("<Escape>")
        except tk.TclError:
            pass
        self._capture = None

    def remove_position(self) -> None:
        sel = self.position_list.curselection()
        if not sel:
            return
        del self._positions[sel[0]]
        self._refresh_list()

    def move_position(self, delta: int) -> None:
        sel = self.position_list.curselection()
        if not sel:
            return
        index = sel[0]
        target = index + delta
        if not 0 <= target < len(self._positions):
            return
        self._positions[index], self._positions[target] = (
            self._positions[target],
            self._positions[index],
        )
        self._refresh_list()
        self.position_list.selection_set(target)
        self.position_list.activate(target)

    def clear_positions(self) -> None:
        self._positions.clear()
        self._refresh_list()

    def _refresh_list(self) -> None:
        self.position_list.delete(0, "end")
        for i, (x, y) in enumerate(self._positions, start=1):
            self.position_list.insert("end", f"{i}: ({x}, {y})")

    def start_clicking(self) -> None:
        if self._click_thread and self._click_thread.is_alive():
            return
        if not self._positions:
            messagebox.showerror("No positions", "Add at least one position first.")
            return
        try:
            interval = int(self.interval_var.get())
            if interval < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid interval", "Enter a non-negative whole number of milliseconds."
            )
            return

        self._stop_event.clear()
        positions_snapshot = list(self._positions)
        self._click_thread = threading.Thread(
            target=self._click_loop, args=(interval, positions_snapshot), daemon=True
        )
        self._click_thread.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.capture_button.config(state="disabled")
        self._escape_thread = threading.Thread(target=self._watch_escape, daemon=True)
        self._escape_thread.start()
        self.status_var.set(
            f"Clicking {len(positions_snapshot)} positions every {interval} ms. Press Esc to stop."
        )

    def stop_clicking(self) -> None:
        self._stop_event.set()

    def _watch_escape(self) -> None:
        while not self._stop_event.wait(0.03):
            if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                self._stop_event.set()
                break

    def _click_loop(self, interval_ms: int, positions: list[tuple[int, int]]) -> None:
        interval_s = interval_ms / 1000.0
        while not self._stop_event.is_set():
            for x, y in positions:
                if self._stop_event.is_set():
                    break
                self._click_at(x, y)
                if interval_s and self._stop_event.wait(interval_s):
                    break
        self.root.after(0, self._on_loop_exit)

    def _on_loop_exit(self) -> None:
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.capture_button.config(state="normal")
        self.status_var.set("Stopped")

    def _click_at(self, x: int, y: int) -> None:
        pydirectinput.click(x=int(x), y=int(y))

    def on_close(self) -> None:
        self._stop_event.set()
        if self._capture is not None:
            self._capture.cancel()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ClickerApp().run()
