"""Original vector props and motion curves, shared by live fallback and exports."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen


def pose(action, phase):
    wave = math.sin(phase * math.tau)
    if action == 'click_wave': return (0, 0, wave * .8)
    if action == 'click_heart': return (0, 0, wave * .4)
    if action == 'click_shy': return (0, 0, wave * .6)
    if action == 'click_surprised': return (0, 0, 0)
    if action == 'leisure_stretch': return (0, -abs(wave) * .025, wave * 6)
    if action == 'leisure_music': return (wave * .015, -abs(wave) * .008, wave * 3)
    if action == 'working':return (0, 0, 0)
    if action in ('leisure_snack', 'leisure_phone'): return (0, 0, wave * .3)
    return (0, 0, 0)


def transform_character(painter, rect, action, phase):
    dx, dy, angle = pose(action, phase)
    painter.translate(rect.center().x() + dx * rect.width(), rect.bottom() + dy * rect.height())
    painter.rotate(angle)
    painter.translate(-rect.center().x(), -rect.bottom())


def draw_props(p, rect, action, phase):
    """Coordinates follow the visible character, not transparent canvas margins."""
    p.save()
    p.translate(rect.x(), rect.y())
    p.scale(rect.width() / 100, rect.height() / 100)
    p.setPen(QPen(QColor('#4c91a5'), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    wave = math.sin(phase * math.tau)

    def rounded(x, y, w, h, color, radius=3):
        p.setBrush(QColor(color)); p.drawRoundedRect(QRectF(x, y, w, h), radius, radius)

    def line(x, y, xx, yy, color='#70e2bf', width=1.4):
        p.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x, y), QPointF(xx, yy))

    if action == 'working':
        # The monitor's back faces us; its screen faces the character, behind it.
        rounded(12, 72, 5, 24, '#d9c7ac', 1)
        rounded(80, 72, 5, 24, '#d9c7ac', 1)
        rounded(8, 68, 82, 7, '#eddbc0', 2)
        rounded(58, 43, 31, 27, '#bccbdc', 3)
        rounded(70, 61, 5, 13, '#dce6ed', 1)
        rounded(65, 73, 17, 2.5, '#cad8e5', 1)
        rounded(23, 66, 33, 5, '#d5e6ed', 1)
        for row in range(2):
            for col in range(6):
                rounded(26 + col * 4.4, 67 + row * 1.4, 3, .6, '#f4fbff', .2)
        for x, offset in ((28, 0), (43, math.pi)):
            rounded(x, 63 + math.sin(phase * math.tau * 2 + offset) * .6, 8, 4, '#f7e6d9', 1.5)
    elif action == 'leisure_phone':
        p.save();p.translate(64, 65);p.rotate(-9 + wave * 3)
        rounded(-8, -13, 16, 27, '#254c65', 3)
        rounded(-6, -10, 12, 19, '#d5f5f2', 1)
        line(-2, -11, 2, -11, '#a8d3e2', .7)
        offset = (phase * 14) % 7
        for i in range(3):
            rounded(-4, -7 + i * 5 - offset / 3, 8, 2.8, ('#78b9d9', '#89d6bb', '#b8c7eb')[i], 1)
        rounded(4, 3 + wave * 2, 7, 4, '#f7e6d9', 2)
        p.restore()
    elif action == 'leisure_snack':
        rounded(54, 60, 23, 23, '#ffe5ad', 3)
        line(55, 61, 75, 61, '#d6a064')
        rounded(58, 65, 15, 10, '#fff5d6', 2)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#d89e64'))
        p.drawEllipse(QRectF(61, 67, 8, 7))
        for x, y in ((63, 69), (67, 71), (64, 72)):
            p.setBrush(QColor('#8d674b'));p.drawEllipse(QRectF(x, y, 1.3, 1.3))
        rise = (wave + 1) / 2
        cx, cy = 40 + rise * 3, 61 - rise * 15
        p.setBrush(QColor('#e6b66c'));p.drawEllipse(QRectF(cx, cy, 7, 6))
        p.setBrush(QColor('#fff0dc'));p.drawEllipse(QRectF(cx - 3, cy + 3, 9, 4))
        if phase > .65:
            p.setBrush(QColor('#e8b25d'));p.drawEllipse(QRectF(43, 48, 1.2, 1.2))
    elif action in ('leisure_music', 'leisure_stretch'):
        for i in range(3):
            x, y = 10 + i * 37, 24 - ((phase + i / 3) % 1) * 15
            if action == 'leisure_music':
                line(x, y, x, y - 7, '#55a9c7', 1.4)
                line(x, y - 7, x + 5, y - 8, '#55a9c7', 1.4)
                p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#55a9c7'))
                p.drawEllipse(QRectF(x - 4, y - 1, 4, 3))
            else:
                line(x - 2, y, x + 2, y, '#b6cf69', 1)
                line(x, y - 3, x, y + 3, '#b6cf69', 1)
    elif action == 'click_heart':
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, scale in ((15, 29, 1), (80, 17, .8), (75, 46, .6)):
            y -= phase * 5
            heart = QPainterPath(QPointF(x, y + 4 * scale))
            heart.cubicTo(x - 12 * scale, y - 3 * scale, x - 3 * scale, y - 10 * scale, x, y - 4 * scale)
            heart.cubicTo(x + 3 * scale, y - 10 * scale, x + 12 * scale, y - 3 * scale, x, y + 4 * scale)
            p.setBrush(QColor('#f39cae'));p.drawPath(heart)
    elif action == 'click_shy':
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(246, 152, 175, 125))
        p.drawEllipse(QRectF(30, 37, 9, 3));p.drawEllipse(QRectF(61, 37, 9, 3))
        for x in (29, 66):
            line(x, 34, x - 1, 38, '#ed9db2', .6)
    elif action in ('click_wave', 'click_surprised'):
        for i in range(3):
            x, y = 12 + i * 35, 18 - wave * 3
            line(x - 2, y, x + 2, y, '#60b9d1', 1.1)
            line(x, y - 3, x, y + 3, '#60b9d1', 1.1)
    p.restore()
