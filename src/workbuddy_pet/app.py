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
from .ui.pet import PetWindow, mascot_icon
from .ui.card import CardWindow
from .ui.animation import AnimationPlayer
from .ui.materials import MaterialPanel
from .ui.chat import ChatPanel
from .materials import MaterialLibrary, MaterialError
from .local_data import LocalDataReader
from .background import Task
from .ui.settings import SettingsDialog
from .ui.tray import PetTray
from .windows import configure_startup, discover_workbuddy, open_workbuddy, open_conversation, validate_workbuddy_path


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
    def __init__(self, app: QApplication, root: Path, demo: bool, workbuddy_home: Path | None = None):
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
        self.workbuddy_home = workbuddy_home or Path.home()/'.workbuddy'
        self.library = MaterialLibrary(self.root/'characters')
        self.data_reader = LocalDataReader(self.workbuddy_home)
        self.stats_job = None
        self.snapshot = None
        self.requested_days = None
        self.next_data = 0
        self.active_pack = None
        try:
            ids = json.loads((root / "acknowledged.json").read_text(encoding="utf-8"))
            self.acknowledged = deque([s for s in ids if isinstance(s, str)][-512:], maxlen=512) if isinstance(ids, list) else deque(maxlen=512)
        except (OSError, ValueError, TypeError):
            self.acknowledged = deque(maxlen=512)
        self.pet = PetWindow(self.settings.size, demo)
        self.bubble = CardWindow(demo)
        self.player = AnimationPlayer(self)
        self.player.changed.connect(self.pet.update)
        self.pet.player = self.player
        self.pet.open_requested.connect(self.open_card)
        self.pet.settings_requested.connect(self.open_settings)
        self.pet.moved.connect(self.position_bubble)
        self.pet.moved.connect(self.schedule_position_save)
        self.bubble.open_requested.connect(self.open_workbuddy)
        self.bubble.settings_requested.connect(self.open_settings)
        self.bubble.acknowledged.connect(self.acknowledge)
        self.bubble.conversation_requested.connect(self.jump_conversation)
        self.bubble.data_requested.connect(self.load_data)
        self.bubble.moved.connect(self.card_moved)
        self.bubble.compact_changed.connect(self.save_compact)
        self.bubble.resized.connect(self.clamp_card)
        self.bubble.chat = ChatPanel(self.root,lambda:self.settings.workbuddy_path,self.workbuddy_home)
        self.bubble.chat.open_requested.connect(self.open_current_conversation)
        self.bubble.add_page(self.bubble.chat,'聊天')
        self.bubble.materials = MaterialPanel(self.library)
        self.bubble.materials.activate_requested.connect(self.activate_character)
        self.bubble.materials.remove_requested.connect(self.remove_character)
        self.bubble.materials.card_only_requested.connect(self.enable_card_only)
        self.bubble.add_page(self.bubble.materials,'素材')
        from .cli import diagnose
        self.dialog = SettingsDialog(self.settings,diagnose(self.root),self.bubble,embedded=True)
        self.dialog.saved.connect(self.apply_settings)
        self.dialog.install_requested.connect(self.install_integration)
        self.dialog.uninstall_requested.connect(self.uninstall_integration)
        self.dialog.reset_requested.connect(self.reset_position)
        self.bubble.add_page(self.dialog,'设置')
        self.bubble.observe_activity()
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.save_position)
        self.tray = PetTray(self, self.toggle_visible, self.open_settings, app.quit)
        self.tray.messageClicked.connect(self.open_workbuddy)
        self.reset_position(self.settings.position)
        self.pet.setVisible(not self.settings.card_only)
        if self.settings.card_only:self.pet.timer.stop()
        self.bubble.show()
        self.bubble.set_compact(self.settings.compact)
        self.restore_character()
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

    def card_moved(self,x,y):
        self.pet.move(x+self.bubble.width()-20,y+15)
        self.schedule_position_save()

    def clamp_card(self):
        x,y=clamp_position((self.bubble.x(),self.bubble.y()),(self.bubble.width(),self.bubble.height()),self.screens())
        if (x,y)!=(self.bubble.x(),self.bubble.y()):self.bubble.move(x,y)

    def save_compact(self,value):
        self.settings=replace(self.settings,compact=value)
        save_settings(self.root,self.settings)

    def open_card(self):
        self.user_visible=True
        self.bubble.show();self.bubble.set_compact(False)
        self.bubble.raise_();self.bubble.activateWindow()

    def enable_card_only(self):
        self.apply_settings(replace(self.settings,card_only=True))

    def restore_character(self):
        self.active_pack=None
        self.player.clear()
        if self.settings.card_only:return
        if self.settings.character!='builtin':
            try:
                self.active_pack=self.library.load(self.settings.character)
                self.player.load(self.active_pack,'idle')
            except MaterialError:
                self.active_pack=None;self.player.clear()
                self.settings=replace(self.settings,character='builtin')
                save_settings(self.root,self.settings)
                self.bubble.materials.status.setText('所选素材不可用，已恢复内置角色。')
        self.player.set_visible(self.pet.isVisible())
        if not self.active_pack and self.pet.isVisible():self.pet.timer.start()

    def activate_character(self,key):
        previous=self.settings
        try:
            if key!='builtin':
                candidate=self.library.load(key)
                self.player.load(candidate,derive_display(self.sessions,time.time()).state)
                self.active_pack=candidate
            else:self.active_pack=None;self.player.clear()
            self.apply_settings(replace(previous,character=key,card_only=False))
            self.bubble.materials.status.setText('所选角色已启用。')
        except MaterialError as error:self.bubble.materials.status.setText(str(error))

    def remove_character(self,key):
        if not key or key=='builtin':return
        if self.bubble.materials.job:return
        try:
            if self.settings.character==key:
                self.player.clear();self.active_pack=None
                self.apply_settings(replace(self.settings,character='builtin',card_only=True))
            self.bubble.materials.player.clear()
            self.library.remove(key)
            self.bubble.materials.reload()
            self.bubble.materials.status.setText('所选素材副本已删除，卡片和源文件保留。')
        except (MaterialError,OSError) as error:self.bubble.materials.status.setText(str(error))

    def load_data(self,days=None):
        self.requested_days=days
        if self.stats_job or self.shutting_down:return
        self.next_data=time.monotonic()+15
        self.stats_job=Task(lambda:self.data_reader.snapshot(days),self)
        def received(snapshot):
            self.snapshot=snapshot
            if snapshot.days==self.requested_days:self.bubble.set_snapshot(snapshot,self.sessions)
        def finished():
            job=self.stats_job;self.stats_job=None
            if job:job.deleteLater()
            if self.snapshot and self.snapshot.days!=self.requested_days and not self.shutting_down:self.load_data(self.requested_days)
        self.stats_job.done.connect(received)
        self.stats_job.failed.connect(lambda _:self.bubble.scope.setText('本地数据暂不可读，稍后重试。'))
        self.stats_job.finished.connect(finished)
        self.stats_job.start()

    def jump_conversation(self,session_id):
        try:
            open_conversation(session_id)
            if self.settings.workbuddy_path:open_workbuddy(Path(self.settings.workbuddy_path))
        except (OSError,ValueError):
            self.dialog.hint.setText('该会话链接无法打开，请在 WorkBuddy 中查找对应任务。')
            self.open_workbuddy()

    def open_current_conversation(self):
        session_id=derive_display(self.sessions,time.time()).session_id
        if session_id:self.jump_conversation(session_id)
        else:self.open_workbuddy()

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
        if self.active_pack and self.pet.isVisible():
            try:self.player.load(self.active_pack,display.state)
            except MaterialError:
                self.player.clear();self.active_pack=None
                self.pet.timer.start()
                self.bubble.materials.status.setText('动画读取失败，已暂时使用内置角色。')
        self.bubble.maybe_collapse(self.settings)
        if time.monotonic()>=self.next_data:self.load_data(self.bubble.range.currentData())
        for reminder in display.reminders:
            if reminder.id not in self.sent:
                self.sent.add(reminder.id)
                if self.settings.notifications and not self.demo:
                    self.tray.remind(reminder.kind)
        try:
            atomic_json(self.root / "runtime.json", {"schema": 1, "version": __version__, "pid": os.getpid(),
                "at": time.time(), "state": display.state, "connection": display.connection,
                "sessions": display.session_count, "unread": len(display.reminders), "demo": self.demo,
                "visible": self.bubble.isVisible(), "card_only":self.settings.card_only,
                "compact":self.bubble.compact,"position": [self.pet.x(), self.pet.y()]})
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
        self.open_card()
        self.bubble.tabs.setCurrentIndex(self.bubble.tabs.count()-1)

    def apply_settings(self, settings):
        try:
            previous=self.settings
            if settings.workbuddy_path:
                validate_workbuddy_path(Path(settings.workbuddy_path))
            if settings.startup != self.settings.startup:
                from .integration import runtime_command
                configure_startup(settings.startup, runtime_command(self.root))
            save_settings(self.root, settings)
            self.settings = settings
            self.pet.set_pet_size(settings.size)
            self.pet.setVisible(self.user_visible and not settings.card_only)
            self.player.set_visible(self.pet.isVisible())
            if settings.card_only:
                self.player.clear();self.active_pack=None;self.pet.timer.stop()
            elif previous.card_only or previous.character!=settings.character:
                self.restore_character()
            self.reset_position(settings.position)
            if self.dialog:
                self.dialog.hint.setText("设置已保存。")
                self.dialog.settings = settings
                self.dialog.card_only.setChecked(settings.card_only)
        except (OSError, ValueError):
            if self.dialog:
                self.dialog.hint.setText("保存失败，请检查程序位置和用户目录是否可写。")

    def install_integration(self):
        from .cli import diagnose
        from .integration import install_integration
        try:
            result = install_integration(self.workbuddy_home, self.root)
            self.dialog.hint.setText("接入已配置。请在 WorkBuddy 新建任务；若一直未连接，请退出并重新打开 WorkBuddy。")
            self.dialog.set_diagnostic(diagnose(self.root))
        except (OSError, ValueError):
            self.dialog.hint.setText("接入失败，原有配置未覆盖。请使用诊断命令检查配置。")

    def uninstall_integration(self):
        from .cli import diagnose
        from .integration import uninstall_integration
        try:
            uninstall_integration(self.workbuddy_home, self.root)
            self.dialog.hint.setText("本桌宠接入已移除，其他插件设置保留。请重新打开 WorkBuddy。")
            self.dialog.set_diagnostic(diagnose(self.root))
        except (OSError, ValueError):
            self.dialog.hint.setText("未找到可安全移除的接入记录，未修改 WorkBuddy 配置。")

    def toggle_visible(self):
        self.user_visible = not self.user_visible
        self.pet.setVisible(self.user_visible and not self.settings.card_only)
        self.bubble.setVisible(self.user_visible)

    def demo_step(self):
        sequence = ("UserPromptSubmit", "PreToolUse", "PermissionRequest", "PostToolUse", "Stop")
        kind = sequence[self.demo_index % len(sequence)]
        self.consume([Event(f"demo-{self.demo_index}", time.time(), "demo-session", kind)])
        self.demo_index += 1

    def capture(self, path: Path):
        from PySide6.QtGui import QColor, QPainter, QPixmap
        image = QPixmap(self.bubble.width()+self.pet.width()+50,max(self.bubble.height()+40,self.pet.height()+40))
        image.fill(QColor("#eef5fa"))
        painter = QPainter(image)
        painter.drawPixmap(15, 20, self.bubble.grab())
        if not self.settings.card_only:painter.drawPixmap(self.bubble.width()+30, 20, self.pet.grab())
        painter.end()
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(path))

    def shutdown(self):
        if self.shutting_down:
            return
        self.shutting_down = True
        self.timer.stop()
        if self.demo and hasattr(self,'demo_timer'):self.demo_timer.stop()
        if self.stats_job:self.stats_job.cancel.set()
        self.bubble.chat.shutdown()
        self.bubble.materials.shutdown()
        self.player.clear()
        if self.worker:
            self.worker.requestInterruption()
            self.worker.wait(3000)
        self.save_position()
        self.tray.hide()
        self.bubble.hide()
        self.pet.hide()


def run_app(root: Path, demo=False, *, quit_requested=False, show_settings=False,
            smoke_seconds=0, capture: Path | None = None, workbuddy_home: Path | None = None, card_only=False,
            capture_page='details') -> int:
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
        socket.write(b"quit" if quit_requested else b"card-only" if card_only else b"settings" if show_settings else b"show")
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
    if card_only:
        save_settings(root,replace(load_settings(root),card_only=True))
    controller = Controller(app, root, demo,workbuddy_home)
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
            elif command == b'card-only':
                controller.enable_card_only();controller.open_card()
            else:
                controller.user_visible = True
                controller.pet.setVisible(not controller.settings.card_only)
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
        def capture_view():
            controller.bubble.set_compact(capture_page=='capsule')
            if capture_page!='capsule':controller.bubble.tabs.setCurrentIndex(('details','data','chat','materials','settings').index(capture_page))
            app.processEvents()
            controller.capture(capture)
        QTimer.singleShot(700,capture_view)
    if smoke_seconds > 0:
        QTimer.singleShot(int(smoke_seconds * 1000), app.quit)
    return app.exec()
