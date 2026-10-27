"""An original vector mascot and a separate, compact status card."""
import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QMenu

from ..state import DisplayState

COLORS = {"idle": "#65a9d5", "thinking": "#8d85eb", "working": "#3998f2", "review": "#f3aa4f",
          "waiting": "#ee9b69", "done": "#47bba0", "failed": "#e97a89"}
LABELS = {"idle": "我在这里，随时待命", "thinking": "正在思考", "working": "正在执行任务",
          "review": "有操作需要你确认", "waiting": "正在等你的回复", "done": "任务完成啦", "failed": "遇到问题，需要看一下"}
SUBTITLES = {"idle": "陪你把今天的事情做好", "thinking": "正在整理思路，请稍等一下", "working": "有新进展时，我会提醒你",
             "review": "点击打开 WorkBuddy 查看并确认", "waiting": "打开 WorkBuddy 继续对话", "done": "打开 WorkBuddy 查看结果",
             "failed": "打开 WorkBuddy 查看具体情况"}


def mascot_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#4ba5eb"))
    p.drawRoundedRect(QRectF(5, 5, 54, 54), 20, 20)
    p.setBrush(QColor("#153754"))
    p.drawRoundedRect(QRectF(14, 21, 36, 24), 10, 10)
    p.setPen(QPen(QColor("#e9fbff"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(24, 30, 24, 35)
    p.drawLine(40, 30, 40, 35)
    p.end()
    return QIcon(pixmap)


class PetWindow(QWidget):
    open_requested = Signal()
    settings_requested = Signal()
    moved = Signal(int, int)
    acknowledged = Signal()
    page_requested = Signal(str)

    def __init__(self, size: int = 160, demo: bool = False):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("WorkBuddy 桌宠")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(mascot_icon())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.display = DisplayState()
        self.demo = demo
        self.tick = 0
        self.press_position = None
        self.dragging = False
        self.player = None
        self.context_menu = QMenu(self)
        self.context_menu.setStyleSheet('QMenu{background:#fbfeff;border:1px solid #d9e7f1;padding:5px;} QMenu::item{padding:7px 18px;color:#2b506d;} QMenu::item:selected{background:#e7f2fb;border-radius:5px;}')
        for label,key in (('任务详情','details'),('积分与模型','data'),('聊天','chat'),('角色与素材','materials'),('设置与连接','settings')):
            action=self.context_menu.addAction(label)
            action.setData(key)
            action.triggered.connect(lambda checked=False,page=key:self.page_requested.emit(page))
        self.context_menu.addSeparator()
        action=self.context_menu.addAction('收成胶囊');action.setData('capsule')
        action.triggered.connect(lambda:self.page_requested.emit('capsule'))
        self.set_pet_size(size)
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.animate)
        self.timer.start()

    def set_pet_size(self, size: int):
        self.setFixedSize(size + 24, int(size * 1.22) + 24)
        self.update()

    def set_display(self, state: DisplayState):
        self.display = state
        self.update()

    def animate(self):
        if self.player and self.player.frames:
            self.timer.stop()
            return
        if self.isVisible():
            self.tick += 1
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.player and self.player.pixmap:
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            pixmap = self.player.pixmap
            target = pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            p.drawPixmap((self.width()-target.width())//2, self.height()-target.height(), pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            p.end()
            return
        p.scale(self.width() / 184, self.height() / 219)
        t = self.tick / 15
        bob = math.sin(t) * 2.2
        color = QColor(COLORS[self.display.state])
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(6):
            p.setBrush(QColor(29, 66, 102, 4 + i * 2))
            p.drawEllipse(QRectF(38 + i, 190 + i / 2, 108 - i * 2, 15 - i))
        p.translate(0, bob)
        # Soft halo, two antennae, and rounded body. No external art assets.
        p.setBrush(QColor(color.red(), color.green(), color.blue(), 19))
        p.drawEllipse(QRectF(17, 28, 150, 150))
        p.setPen(QPen(QColor("#b5d9ed"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(64, 60), QPointF(53, 40))
        p.drawLine(QPointF(120, 60), QPointF(131, 40))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QRectF(46, 31, 14, 14))
        p.drawEllipse(QRectF(124, 31, 14, 14))
        p.setBrush(QColor("#c3dfef"))
        p.drawRoundedRect(QRectF(48, 169, 29, 22), 11, 11)
        p.drawRoundedRect(QRectF(107, 169, 29, 22), 11, 11)
        gradient = QLinearGradient(40, 55, 145, 175)
        gradient.setColorAt(0, QColor("#ffffff"))
        gradient.setColorAt(1, QColor("#d9eef8"))
        p.setBrush(gradient)
        p.setPen(QPen(QColor("#b8d8e9"), 1.5))
        p.drawRoundedRect(QRectF(34, 53, 116, 126), 47, 47)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#e4f1f8"))
        p.drawEllipse(QRectF(22, 107, 22, 38))
        p.drawEllipse(QRectF(140, 107, 22, 38))
        visor = QLinearGradient(45, 77, 134, 128)
        visor.setColorAt(0, QColor("#224862"))
        visor.setColorAt(1, QColor("#102e47"))
        p.setBrush(visor)
        p.drawRoundedRect(QRectF(45, 77, 94, 57), 25, 25)
        p.setBrush(QColor(255, 255, 255, 17))
        p.drawRoundedRect(QRectF(54, 82, 74, 15), 7, 7)
        p.setPen(QPen(QColor("#b6efff"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        blink = self.tick % 130 in (0, 1, 2)
        for x in (72, 112):
            if self.display.state == "done":
                path = QPainterPath(QPointF(x - 5, 108))
                path.quadTo(x, 99, x + 5, 108)
                p.drawPath(path)
            elif self.display.state == "failed":
                p.drawLine(QPointF(x - 4, 102), QPointF(x + 4, 110))
                p.drawLine(QPointF(x + 4, 102), QPointF(x - 4, 110))
            else:
                p.drawLine(QPointF(x - 3, 106), QPointF(x + 3, 106)) if blink else p.drawLine(QPointF(x, 101), QPointF(x, 111))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(73, 147, 38, 12), 6, 6)
        p.setBrush(QColor("#ffffff"))
        for i in range(3):
            alpha = 255 if self.display.state in ("idle", "done") or self.tick // 7 % 3 == i else 80
            p.setBrush(QColor(255, 255, 255, alpha))
            p.drawEllipse(QRectF(80 + i * 9, 151, 4, 4))
        if self.display.state in ("review", "waiting", "done", "failed"):
            p.setBrush(color)
            p.drawEllipse(QRectF(129, 49, 27, 27))
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            symbol = "✓" if self.display.state == "done" else "!" if self.display.state in ("review", "failed") else "?"
            p.drawText(QRectF(129, 49, 27, 27), Qt.AlignmentFlag.AlignCenter, symbol)
        elif self.display.state in ("thinking", "working"):
            for i in range(3):
                angle = t + i * math.pi * 2 / 3
                p.setBrush(QColor(color.red(), color.green(), color.blue(), 180))
                p.drawEllipse(QRectF(90 + math.cos(angle) * 63, 105 + math.sin(angle) * 67, 6, 6))
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_position = event.globalPosition().toPoint()
            self.origin = self.pos()
            self.dragging = False

    def mouseMoveEvent(self, event):
        if self.press_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.press_position
            self.dragging = self.dragging or delta.manhattanLength() > 6
            if self.dragging:
                self.move(self.origin + delta)
                self.moved.emit(self.x(), self.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.press_position is not None:
            if not self.dragging:
                self.open_requested.emit()
            self.press_position = None

    def contextMenuEvent(self, event):
        self.context_menu.popup(event.globalPos())
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start()
        if self.player:
            self.player.set_visible(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.timer.stop()
        if self.player:
            self.player.set_visible(False)


class StatusBubble(QWidget):
    open_requested = Signal()
    settings_requested = Signal()
    acknowledged = Signal()

    def __init__(self, demo=False):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("WorkBuddy 桌宠状态")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(292)
        self.demo = demo
        self.setStyleSheet("QLabel{background:transparent;color:#24405a;} QPushButton{border:0;border-radius:8px;padding:7px 10px;font-size:11px;} QPushButton:hover{background:#e2f0fa;}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)
        top = QHBoxLayout()
        brand = QLabel("WORKBUDDY  /  小搭子" + ("  · 演示" if demo else ""))
        brand.setStyleSheet("font-size:10px;color:#7291aa;letter-spacing:1px;")
        top.addWidget(brand)
        top.addStretch()
        gear = QPushButton("⋯")
        gear.setStyleSheet("font-size:18px;padding:0;color:#7291aa;")
        gear.setAccessibleName("打开桌宠设置")
        gear.setFixedWidth(28)
        gear.clicked.connect(self.settings_requested)
        top.addWidget(gear)
        layout.addLayout(top)
        self.title = QLabel()
        self.title.setStyleSheet("font-size:15px;font-weight:600;")
        self.subtitle = QLabel()
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("font-size:11px;color:#7c91a4;")
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        buttons = QHBoxLayout()
        open_button = QPushButton("打开 WorkBuddy  ↗")
        open_button.setStyleSheet("color:#3786bf;background:#edf6fd;")
        open_button.clicked.connect(self.open_requested)
        self.ack = QPushButton("知道了")
        self.ack.setStyleSheet("color:#7c91a4;")
        self.ack.clicked.connect(self.acknowledged)
        buttons.addWidget(open_button)
        buttons.addStretch()
        buttons.addWidget(self.ack)
        layout.addLayout(buttons)
        self.set_display(DisplayState())

    def set_display(self, display: DisplayState):
        title, subtitle = LABELS[display.state], SUBTITLES[display.state]
        if display.connection == "disconnected":
            title, subtitle = "等待 WorkBuddy 连接", "打开设置，完成首次连接"
        elif display.connection == "stale":
            subtitle = "暂时没有新进展，点击查看 WorkBuddy"
        self.title.setText(title)
        self.subtitle.setText(subtitle)
        self.ack.setVisible(bool(display.reminders))
        self.adjustSize()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#d7e7f3"), 1))
        p.setBrush(QColor(251, 254, 255, 249))
        p.drawRoundedRect(QRectF(.5, .5, self.width() - 1, self.height() - 1), 18, 18)
        p.end()
