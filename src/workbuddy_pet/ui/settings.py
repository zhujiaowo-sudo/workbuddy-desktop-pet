from .theme import STYLE,THEME_NAMES
import json
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                              QLabel, QLineEdit, QPushButton, QSpinBox, QTextEdit, QVBoxLayout,QComboBox)

from ..settings import Settings,DISPLAY_MODES,display_mode


class SettingsDialog(QDialog):
    saved = Signal(object)
    changed = Signal()
    install_requested = Signal()
    uninstall_requested = Signal()
    reset_requested = Signal()
    detect_requested = Signal()
    update_requested = Signal()

    def __init__(self, settings: Settings, diagnostic: dict, parent=None, embedded=False):
        super().__init__(parent)
        if embedded:
            from PySide6.QtCore import Qt
            self.setWindowFlags(Qt.WindowType.Widget)
        self.settings = settings
        self.setWindowTitle("WorkBuddy 桌宠设置")
        if not embedded:self.resize(490,500)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        if embedded:layout.setContentsMargins(4,6,4,4)
        heading = QLabel("偏好设置")
        heading.setStyleSheet("font-size:17px;font-weight:600;padding:4px 0;")
        layout.addWidget(heading)
        form = QFormLayout()
        line = QHBoxLayout()
        self.path = QLineEdit(settings.workbuddy_path)
        self.path.setMinimumWidth(70)
        self.path.setPlaceholderText("选择 WorkBuddy.exe")
        browse = QPushButton("选择")
        browse.clicked.connect(self.choose_path)
        line.addWidget(self.path)
        line.addWidget(browse)
        detect=QPushButton('检测');detect.clicked.connect(self.detect_requested);line.addWidget(detect)
        form.addRow("WorkBuddy 位置", line)
        self.size = QSpinBox()
        self.size.setRange(100, 240)
        self.size.setValue(settings.size)
        form.addRow("角色大小", self.size)
        self.notify = QCheckBox("完成或需要确认时通知我")
        self.notify.setChecked(settings.notifications)
        form.addRow("消息提醒", self.notify)
        self.startup = QCheckBox("登录 Windows 后启动桌宠")
        self.startup.setChecked(settings.startup)
        form.addRow("自动启动", self.startup)
        self.card_only = QCheckBox('仅显示卡片，隐藏人物')
        self.card_only.setChecked(settings.card_only)
        self.card_only.hide()
        self.display_mode=QComboBox()
        for label,key in DISPLAY_MODES:self.display_mode.addItem(label,key)
        self.sync_display(settings)
        form.addRow('显示方式',self.display_mode)
        self.theme_combo=QComboBox()
        for label,key in THEME_NAMES:self.theme_combo.addItem(label,key)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(settings.theme));form.addRow('看板配色',self.theme_combo)
        self.transparent=QCheckBox('胶囊透明底');self.transparent.setChecked(settings.capsule_transparent)
        self.transparent.setToolTip('只改变胶囊背景，窗口和大看板保持实底。');form.addRow('胶囊外观',self.transparent)
        self.auto_collapse = QCheckBox('自动收起临时概览（窗口常驻）')
        self.auto_collapse.setChecked(settings.auto_collapse)
        form.addRow('自动收起', self.auto_collapse)
        self.collapse_seconds = QSpinBox()
        self.collapse_seconds.setRange(10,600)
        self.collapse_seconds.setSuffix(' 秒')
        self.collapse_seconds.setValue(settings.collapse_seconds)
        form.addRow('闲置时间', self.collapse_seconds)
        self.balance_enabled=QCheckBox('授权本地查询剩余积分')
        self.balance_enabled.setChecked(settings.balance_enabled)
        self.balance_enabled.setToolTip('使用 WorkBuddy 的本地连接票据查询个人账户余额；票据仅用于本机认证，不上传或保存到桌宠目录。')
        form.addRow('积分余额',self.balance_enabled)
        self.checkin_enabled=QCheckBox('授权查询签到，点击按钮时领取')
        self.checkin_enabled.setChecked(settings.checkin_enabled)
        self.checkin_enabled.setToolTip('通过 WorkBuddy 本地连接查询签到状态；仅点击签到按钮时领取。不自动签到，票据仅用于本机握手。')
        form.addRow('每日签到',self.checkin_enabled)
        self.quick_action=QComboBox()
        for label,key in (('每日签到','checkin'),('WorkBuddy 官网','website'),('自定义网页','custom'),('刷新数据','refresh')):
            self.quick_action.addItem(label,key)
        self.quick_action.setCurrentIndex(self.quick_action.findData(settings.quick_action))
        form.addRow('左侧快捷按钮',self.quick_action)
        self.quick_url=QLineEdit(settings.quick_url);self.quick_url.setPlaceholderText('https://example.com')
        self.quick_url.setEnabled(settings.quick_action=='custom')
        self.quick_action.currentIndexChanged.connect(lambda:self.quick_url.setEnabled(self.quick_action.currentData()=='custom'))
        form.addRow('自定义网页',self.quick_url)
        self.auto_update=QCheckBox('启动及每 6 小时检查新版本');self.auto_update.setChecked(settings.auto_update)
        form.addRow('软件更新',self.auto_update)
        update=QPushButton('检查更新');update.clicked.connect(self.update_requested);form.addRow('',update)
        self.update_status=QLabel('后台检查不影响使用，确认后才下载/安装。');self.update_status.setWordWrap(True);form.addRow('',self.update_status)
        layout.addLayout(form)
        self.hint = QLabel("首次连接将安装本地状态插件。请保存后连接，再在 WorkBuddy 新建一个任务。")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        actions = QHBoxLayout()
        connect = QPushButton("连接 WorkBuddy")
        connect.clicked.connect(self.install_requested)
        disconnect = QPushButton("移除接入")
        disconnect.clicked.connect(self.uninstall_requested)
        reset = QPushButton("重置位置")
        reset.clicked.connect(self.reset_requested)
        for button in (connect, disconnect, reset):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.report = QTextEdit()
        self.report.setReadOnly(True)
        self.report.setMaximumHeight(160)
        self.set_diagnostic(diagnostic)
        diagnostic=QPushButton('连接诊断 ▸');diagnostic.setCheckable(True)
        diagnostic.toggled.connect(self.report.setVisible);layout.addWidget(diagnostic)
        layout.addWidget(self.report);self.report.hide()
        save = QPushButton("保存设置")
        save.setStyleSheet("background:#666666;color:white;font-weight:600;padding:11px;")
        save.clicked.connect(self.save)
        save.setProperty('primary',True)
        save.setStyleSheet('')
        if embedded:save.hide()
        else:layout.insertWidget(1,save)
        for signal in (self.path.textEdited,self.size.valueChanged,self.notify.toggled,self.startup.toggled,
                       self.display_mode.currentIndexChanged,self.auto_collapse.toggled,self.collapse_seconds.valueChanged,
                       self.balance_enabled.toggled,self.checkin_enabled.toggled,self.quick_action.currentIndexChanged,
                       self.quick_url.textEdited,self.auto_update.toggled,self.theme_combo.currentIndexChanged,self.transparent.toggled):signal.connect(self.changed)


    def sync_display(self,settings):
        mode=display_mode(settings)
        self.display_mode.setCurrentIndex(self.display_mode.findData(mode))

    def choose_path(self):
        name, _ = QFileDialog.getOpenFileName(self, "选择 WorkBuddy", self.path.text(), "WorkBuddy (WorkBuddy.exe)")
        if name:
            self.path.setText(name)

    def save(self):
        self.saved.emit(replace(self.settings, workbuddy_path=self.path.text().strip(), size=self.size.value(),
                                notifications=self.notify.isChecked(), startup=self.startup.isChecked(),
                                card_only=self.display_mode.currentData() in ('detached','window_only'),avatar_collapsed=False,
                                window_mode=self.display_mode.currentData() in ('window','window_only'),
                                theme=self.theme_combo.currentData(),capsule_transparent=self.transparent.isChecked(),
                                minimal=self.display_mode.currentData()=='minimal',auto_collapse=self.auto_collapse.isChecked(),
                                collapse_seconds=self.collapse_seconds.value(),balance_enabled=self.balance_enabled.isChecked(),
                                checkin_enabled=self.checkin_enabled.isChecked(),quick_action=self.quick_action.currentData(),
                                quick_url=self.quick_url.text().strip(),auto_update=self.auto_update.isChecked()))

    def set_diagnostic(self, report: dict):
        labels = {"plugin_not_configured": "尚未连接", "waiting_for_event": "已配置，等待 WorkBuddy 新任务",
                  "events_received": "已收到 WorkBuddy 事件"}
        lines = ["连接状态：" + labels.get(report.get("state"), "正在检查"),
                 "程序位置：" + ("有效" if report.get("application_found") else "需要选择 WorkBuddy.exe"),
                 "版本：" + report.get("version", "未知")]
        if report.get("event_counts"):
            lines += ["", "最近收到的事件："] + [f"  {key}：{value}" for key, value in report["event_counts"].items()]
        self.report.setPlainText("\n".join(lines))
