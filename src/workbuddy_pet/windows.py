"""Validated process launch and exact executable-path window matching."""
import os
import subprocess
from pathlib import Path
import re
from urllib.parse import quote
from urllib.parse import urlsplit

WORKBUDDY_WEBSITE = 'https://www.workbuddy.cn/'


def website_url(value: str) -> str:
    if not isinstance(value,str) or len(value)>2048 or any(c.isspace() or ord(c)<32 for c in value):
        raise ValueError('请输入有效的 HTTP(S) 网页地址')
    try:
        parts=urlsplit(value)
        if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password or parts.port==0:
            raise ValueError
    except ValueError:
        raise ValueError('请输入有效的 HTTP(S) 网页地址') from None
    return value


def open_website(value: str):
    value=website_url(value)
    if os.name=='nt':os.startfile(value)


def path_from_registration(raw: str) -> Path | None:
    match=re.match(r'^\s*"([^"]*WorkBuddy\.exe)"',raw,re.I) or re.match(r'^\s*(.*?WorkBuddy\.exe)(?:\s|,|$)',raw,re.I)
    return Path(os.path.expandvars(match[1])) if match else None


def running_workbuddy_paths():
    """Read process executable paths only; never process arguments or credentials."""
    if os.name!='nt':return []
    import ctypes
    from ctypes import wintypes
    class Entry(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),
                  ('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),
                  ('priority',wintypes.LONG),('flags',wintypes.DWORD),('exe',wintypes.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    handle=kernel.CreateToolhelp32Snapshot(2,0);paths=[]
    if handle==ctypes.c_void_p(-1).value:return paths
    try:
        entry=Entry();entry.size=ctypes.sizeof(Entry);more=kernel.Process32FirstW(handle,ctypes.byref(entry))
        while more:
            if entry.exe.lower()=='workbuddy.exe':
                process=kernel.OpenProcess(0x1000,False,entry.pid)
                if process:
                    try:
                        buffer=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(buffer))
                        if kernel.QueryFullProcessImageNameW(process,0,buffer,ctypes.byref(size)):paths.append(Path(buffer.value))
                    finally:kernel.CloseHandle(process)
            more=kernel.Process32NextW(handle,ctypes.byref(entry))
    finally:kernel.CloseHandle(handle)
    return paths


def conversation_url(session_id: str) -> str:
    if not isinstance(session_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_:\-]{0,255}', session_id):
        raise ValueError('会话标识无效')
    return 'workbuddy://chat/' + quote(session_id, safe='')


def open_conversation(session_id: str):
    url = conversation_url(session_id)
    if os.name != 'nt':
        raise OSError('会话跳转需要 Windows 协议处理程序')
    os.startfile(url)


def validate_workbuddy_path(path: Path) -> Path:
    path = Path(path).absolute()
    if path.name.lower() != "workbuddy.exe" or not path.is_file():
        raise ValueError("请选择已安装的 WorkBuddy.exe")
    with path.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise ValueError("所选文件不是 Windows 应用程序")
    return path


def discover_workbuddy() -> Path | None:
    candidates = list(running_workbuddy_paths())
    if os.name == "nt":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
                for key_path in (r'Software\Classes\workbuddy\shell\open\command',
                                 r'Software\Microsoft\Windows\CurrentVersion\App Paths\WorkBuddy.exe'):
                    try:
                        with winreg.OpenKey(hive,key_path,0,winreg.KEY_READ|view) as key:
                            found=path_from_registration(str(winreg.QueryValueEx(key,'')[0]))
                            if found:candidates.append(found)
                    except OSError:pass
                try:
                    with winreg.OpenKey(hive,r'Software\Microsoft\Windows\CurrentVersion\Uninstall',0,winreg.KEY_READ|view) as parent:
                        for index in range(min(winreg.QueryInfoKey(parent)[0],4096)):
                            try:
                                with winreg.OpenKey(parent,winreg.EnumKey(parent,index)) as key:
                                    if 'workbuddy' not in str(winreg.QueryValueEx(key,'DisplayName')[0]).lower():continue
                                    for name in ('DisplayIcon','InstallLocation'):
                                        try:
                                            raw=str(winreg.QueryValueEx(key,name)[0])
                                            candidates.append(path_from_registration(raw) or Path(raw.strip('"'))/'WorkBuddy.exe')
                                        except OSError:pass
                            except OSError:pass
                except OSError:pass
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
