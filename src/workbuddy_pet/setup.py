"""Installer bridge: explicit first-install consent, preserving existing preferences."""
import hashlib
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

from .integration import install_integration, uninstall_integration, runtime_command
from .settings import load_settings, save_settings
from .storage import plain, atomic_json
from .windows import discover_workbuddy, configure_startup, validate_workbuddy_path


def stop_running(root):
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtNetwork import QLocalSocket
    app = QCoreApplication.instance() or QCoreApplication([])
    name = 'workbuddy-desktop-pet-'+hashlib.sha256(str(plain(root)).lower().encode()).hexdigest()[:24]
    deadline = time.monotonic()+15
    while time.monotonic() < deadline:
        socket = QLocalSocket()
        socket.connectToServer(name)
        if not socket.waitForConnected(200):
            return
        socket.write(b'quit'); socket.flush(); socket.waitForBytesWritten(300)
        socket.disconnectFromServer(); app.processEvents(); time.sleep(.1)
    raise ValueError('桌宠仍在退出，请稍后重试安装')


def apply_setup(root, home, *, connect=False, balance=False, checkin=False, startup=False, workbuddy_exe=None):
    root, home = plain(root), plain(home)
    existed = (root/'settings.json').exists()
    settings = load_settings(root)
    root.mkdir(parents=True, exist_ok=True)
    receipt = root/'integration-receipt.json'
    command = runtime_command(root)
    if existed:
        # Rebind only a previously authorized integration; never re-enable a removed one.
        if receipt.exists():
            saved = json.loads(receipt.read_text(encoding='utf-8'))
            install_integration(Path(saved['home']), root)
        if settings.startup:configure_startup(True, command)
        state = 'preserved'
    else:
        path = validate_workbuddy_path(workbuddy_exe) if workbuddy_exe else discover_workbuddy()
        settings = replace(settings, workbuddy_path=str(path) if path else '')
        if connect and path:
            install_integration(home, root)
            settings = replace(settings, balance_enabled=balance, checkin_enabled=checkin, onboarding_done=True)
            state = 'configured'
        else:
            settings = replace(settings, onboarding_done=not connect)
            state = 'needs_workbuddy' if connect else 'installed'
        if startup:configure_startup(True, command)
        settings = replace(settings, startup=startup)
        save_settings(root, settings)
    atomic_json(root/'installation.json', {'exe':str(Path(sys.executable).resolve())})
    return {'state':state, 'existing_preferences_preserved':existed}


def remove_setup(root):
    root = plain(root)
    marker = root/'installation.json'
    if not marker.exists():
        return {'state':'not_owned'}
    owner = json.loads(marker.read_text(encoding='utf-8'))
    if Path(owner.get('exe','')).resolve() != Path(sys.executable).resolve():
        return {'state':'not_owned'}
    stop_running(root)
    receipt = root/'integration-receipt.json'
    if receipt.exists():
        saved = json.loads(receipt.read_text(encoding='utf-8'))
        uninstall_integration(Path(saved['home']), root)
    if sys.platform=='win32':
        import winreg,subprocess
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                value=winreg.QueryValueEx(key,'WorkBuddyDesktopPet')[0]
            if value==subprocess.list2cmdline(runtime_command(root)):configure_startup(False,runtime_command(root))
        except FileNotFoundError:pass
    settings = load_settings(root)
    save_settings(root, replace(settings, startup=False, onboarding_done=False))
    marker.unlink()
    return {'state':'removed', 'user_data_preserved':True}
