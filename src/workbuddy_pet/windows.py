"""Validated process launch and exact executable-path window matching."""
import os
import subprocess
from pathlib import Path


def validate_workbuddy_path(path: Path) -> Path:
    path = Path(path).absolute()
    if path.name.lower() != "workbuddy.exe" or not path.is_file():
        raise ValueError("请选择已安装的 WorkBuddy.exe")
    with path.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise ValueError("所选文件不是 Windows 应用程序")
    return path


def discover_workbuddy() -> Path | None:
    candidates = []
    if os.name == "nt":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for key_path in (r"Software\Microsoft\Windows\CurrentVersion\Uninstall\WorkBuddy",
                             r"Software\Microsoft\Windows\CurrentVersion\App Paths\WorkBuddy.exe"):
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        for name in ("InstallLocation", "DisplayIcon", ""):
                            try:
                                raw = str(winreg.QueryValueEx(key, name)[0]).strip('"').split(",")[0]
                                p = Path(raw)
                                candidates.append(p if p.suffix.lower() == ".exe" else p / "WorkBuddy.exe")
                            except OSError:
                                pass
                except OSError:
                    pass
        for env in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            if os.environ.get(env):
                for suffix in ("WorkBuddy/WorkBuddy.exe", "Programs/WorkBuddy/WorkBuddy.exe"):
                    candidates.append(Path(os.environ[env]) / suffix)
    for path in candidates:
        try:
            return validate_workbuddy_path(path)
        except (ValueError, OSError):
            pass
    return None


def open_workbuddy(path: Path) -> bool:
    path = validate_workbuddy_path(path)
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user.SetForegroundWindow.argtypes = [wintypes.HWND]
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def visit(hwnd, _):
        if not user.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel.OpenProcess(0x1000, False, pid.value)
        if handle:
            try:
                buffer = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(buffer))
                if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                    if os.path.normcase(buffer.value) == os.path.normcase(str(path)):
                        found.append(hwnd)
            finally:
                kernel.CloseHandle(handle)
        return True

    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.EnumWindows(visit, 0)
    if found:
        user.ShowWindow(found[0], 9)
        return bool(user.SetForegroundWindow(found[0]))
    subprocess.Popen([str(path)], cwd=str(path.parent), close_fds=True)
    return True


def configure_startup(enabled: bool, command: list[str]) -> None:
    if os.name != "nt":
        return
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            winreg.SetValueEx(key, "WorkBuddyDesktopPet", 0, winreg.REG_SZ, subprocess.list2cmdline(command))
        else:
            try:
                winreg.DeleteValue(key, "WorkBuddyDesktopPet")
            except FileNotFoundError:
                pass
