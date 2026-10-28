"""Explicit first-run consent; discovery never reads connection tickets."""
from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QCheckBox,QPushButton,QHBoxLayout


class BindingDialog(QDialog):
    bind_requested=Signal(bool,bool)
    detect_requested=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('连接 WorkBuddy');self.setFixedWidth(370)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet('QDialog{background:#fbfeff;} QLabel,QCheckBox{color:#36516b;} QPushButton{background:#e4f1fb;color:#246b9e;padding:9px;border:0;border-radius:8px;}')
        layout=QVBoxLayout(self)
        title=QLabel('欢迎使用 WorkBuddy 小搭子');title.setStyleSheet('font-size:16px;font-weight:600;');layout.addWidget(title)
        self.status=QLabel('正在自动查找 WorkBuddy…');self.status.setWordWrap(True);layout.addWidget(self.status)
        note=QLabel('完成绑定会安装本地任务状态插件。下列积分功能使用 WorkBuddy 本机连接票据认证，票据不会上传或写入日志；不读取聊天内容，不修改审批。');note.setWordWrap(True);layout.addWidget(note)
        self.balance=QCheckBox('允许查询剩余积分');self.balance.setChecked(True);layout.addWidget(self.balance)
        self.checkin=QCheckBox('允许查询签到；仅我点击签到时领取');self.checkin.setChecked(True);layout.addWidget(self.checkin)
        self.hint=QLabel('请先在 WorkBuddy 登录。状态插件可能需新建任务或重启 WorkBuddy 后生效。');self.hint.setWordWrap(True);layout.addWidget(self.hint)
        row=QHBoxLayout()
        detect=QPushButton('重新检测');detect.clicked.connect(self.detect_requested);row.addWidget(detect)
        later=QPushButton('稍后');later.clicked.connect(self.reject);row.addWidget(later)
        self.bind=QPushButton('同意并完成绑定');self.bind.clicked.connect(lambda:self.bind_requested.emit(self.balance.isChecked(),self.checkin.isChecked()));row.addWidget(self.bind)
        layout.addLayout(row)

    def found(self,path):
        self.status.setText('已找到 WorkBuddy：\n'+str(path) if path else '未找到 WorkBuddy。请先启动它后重新检测，或在设置中选择 WorkBuddy.exe。')
        self.bind.setEnabled(bool(path))
