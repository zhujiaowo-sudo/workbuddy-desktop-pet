from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .pet import mascot_icon


class PetTray(QSystemTrayIcon):
    def __init__(self, parent, show, settings, quit_app):
        super().__init__(mascot_icon(), parent)
        self.setToolTip("WorkBuddy 小搭子")
        self.menu = QMenu()
        for text, callback in (("显示 / 隐藏桌宠", show), ("设置与连接诊断", settings), ("退出桌宠", quit_app)):
            action = QAction(text, self.menu)
            action.triggered.connect(callback)
            self.menu.addAction(action)
        self.setContextMenu(self.menu)
        self.activated.connect(lambda reason: show() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.show()

    def remind(self, kind: str):
        messages = {"done": "任务已完成，点击桌宠打开 WorkBuddy 查看结果。", "review": "有操作需要你在 WorkBuddy 中确认。",
                    "waiting": "WorkBuddy 正在等待你的回复。", "failed": "任务遇到问题，请打开 WorkBuddy 查看。"}
        if self.supportsMessages():
            self.showMessage("WorkBuddy 小搭子", messages[kind], QSystemTrayIcon.MessageIcon.Information, 6000)
