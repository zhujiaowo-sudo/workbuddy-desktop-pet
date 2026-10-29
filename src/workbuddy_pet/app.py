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
from .runtime import RuntimeWriter
from .ui.pet import PetWindow, mascot_icon
from .ui.card import CardWindow,PAGE_KEYS
from .ui.animation import AnimationPlayer
from .ui.materials import MaterialPanel
from .materials import MaterialLibrary, MaterialError
from .local_data import LocalDataReader
from .placement import card_position,fit_capsule_pet,panel_height_limit,pet_below_capsule
from .background import Task
from .balance import read_balance
from .checkin import CheckinSnapshot,read_checkin,perform_checkin,local_day
from .interaction import Interaction,response_for_click,IdleDirector,AmbientDirector,idle_allowed
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
        self.avatar_collapsed=self.settings.avatar_collapsed
        self._capsule_anchor=None
        self.binding=None;self.discovery_job=None
        self.shutting_down = False
        self.runtime_writer = RuntimeWriter(self.root / 'runtime.json')
        self.workbuddy_home = workbuddy_home or Path.home()/'.workbuddy'
        self.library = MaterialLibrary(self.root/'characters')
        self.data_reader = LocalDataReader(self.workbuddy_home)
        self.stats_job = None
        self.snapshot = None
        self.requested_days = None
        self.next_data = 0
        self.active_pack = None
        self.balance_job=None
        self.next_balance=0
        self.last_balance_query=0
        self.checkin_job=None;self.next_checkin=0;self.checkin_snapshot=CheckinSnapshot();self.checkin_day=local_day()
        self.active_interaction=None;self.interaction_deadline=0;self.interaction_index=0;self.last_pet_click=-1
        self.idle_director=IdleDirector()
        self.ambient_director=AmbientDirector()
        self.visual_action='idle'
        self.interaction_timer=QTimer(self);self.interaction_timer.setSingleShot(True)
        self.interaction_timer.timeout.connect(self.finish_interaction)
        self._positioning=False
        self._card_placed = False
        self._last_card_pos = None
        try:
            ids = json.loads((root / "acknowledged.json").read_text(encoding="utf-8"))
            self.acknowledged = deque([s for s in ids if isinstance(s, str)][-512:], maxlen=512) if isinstance(ids, list) else deque(maxlen=512)
        except (OSError, ValueError, TypeError):
            self.acknowledged = deque(maxlen=512)
        self.pet = PetWindow(self.settings.size, demo)
        self.bubble = CardWindow(demo)
        self.player = AnimationPlayer(self)
        self.player.finished.connect(self.finish_long_interaction)
        self.player.changed.connect(self.pet.update)
        self.player.bounds_changed.connect(self.position_bubble)
        self.pet.player = self.player
        self.pet.open_requested.connect(self.open_card)
        self.pet.interact_requested.connect(self.interact)
        self.pet.manual_activity.connect(self.pet_activity)
        self.pet.settings_requested.connect(self.open_settings)
        self.pet.page_requested.connect(self.open_page)
        self.pet.quit_requested.connect(app.quit)
        self.pet.moved.connect(self.position_bubble)
        self.pet.moved.connect(self.schedule_position_save)
        self.bubble.open_requested.connect(self.open_workbuddy)
        self.bubble.settings_requested.connect(self.open_settings)
        self.bubble.acknowledged.connect(self.acknowledge)
        self.bubble.conversation_requested.connect(self.jump_conversation)
        self.bubble.data_requested.connect(self.load_data)
        self.bubble.balance_requested.connect(self.open_balance)
        self.bubble.refresh_requested.connect(self.refresh_data)
        self.bubble.quick_requested.connect(self.quick_clicked)
        self.bubble.page_requested.connect(self.open_page)
        self.bubble.avatar_requested.connect(self.toggle_avatar)
        self.bubble.quit_requested.connect(app.quit)
        self.bubble.set_avatar_hidden(self.avatar_collapsed or self.settings.card_only,self.settings.card_only)
        self.bubble.set_quick_action(self.settings.quick_action,self.settings.quick_url)
        self.bubble.moved.connect(self.card_moved)
        self.bubble.compact_changed.connect(self.save_compact)
        self.bubble.resized.connect(self.position_bubble)
        self.bubble.chat_requested.connect(self.open_current_conversation)
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
        self.dialog.reset_requested.connect(self.reset_to_corner)
        self.dialog.detect_requested.connect(self.detect_workbuddy)
        self.bubble.add_page(self.dialog,'设置')
        for menu in (self.pet.context_menu,self.bubble.context_menu):
            menu.aboutToShow.connect(lambda m=menu:self.populate_menu(m))
        self.bubble.minimal=self.settings.minimal
        self.bubble.observe_activity()
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.save_position)
        self.tray = PetTray(self, self.toggle_visible, self.open_settings, app.quit)
        self.tray.messageClicked.connect(self.open_workbuddy)
        self.bubble.minimal=self.settings.minimal and not (self.avatar_collapsed or self.settings.card_only)
        self.bubble.set_compact(self.settings.compact)
        self._card_placed=False  # First placement uses saved pet/card coordinates, not the hidden widget's origin.
        self.reset_position(self.settings.position)
        self.pet.setVisible(not self.settings.card_only and not self.avatar_collapsed)
        if self.settings.card_only:self.pet.timer.stop()
        self.bubble.show()
        self.restore_character()
        if self.avatar_collapsed and not self.settings.card_position:
            self._card_placed=False
            self.reset_position(self.settings.position)
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
        from .ui.updates import UpdateManager
        self.updates=UpdateManager(self)
        self.dialog.update_requested.connect(lambda:self.updates.check(manual=True))
        if not demo:QTimer.singleShot(1000,self.first_binding)
        self.refresh()

    def screens(self):
        return [Rect(s.availableGeometry().x(), s.availableGeometry().y(), s.availableGeometry().width(),
                     s.availableGeometry().height()) for s in QGuiApplication.screens()]

    def reset_position(self, position=None):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        position = position or (screen.right() - self.pet.width() - 35, screen.bottom() - self.pet.height() - 30)
        x, y = clamp_position(position, (self.pet.width(), self.pet.height()), self.screens())
        self.pet.move(x, y)
        if (self.settings.card_only or self.avatar_collapsed) and self.settings.card_position:
            self.bubble.move(*clamp_position(self.settings.card_position,(self.bubble.width(),self.bubble.height()),self.screens()))
            self._card_placed=True
        self.position_bubble()

    def position_bubble(self, *_):
        if self.shutting_down or self._positioning:return
        self._positioning=True
        try:
            size=(self.bubble.width(),self.bubble.height())
            if (self.settings.card_only or self.avatar_collapsed) and self._card_placed:
                x,y=clamp_position((self.bubble.x(),self.bubble.y()),size,self.screens())
            else:
                rect=Rect(self.pet.x(),self.pet.y(),self.pet.width(),self.pet.height())
                visible=self.pet.content_rect()
                anchor=Rect(rect.x+visible.x(),rect.y+visible.y(),visible.width(),visible.height())
                self.bubble.fit_height(panel_height_limit(rect,anchor,self.screens()))
                size=(self.bubble.width(),self.bubble.height())
                fitted=fit_capsule_pet(rect,size,self.screens(),anchor=anchor)
                if fitted!=(rect.x,rect.y):
                    self.pet.move(*fitted)
                    anchor=Rect(anchor.x+fitted[0]-rect.x,anchor.y+fitted[1]-rect.y,anchor.width,anchor.height)
                    rect=Rect(*fitted,rect.width,rect.height)
                x,y=card_position(rect,size,self.screens(),compact=self.bubble.compact,anchor=anchor)
            self.bubble.move(x,y);self._last_card_pos=(x,y);self._card_placed=True
            if self.avatar_collapsed and self.bubble.compact:
                self._capsule_anchor=Rect(x,y,*size)
        finally:self._positioning=False

    def reset_to_corner(self):
        if self.settings.card_only or self.avatar_collapsed:
            screen=QGuiApplication.primaryScreen().availableGeometry()
            position=clamp_position((screen.right()+1-self.bubble.width()-24,screen.bottom()+1-self.bubble.height()-24),
                                    (self.bubble.width(),self.bubble.height()),self.screens())
            self.bubble.move(*position);self._last_card_pos=position;self._card_placed=True
            if self.avatar_collapsed and self.bubble.compact:self._capsule_anchor=Rect(*position,self.bubble.width(),self.bubble.height())
            self.save_position()
        else:self.reset_position();self.save_position()

    def card_moved(self,x,y):
        if not self.settings.card_only and not self.avatar_collapsed and self._last_card_pos:
            dx,dy=x-self._last_card_pos[0],y-self._last_card_pos[1]
            self.pet.move(*clamp_position((self.pet.x()+dx,self.pet.y()+dy),(self.pet.width(),self.pet.height()),self.screens()))
            self.position_bubble()
        else:
            position=clamp_position((x,y),(self.bubble.width(),self.bubble.height()),self.screens())
            self.bubble.move(*position);self._last_card_pos=position
            if self.avatar_collapsed and self.bubble.compact:self._capsule_anchor=Rect(*position,self.bubble.width(),self.bubble.height())
        self.schedule_position_save()

    def save_compact(self,value):
        if not value and self.avatar_collapsed:self.restore_avatar(persist=False)
        if not value and self.settings.card_only:self.avatar_collapsed=False
        self.bubble.set_avatar_hidden(self.avatar_collapsed or self.settings.card_only,self.settings.card_only)
        self.settings=replace(self.settings,compact=value,avatar_collapsed=self.avatar_collapsed,
                              card_position=(self.bubble.x(),self.bubble.y()) if self.avatar_collapsed else self.settings.card_position)
        save_settings(self.root,self.settings)
        self.dialog.settings=self.settings

    def collapse_avatar(self):
        self.bubble.minimal=False
        self.user_visible=True;self.bubble.show();self.bubble.set_compact(True,manual=True)
        self.avatar_collapsed=True;self.pet.hide()
        self.idle_director.cancel();self.ambient_director.cancel();self.finish_interaction(refresh=False)
        self._capsule_anchor=Rect(self.bubble.x(),self.bubble.y(),self.bubble.width(),self.bubble.height())
        self.settings=replace(self.settings,compact=True,avatar_collapsed=True,card_position=self.bubble.pos().toTuple())
        self.bubble.set_avatar_hidden(True,self.settings.card_only)
        self.dialog.settings=self.settings;save_settings(self.root,self.settings);self.position_bubble()

    def toggle_avatar(self):
        if self.avatar_collapsed or self.settings.card_only:self.show_avatar()
        else:self.collapse_avatar()

    def restore_avatar(self,*,exit_card_only=False,persist=True):
        if self.settings.card_only and not exit_card_only:return
        detached=self.avatar_collapsed or self.settings.card_only
        capsule=self._capsule_anchor or Rect(self.bubble.x(),self.bubble.y(),self.bubble.width(),self.bubble.height())
        was_card_only=self.settings.card_only
        self.user_visible=True;self.avatar_collapsed=False
        self.settings=replace(self.settings,avatar_collapsed=False,card_only=False if exit_card_only else self.settings.card_only)
        if was_card_only:self.restore_character()
        if detached:
            rect=Rect(self.pet.x(),self.pet.y(),self.pet.width(),self.pet.height());visible=self.pet.content_rect()
            anchor=Rect(rect.x+visible.x(),rect.y+visible.y(),visible.width(),visible.height())
            self.pet.move(*pet_below_capsule(rect,anchor,capsule,self.screens()))
        self.bubble.minimal=self.settings.minimal
        self.bubble.set_mode(self.bubble.mode)
        self.pet.setVisible(not self.settings.card_only)
        self.bubble.set_avatar_hidden(self.settings.card_only,self.settings.card_only)
        self.dialog.card_only.setChecked(self.settings.card_only);self.dialog.settings=self.settings
        self.position_bubble()
        if persist:save_settings(self.root,self.settings);self.schedule_position_save()

    def show_avatar(self):
        self.restore_avatar(exit_card_only=True)
        self.bubble.show();self.refresh()

    def open_card(self):
        self.restore_avatar()
        self.finish_interaction()
        self.user_visible=True
        self.pet.setVisible(not self.settings.card_only)
        self.bubble.show();self.bubble.open_summary(manual=True)
        self.position_bubble()
        self.bubble.raise_();self.bubble.activateWindow()

    def populate_menu(self,menu):
        from .builtin import BUILTIN_PACKS,builtin_pack
        submenu=menu.character_menu;submenu.clear()
        packs=[builtin_pack(key) for key in BUILTIN_PACKS]+self.library.list_packs()
        for pack in packs:
            action=submenu.addAction(pack.name);action.setCheckable(True)
            action.setChecked(pack.key==self.settings.character);action.setData(pack.key)
            action.triggered.connect(lambda checked=False,key=pack.key:self.activate_character(key))
        submenu.addSeparator();submenu.addAction('管理素材…',lambda:self.open_page('materials'))
        for key,action in menu.mode_actions.items():
            action.setChecked(self.settings.minimal if key=='minimal' else not self.settings.minimal)

    def set_display_mode(self,minimal):
        self.restore_avatar(exit_card_only=True)
        self.settings=replace(self.settings,minimal=minimal,compact=True)
        self.bubble.minimal=minimal;self.bubble.set_compact(True)
        self.dialog.settings=self.settings
        save_settings(self.root,self.settings);self.bubble.show();self.position_bubble()

    def open_page(self,key):
        if key.startswith('mode:'):
            self.set_display_mode(key=='mode:minimal');return
        if key=='chat':self.open_current_conversation();return
        if key=='summary':self.open_card();return
        self.finish_interaction()
        if key=='capsule':
            self.collapse_avatar()
        else:
            self.restore_avatar()
            self.user_visible=True;self.pet.setVisible(not self.settings.card_only);self.bubble.show()
            self.bubble.open_page(key)
            self.position_bubble();self.bubble.raise_();self.bubble.activateWindow()

    def interact(self):
        now=time.monotonic()
        if self.last_pet_click>=0 and now-self.last_pet_click<.35:return
        self.last_pet_click=now
        response=response_for_click(self.interaction_index);self.interaction_index+=1
        self.respond(response)

    def respond(self,response):
        if not self.user_visible or self.settings.card_only or self.shutting_down:return
        self.idle_director.cancel()
        seconds=13 if self.active_pack and self.active_pack.schema==3 else response.seconds
        self.active_interaction=response;self.interaction_deadline=time.monotonic()+seconds
        self.bubble.show_interaction(response.text,response.seconds)
        # Authored animation already contains its gesture; never stack a window hop.
        if not self.active_pack or response.action not in self.active_pack.actions:self.pet.play_interaction_motion()
        self.interaction_timer.start(round(seconds*1000));self.refresh()

    def finish_long_interaction(self):
        if self.active_interaction and self.active_pack and self.active_pack.schema==3:
            self.finish_interaction()

    def finish_interaction(self,refresh=True):
        was_active=self.active_interaction is not None
        self.interaction_timer.stop();self.active_interaction=None;self.interaction_deadline=0
        self.bubble.clear_interaction()
        if was_active and refresh and not self.shutting_down:self.refresh()

    def pet_activity(self):
        self.idle_director.cancel()
        self.ambient_director.cancel()
        self.finish_interaction(refresh=False)
        self.refresh()

    def enable_card_only(self):
        self.apply_settings(replace(self.settings,card_only=True))

    def restore_character(self):
        self.idle_director.cancel()
        self.ambient_director.cancel()
        self.active_pack=None
        self.player.clear()
        if self.settings.card_only:return
        from .builtin import builtin_pack,BUILTIN_PACKS
        if self.settings.character in BUILTIN_PACKS:
            self.active_pack=builtin_pack(self.settings.character)
            self.player.load(self.active_pack,'idle')
        else:
            try:
                self.active_pack=self.library.load(self.settings.character)
                self.player.load(self.active_pack,'idle')
            except MaterialError:
                self.active_pack=builtin_pack();self.player.load(self.active_pack,'idle')
                self.settings=replace(self.settings,character='builtin')
                save_settings(self.root,self.settings)
                self.bubble.materials.status.setText('所选素材不可用，已恢复内置角色。')
        self.player.set_visible(self.pet.isVisible())
        self.bubble.materials.reload(self.settings.character)
        if not self.active_pack and self.pet.isVisible():self.pet.timer.start()

    def activate_character(self,key):
        previous=self.settings
        try:
            from .builtin import builtin_pack,BUILTIN_PACKS
            if key not in BUILTIN_PACKS:
                candidate=self.library.load(key,force=True)
                self.player.load(candidate,derive_display(self.sessions,time.time()).state)
                self.active_pack=candidate
            else:
                from .builtin import builtin_pack
                self.active_pack=builtin_pack(key,force=True);self.player.load(self.active_pack,'idle')
            self.apply_settings(replace(previous,character=key,card_only=False))
            self.bubble.materials.status.setText('所选角色已启用。')
        except MaterialError as error:self.bubble.materials.status.setText(str(error))

    def remove_character(self,key):
        from .builtin import BUILTIN_PACKS
        if not key or key in BUILTIN_PACKS:return
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

    def open_balance(self):
        if not self.settings.balance_enabled:
            self.show_binding()
            return
        self.open_card()
        self.next_balance=0
        self.load_balance()

    def refresh_data(self):
        self.load_data(self.bubble.range.currentData())
        if self.settings.balance_enabled:
            self.next_balance=0
            self.load_balance()
        self.next_checkin=0;self.load_checkin()

    def quick_clicked(self):
        from .windows import open_website,WORKBUDDY_WEBSITE
        try:
            if self.settings.quick_action=='checkin':self.checkin_clicked()
            elif self.settings.quick_action=='refresh':self.refresh_data();self.bubble.show_interaction('正在刷新积分和统计',3)
            else:open_website(WORKBUDDY_WEBSITE if self.settings.quick_action=='website' else self.settings.quick_url)
        except (OSError,ValueError):
            self.open_settings();self.dialog.hint.setText('网页地址无效或无法打开，请填写 http:// 或 https:// 地址。')

    def load_checkin(self):
        if not self.settings.checkin_enabled:
            self.next_checkin=float('inf')
            self.checkin_snapshot=CheckinSnapshot('disabled',message='每日签到未启用，点击在设置中授权')
            self.bubble.set_checkin(self.checkin_snapshot)
            return
        if self.demo or self.shutting_down or self.checkin_job:return
        self._start_checkin(False)

    def checkin_clicked(self):
        if not self.settings.checkin_enabled:
            self.open_settings();self.dialog.hint.setText('勾选“授权查询签到，点击按钮时领取”并保存；仅点击签到按钮会领取积分。')
            QTimer.singleShot(0,self.focus_checkin_setting)
            return
        if self.demo:
            self.bubble.show_interaction('演示模式不会领取积分',4);return
        if self.checkin_job or self.shutting_down:return
        self._start_checkin(True)

    def focus_checkin_setting(self):
        if not self.shutting_down:
            self.bubble.tabs.pages.widget(PAGE_KEYS.index('settings')).ensureWidgetVisible(self.dialog.checkin_enabled,8,16)

    def _start_checkin(self,claim):
        self.next_checkin=time.monotonic()+300;started_day=local_day()
        self.bubble.set_checkin_busy(claim)
        def function():
            if not self.settings.checkin_enabled or self.checkin_job is None or self.checkin_job.cancel.is_set():
                return CheckinSnapshot('disabled',message='签到授权未启用')
            if claim:return perform_checkin(self.workbuddy_home,lambda:not self.settings.checkin_enabled or self.checkin_job is None or self.checkin_job.cancel.is_set())
            return read_checkin(self.workbuddy_home)
        self.checkin_job=Task(function,self)
        def received(snapshot):
            if self.shutting_down or not self.settings.checkin_enabled:return
            if not claim and started_day!=local_day():self.next_checkin=0;return
            self.checkin_snapshot=snapshot;self.bubble.set_checkin(snapshot)
            if claim:
                if snapshot.state=='claimed':
                    text=f'签到成功，领取 {snapshot.awarded:g} 积分！' if snapshot.awarded is not None else '签到成功，正在刷新积分～'
                    self.respond(Interaction(text,'done',5))
                elif snapshot.checked:self.respond(Interaction('今天已经签到过啦～','waiting'))
                else:self.bubble.show_interaction(snapshot.message,5)
                if snapshot.checked:
                    if self.settings.balance_enabled:self.next_balance=0;self.load_balance()
                    self.next_checkin=time.monotonic()+5
                elif snapshot.state in ('uncertain','error'):self.next_checkin=time.monotonic()+5
        def failed(_):
            if self.shutting_down or not self.settings.checkin_enabled:return
            self.checkin_snapshot=CheckinSnapshot('uncertain' if claim else 'unknown',message='签到结果待确认，请刷新或打开 WorkBuddy')
            self.bubble.set_checkin(self.checkin_snapshot);self.next_checkin=time.monotonic()+5
        def finished():
            job=self.checkin_job;self.checkin_job=None
            if job:job.deleteLater()
            if not self.shutting_down and self.settings.checkin_enabled and self.next_checkin<=time.monotonic():self.load_checkin()
        self.checkin_job.done.connect(received);self.checkin_job.failed.connect(failed)
        self.checkin_job.finished.connect(finished);self.checkin_job.start()

    def load_balance(self):
        if not self.settings.balance_enabled:
            self.bubble.set_balance(None,'在设置中启用“授权本地查询剩余积分”')
            self.bubble.balance_badge.setText('积分未启用')
            self.bubble.resize_balance_badge()
            self.bubble.balance_label.setText('剩余可用积分：未启用')
            return
        if self.demo or self.balance_job or self.shutting_down:return
        self.next_balance=time.monotonic()+60
        self.last_balance_query=time.monotonic()
        self.balance_job=Task(lambda:read_balance(self.workbuddy_home),self)
        def received(snapshot):
            if not self.settings.balance_enabled or self.shutting_down:return
            stamp=time.strftime('%H:%M:%S',time.localtime(snapshot.at)) if snapshot.at else ''
            self.bubble.set_balance(snapshot.remaining,snapshot.message+(' · '+stamp+' 更新' if stamp else ''))
        def finished():
            job=self.balance_job;self.balance_job=None
            if job:job.deleteLater()
        self.balance_job.done.connect(received)
        self.balance_job.failed.connect(lambda _:self.bubble.set_balance(None,'余额查询暂不可用'))
        self.balance_job.finished.connect(finished)
        self.balance_job.start()

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
        if self.settings.card_only or self.avatar_collapsed:
            position=clamp_position((self.bubble.x(),self.bubble.y()),(self.bubble.width(),self.bubble.height()),self.screens())
            self.bubble.move(*position)
            self.settings=replace(self.settings,card_position=position)
            save_settings(self.root,self.settings)
            return
        x, y = clamp_position((self.pet.x(), self.pet.y()), (self.pet.width(), self.pet.height()), self.screens())
        self.pet.move(x, y)
        self.settings = replace(self.settings, position=(x, y))
        save_settings(self.root, self.settings)
        self.position_bubble()

    def consume(self, events):
        if self.settings.balance_enabled and any(event.kind=='Stop' for event in events):
            self.next_balance=min(self.next_balance,max(time.monotonic()+3,self.last_balance_query+15))
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
        now=time.monotonic()
        if self.active_interaction and (now>=self.interaction_deadline or display.state in ('review','waiting','failed')
                                       or not self.pet.isVisible()):
            self.finish_interaction(refresh=False)
        eligible=(self.pet.isVisible() and not self.settings.card_only and not self.active_interaction
                  and self.bubble.mode in ('capsule','summary') and self.pet.press_position is None
                  and not self.pet.context_menu.isVisible() and not self.bubble.context_menu.isVisible()
                  and idle_allowed(self.sessions,display,time.time()))
        leisure=self.idle_director.step(now,eligible)
        ambient=self.ambient_director.step(now,eligible and not leisure and bool(self.active_pack and 'idle_scratch' in self.active_pack.actions))
        base='idle' if display.state=='done' and idle_allowed(self.sessions,display,time.time()) else display.state
        action=self.active_interaction.action if self.active_interaction else leisure.action if leisure else ambient.action if ambient else base
        self.visual_action=action
        self.pet.set_display(display)
        self.bubble.set_display(display)
        if self.active_pack and self.pet.isVisible():
            try:self.player.load(self.active_pack,action,defer=not self.active_interaction and action not in ('review','waiting','failed'))
            except MaterialError:
                self.player.clear();self.active_pack=None
                self.pet.timer.start()
                self.bubble.materials.status.setText('动画读取失败，已暂时使用内置角色。')
        self.pet.set_visual(action,fallback=not self.active_pack or action not in self.active_pack.actions
                            or action=='working' and self.active_pack.schema==1)
        self.bubble.maybe_collapse(self.settings)
        if time.monotonic()>=self.next_data:self.load_data(self.bubble.range.currentData())
        if time.monotonic()>=self.next_balance:self.load_balance()
        day=local_day()
        if day!=self.checkin_day:
            self.checkin_day=day;self.checkin_snapshot=CheckinSnapshot();self.next_checkin=0
            self.bubble.set_checkin(self.checkin_snapshot)
        if time.monotonic()>=self.next_checkin:self.load_checkin()
        for reminder in display.reminders:
            if reminder.id not in self.sent:
                self.sent.add(reminder.id)
                if self.settings.notifications and not self.demo:
                    self.tray.remind(reminder.kind)
        try:
            self.runtime_writer.submit({"schema": 1, "version": __version__, "pid": os.getpid(),
                "at": time.time(), "state": display.state, "connection": display.connection,
                "sessions": display.session_count, "unread": len(display.reminders), "demo": self.demo,
                "visible": self.bubble.isVisible(), "card_only":self.settings.card_only,
                "compact":self.bubble.compact,"view_mode":self.bubble.mode,"balance_available":self.bubble.balance is not None,
                "animation_loaded":bool(self.player.frames),
                "chat_behavior":"open-workbuddy",
                "visual_action":self.visual_action,"leisure":self.idle_director.active is not None,
                "interacting":self.active_interaction is not None and time.monotonic()<self.interaction_deadline,
                "avatar_collapsed":self.avatar_collapsed,"pet_visible":self.pet.isVisible(),
                "ambient":self.ambient_director.active is not None,
                "checkin_state":self.checkin_snapshot.state,
                "panel_gap":self.pet.y()+self.pet.content_rect().y()-self.bubble.y()-self.bubble.height() if not self.settings.card_only else None,
                "capsule_gap":self.pet.y()+self.pet.content_rect().y()-self.bubble.y()-self.bubble.height()
                    if self.bubble.compact and not self.settings.card_only else None,
                "position": [self.pet.x(), self.pet.y()]})
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
        self.open_page('settings')

    def apply_settings(self, settings):
        try:
            previous=self.settings
            if settings.workbuddy_path:
                validate_workbuddy_path(Path(settings.workbuddy_path))
            if settings.quick_action=='custom':
                from .windows import website_url
                website_url(settings.quick_url)
            if settings.startup != self.settings.startup:
                from .integration import runtime_command
                configure_startup(settings.startup, runtime_command(self.root))
            save_settings(self.root, settings)
            self.settings = settings
            if settings.card_only or previous.character!=settings.character:
                self.idle_director.cancel();self.finish_interaction(refresh=False)
            self.next_balance=0
            self.next_checkin=0
            if not settings.checkin_enabled and self.checkin_job:self.checkin_job.cancel.set()
            self.pet.set_pet_size(settings.size)
            self.bubble.set_quick_action(settings.quick_action,settings.quick_url)
            self.bubble.set_avatar_hidden(settings.card_only or self.avatar_collapsed,settings.card_only)
            self.pet.setVisible(self.user_visible and not settings.card_only and not self.avatar_collapsed)
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
        except (OSError, ValueError) as error:
            if self.dialog:
                self.dialog.hint.setText(str(error) if isinstance(error,ValueError) else '保存失败，请检查用户目录是否可写。')

    def first_binding(self):
        if self.shutting_down or self.demo:return
        if not self.settings.onboarding_done:
            if self.settings.balance_enabled and (self.root/'integration-receipt.json').is_file():
                self.settings=replace(self.settings,onboarding_done=True);save_settings(self.root,self.settings)
            else:self.show_binding()

    def show_binding(self):
        from .ui.onboarding import BindingDialog
        if self.binding is None:
            self.binding=BindingDialog(self.bubble)
            self.binding.bind_requested.connect(self.complete_binding)
            self.binding.detect_requested.connect(self.detect_workbuddy)
        self.binding.found(self.settings.workbuddy_path)
        self.binding.show();self.binding.raise_();self.binding.activateWindow()
        self.detect_workbuddy()

    def detect_workbuddy(self):
        if self.discovery_job or self.shutting_down:return
        def find():
            if self.settings.workbuddy_path:
                try:return validate_workbuddy_path(Path(self.settings.workbuddy_path))
                except (ValueError,OSError):pass
            return discover_workbuddy()
        self.discovery_job=Task(find,self)
        def received(path):
            if path:
                self.settings=replace(self.settings,workbuddy_path=str(path));save_settings(self.root,self.settings)
                self.dialog.path.setText(str(path));self.dialog.settings=self.settings
            self.dialog.hint.setText('已检测到 WorkBuddy。' if path else '未找到 WorkBuddy，请启动后重新检测或手动选择。')
            if self.binding:self.binding.found(path)
        def finished():
            job=self.discovery_job;self.discovery_job=None
            if job:job.deleteLater()
        self.discovery_job.done.connect(received);self.discovery_job.finished.connect(finished);self.discovery_job.start()

    def complete_binding(self,balance,checkin):
        from .integration import install_integration
        try:
            validate_workbuddy_path(Path(self.settings.workbuddy_path))
            install_integration(self.workbuddy_home,self.root)
            self.apply_settings(replace(self.settings,balance_enabled=balance,checkin_enabled=checkin,onboarding_done=True))
            self.dialog.balance_enabled.setChecked(balance);self.dialog.checkin_enabled.setChecked(checkin)
            if self.binding:self.binding.accept()
            self.refresh_data()
            self.bubble.show_interaction('已完成绑定，正在同步积分',5)
        except (OSError,ValueError):
            if self.binding:self.binding.hint.setText('绑定失败，未开启新的积分授权。请检查程序位置和目录写入权限后重试。')

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
        self.pet.setVisible(self.user_visible and not self.settings.card_only and not self.avatar_collapsed)
        self.bubble.setVisible(self.user_visible)
        if not self.user_visible:
            self.idle_director.cancel();self.finish_interaction(refresh=False)
            self.ambient_director.cancel()
        self.refresh()

    def demo_step(self):
        sequence = ("UserPromptSubmit", "PreToolUse", "PermissionRequest", "PostToolUse", "Stop")
        kind = sequence[self.demo_index % len(sequence)]
        self.consume([Event(f"demo-{self.demo_index}", time.time(), "demo-session", kind)])
        self.demo_index += 1

    def capture(self, path: Path):
        from PySide6.QtGui import QColor, QPainter, QPixmap
        bounds=self.bubble.geometry()
        if self.pet.isVisible():bounds=bounds.united(self.pet.geometry())
        bounds=bounds.adjusted(-16,-16,16,16)
        import math
        ratio=self.bubble.devicePixelRatioF()
        image = QPixmap(math.ceil(bounds.width()*ratio),math.ceil(bounds.height()*ratio))
        image.setDevicePixelRatio(ratio)
        image.fill(QColor("#eef5fa"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(self.bubble.x()-bounds.x(),self.bubble.y()-bounds.y(), self.bubble.grab())
        if self.pet.isVisible():painter.drawPixmap(self.pet.x()-bounds.x(),self.pet.y()-bounds.y(), self.pet.grab())
        painter.end()
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(path))

    def shutdown(self):
        if self.shutting_down:
            return
        self.shutting_down = True
        self.timer.stop()
        self.interaction_timer.stop()
        self.idle_director.cancel()
        self.ambient_director.cancel()
        if self.demo and hasattr(self,'demo_timer'):self.demo_timer.stop()
        if self.stats_job:self.stats_job.cancel.set()
        if self.balance_job:self.balance_job.cancel.set()
        if self.checkin_job:self.checkin_job.cancel.set()
        if self.discovery_job:self.discovery_job.cancel.set()
        self.updates.shutdown()
        if self.binding:self.binding.close()
        self.bubble.materials.shutdown()
        self.pet.context_menu.hide();self.bubble.context_menu.hide()
        self.player.clear()
        if self.worker:
            self.worker.requestInterruption()
            self.worker.wait(3000)
        self.save_position()
        self.runtime_writer.close()
        self.tray.hide()
        self.bubble.hide()
        self.pet.hide()


def run_app(root: Path, demo=False, *, quit_requested=False, show_settings=False,
            smoke_seconds=0, capture: Path | None = None, workbuddy_home: Path | None = None, card_only=False,
            capture_page='summary',open_chat=False) -> int:
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
        socket.write(b"quit" if quit_requested else b"card-only" if card_only else b"chat" if open_chat else b"settings" if show_settings else b"show")
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
            elif command == b'chat':
                controller.open_current_conversation()
            else:
                controller.user_visible = True
                if not controller.settings.card_only:controller.restore_avatar()
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
    if open_chat:QTimer.singleShot(0,controller.open_current_conversation)
    if capture:
        def capture_view():
            if capture_page=='interaction':controller.bubble.set_compact(True);controller.interact()
            elif capture_page in ('capsule','summary'):controller.bubble.set_mode(capture_page)
            else:controller.bubble.open_page(capture_page)
            app.processEvents()
            controller.capture(capture)
        QTimer.singleShot(700,capture_view)
    if smoke_seconds > 0:
        QTimer.singleShot(int(smoke_seconds * 1000), app.quit)
    return app.exec()
