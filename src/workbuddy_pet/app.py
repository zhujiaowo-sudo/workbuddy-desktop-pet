import hashlib
import json
import os
import sys
import time
from collections import deque
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .events import Event
from .settings import Rect, clamp_position, load_settings, save_settings
from .spool import SpoolReader
from .state import acknowledge, derive_display, reduce_event
from .storage import atomic_json, plain
from .ui.pet import PetWindow, StatusBubble, mascot_icon
from .ui.settings import SettingsDialog
from .ui.tray import PetTray
from .windows import configure_startup, discover_workbuddy, open_workbuddy, validate_workbuddy_path


class EventWorker(QThread):
    batch = Signal(object)
    status = Signal(str)

    def __init__(self, root: Path, parent=None):
        super().__init__(parent)
        self.root = root

    def run(self):
        reader = SpoolReader(self.root / "events")
        while not self.isInterruptionRequested():
            try:
                batch = reader.poll()
                if batch:
                    self.batch.emit(batch)
            except (OSError, ValueError):
                self.status.emit("event_queue_unavailable")
            for _ in range(5):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)


class Controller(QObject):
    def __init__(self, app: QApplication, root: Path, demo: bool):
        super().__init__(app)
        self.app, self.root, self.demo = app, plain(root), demo
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings = load_settings(root)
        if not self.settings.workbuddy_path:
            path = discover_workbuddy()
            if path:
                self.settings = replace(self.settings, workbuddy_path=str(path))
                save_settings(root, self.settings)
        self.sessions = {}
        self.sent = set()
        self.started = time.time()
        self.dialog = None
        self.user_visible = True
        self.shutting_down = False
        try:
            ids = json.loads((root / "acknowledged.json").read_text(encoding="utf-8"))
            self.acknowledged = deque([s for s in ids if isinstance(s, str)][-512:], maxlen=512) if isinstance(ids, list) else deque(maxlen=512)
        except (OSError, ValueError, TypeError):
            self.acknowledged = deque(maxlen=512)
        self.pet = PetWindow(self.settings.size, demo)
        self.bubble = StatusBubble(demo)
        self.pet.open_requested.connect(self.open_workbuddy)
        self.pet.settings_requested.connect(self.open_settings)
        self.pet.moved.connect(self.position_bubble)
        self.pet.moved.connect(self.schedule_position_save)
        self.bubble.open_requested.connect(self.open_workbuddy)
        self.bubble.settings_requested.connect(self.open_settings)
        self.bubble.acknowledged.connect(self.acknowledge)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.save_position)
        self.tray = PetTray(self, self.toggle_visible, self.open_settings, app.quit)
        self.tray.messageClicked.connect(self.open_workbuddy)
        self.reset_position(self.settings.position)
        self.pet.show()
        self.bubble.show()
        self.position_bubble()
        self.worker = None
        if not demo:
            self.worker = EventWorker(root, self)
            self.worker.batch.connect(self.consume)
            self.worker.start()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        if demo:
            self.demo_index = 0
            self.demo_timer = QTimer(self)
            self.demo_timer.setInterval(3500)
            self.demo_timer.timeout.connect(self.demo_step)
            self.demo_timer.start()
            self.demo_step()
        app.aboutToQuit.connect(self.shutdown)
        self.refresh()

    def screens(self):
        return [Rect(s.availableGeometry().x(), s.availableGeometry().y(), s.availableGeometry().width(),
                     s.availableGeometry().height()) for s in QGuiApplication.screens()]

    def reset_position(self, position=None):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        position = position or (screen.right() - self.pet.width() - 35, screen.bottom() - self.pet.height() - 30)
        x, y = clamp_position(position, (self.pet.width(), self.pet.height()), self.screens())
        self.pet.move(x, y)
        self.position_bubble()

    def position_bubble(self, *_):
        desired = (self.pet.x() - self.bubble.width() + 20, self.pet.y() - 15)
        x, y = clamp_position(desired, (self.bubble.width(), self.bubble.height()), self.screens())
        self.bubble.move(x, y)

    def schedule_position_save(self, *_):
        self.save_timer.start()

    def save_position(self):
        x, y = clamp_position((self.pet.x(), self.pet.y()), (self.pet.width(), self.pet.height()), self.screens())
        self.pet.move(x, y)
        self.settings = replace(self.settings, position=(x, y))
        save_settings(self.root, self.settings)
        self.position_bubble()

    def consume(self, events):
        for event in events:
            self.sessions = reduce_event(self.sessions, event)
            display = derive_display(self.sessions, time.time())
            for reminder in display.reminders:
                if reminder.id in self.acknowledged:
                    self.sessions = acknowledge(self.sessions, reminder.id)
                elif event.at < self.started:
                    self.sent.add(reminder.id)  # Retain unread card without replaying old toast notifications.
        self.refresh()

    def refresh(self):
        display = derive_display(self.sessions, time.time())
        self.pet.set_display(display)
        self.bubble.set_display(display)
        self.position_bubble()
        for reminder in display.reminders:
            if reminder.id not in self.sent:
                self.sent.add(reminder.id)
                if self.settings.notifications and not self.demo:
                    self.tray.remind(reminder.kind)
        try:
            atomic_json(self.root / "runtime.json", {"schema": 1, "version": __version__, "pid": os.getpid(),
                "at": time.time(), "state": display.state, "connection": display.connection,
                "sessions": display.session_count, "unread": len(display.reminders), "demo": self.demo,
                "visible": self.pet.isVisible(), "position": [self.pet.x(), self.pet.y()]})
        except (OSError, ValueError):
            pass

    def acknowledge(self):
        for reminder in derive_display(self.sessions, time.time()).reminders:
            self.sessions = acknowledge(self.sessions, reminder.id)
            if reminder.id not in self.acknowledged:
                self.acknowledged.append(reminder.id)
        atomic_json(self.root / "acknowledged.json", list(self.acknowledged))
        self.refresh()

    def open_workbuddy(self):
        try:
            if not self.settings.workbuddy_path:
                self.open_settings()
                return
            opened = open_workbuddy(Path(self.settings.workbuddy_path))
            if not opened:
                self.tray.showMessage("WorkBuddy 小搭子", "Windows 暂未允许切换前台，请点击任务栏中的 WorkBuddy。")
        except (OSError, ValueError):
            self.open_settings()
            if self.dialog:
                self.dialog.hint.setText("没有找到有效的 WorkBuddy.exe，请重新选择程序位置。")

    def open_settings(self):
        if self.dialog and self.dialog.isVisible():
            self.dialog.raise_()
            self.dialog.activateWindow()
            return
        from .cli import diagnose
        self.dialog = SettingsDialog(self.settings, diagnose(self.root))
        self.dialog.saved.connect(self.apply_settings)
        self.dialog.install_requested.connect(self.install_integration)
        self.dialog.uninstall_requested.connect(self.uninstall_integration)
        self.dialog.reset_requested.connect(self.reset_position)
        self.dialog.show()
        self.dialog.raise_()

    def apply_settings(self, settings):
        try:
            if settings.workbuddy_path:
                validate_workbuddy_path(Path(settings.workbuddy_path))
            if settings.startup != self.settings.startup:
                from .integration import runtime_command
                configure_startup(settings.startup, runtime_command(self.root))
            save_settings(self.root, settings)
            self.settings = settings
            self.pet.set_pet_size(settings.size)
            self.reset_position(settings.position)
            if self.dialog:
                self.dialog.hint.setText("设置已保存。")
                self.dialog.settings = settings
        except (OSError, ValueError):
            if self.dialog:
                self.dialog.hint.setText("保存失败，请检查程序位置和用户目录是否可写。")

    def install_integration(self):
        from .cli import diagnose
        from .integration import install_integration
        try:
            result = install_integration(Path.home() / ".workbuddy", self.root)
            self.dialog.hint.setText("接入已配置。请在 WorkBuddy 新建任务；若一直未连接，请退出并重新打开 WorkBuddy。")
            self.dialog.set_diagnostic(diagnose(self.root))
        except (OSError, ValueError):
            self.dialog.hint.setText("接入失败，原有配置未覆盖。请使用诊断命令检查配置。")

    def uninstall_integration(self):
        from .cli import diagnose
        from .integration import uninstall_integration
        try:
            uninstall_integration(Path.home() / ".workbuddy", self.root)
            self.dialog.hint.setText("本桌宠接入已移除，其他插件设置保留。请重新打开 WorkBuddy。")
            self.dialog.set_diagnostic(diagnose(self.root))
        except (OSError, ValueError):
            self.dialog.hint.setText("未找到可安全移除的接入记录，未修改 WorkBuddy 配置。")

    def toggle_visible(self):
        self.user_visible = not self.user_visible
        self.pet.setVisible(self.user_visible)
        self.bubble.setVisible(self.user_visible)

    def demo_step(self):
        sequence = ("UserPromptSubmit", "PreToolUse", "PermissionRequest", "PostToolUse", "Stop")
        kind = sequence[self.demo_index % len(sequence)]
        self.consume([Event(f"demo-{self.demo_index}", time.time(), "demo-session", kind)])
        self.demo_index += 1

    def capture(self, path: Path):
        from PySide6.QtGui import QColor, QPainter, QPixmap
        image = QPixmap(530, 280)
        image.fill(QColor("#eef5fa"))
        painter = QPainter(image)
        painter.drawPixmap(22, 45, self.bubble.grab())
        painter.drawPixmap(325, 20, self.pet.grab())
        painter.end()
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(path))

    def shutdown(self):
        if self.shutting_down:
            return
        self.shutting_down = True
        self.timer.stop()
        if self.worker:
            self.worker.requestInterruption()
            self.worker.wait(3000)
        self.save_position()
        self.tray.hide()
        self.bubble.hide()
        self.pet.hide()


def run_app(root: Path, demo=False, *, quit_requested=False, show_settings=False,
            smoke_seconds=0, capture: Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("WorkBuddyDesktopPet")
    app.setOrganizationName("WorkBuddyDesktopPet")
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setWindowIcon(mascot_icon())
    root = plain(root)
    server_name = "workbuddy-desktop-pet-" + hashlib.sha256(str(root).lower().encode()).hexdigest()[:24]
    if demo:
        server_name += "-demo"
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if socket.waitForConnected(250):
        socket.write(b"quit" if quit_requested else b"settings" if show_settings else b"show")
        socket.flush()
        socket.waitForBytesWritten(250)
        return 0
    if quit_requested:
        return 0
    QLocalServer.removeServer(server_name)
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not server.listen(server_name):
        return 1
    controller = Controller(app, root, demo)
    peers = []

    def incoming():
        peer = server.nextPendingConnection()
        peers.append(peer)

        def receive():
            command = bytes(peer.readAll())
            if command == b"quit":
                app.quit()
            elif command == b"settings":
                controller.open_settings()
            else:
                controller.user_visible = True
                controller.pet.show()
                controller.bubble.show()
            peer.disconnectFromServer()
            if peer in peers:
                peers.remove(peer)
        peer.readyRead.connect(receive)
        peer.disconnected.connect(peer.deleteLater)
        if peer.bytesAvailable():
            receive()
    server.newConnection.connect(incoming)
    if show_settings:
        controller.open_settings()
    if capture:
        QTimer.singleShot(500, lambda: controller.capture(capture))
    if smoke_seconds > 0:
        QTimer.singleShot(int(smoke_seconds * 1000), app.quit)
    return app.exec()
