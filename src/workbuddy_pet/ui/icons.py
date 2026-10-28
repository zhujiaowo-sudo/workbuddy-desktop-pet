"""Small original line icons, independent of the system's symbol fonts."""
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QColor,QIcon,QPainter,QPen,QPixmap
from PySide6.QtWidgets import QPushButton


def action_icon(kind):
    pixmap=QPixmap(40,40);pixmap.setDevicePixelRatio(2);pixmap.fill(Qt.GlobalColor.transparent)
    p=QPainter(pixmap);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#608eae'),1.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
    if kind=='refresh':
        p.drawArc(QRectF(4,4,12,12),45*16,290*16);p.drawLine(16,3,16,7);p.drawLine(16,7,12,7)
    elif kind=='data':
        for x,y in ((4,11),(9,5),(14,8)):
            p.drawRoundedRect(QRectF(x,y,2,16-y),.5,.5)
    elif kind=='details':
        p.drawRoundedRect(QRectF(5,3,10,14),1,1)
        for y in (7,10,13):p.drawLine(8,y,12,y)
    elif kind=='chat':
        p.drawRoundedRect(QRectF(3,4,14,10),3,3)
        p.drawLine(7,14,5,17);p.drawLine(5,17,11,14)
    elif kind=='settings':
        p.drawEllipse(QRectF(5,5,10,10));p.drawEllipse(QRectF(8,8,4,4))
        for a,b in ((QPointF(10,2),QPointF(10,5)),(QPointF(10,15),QPointF(10,18)),
                    (QPointF(2,10),QPointF(5,10)),(QPointF(15,10),QPointF(18,10))):p.drawLine(a,b)
    elif kind=='website':
        p.drawEllipse(QRectF(3,3,14,14));p.drawEllipse(QRectF(7,3,6,14));p.drawLine(3,10,17,10)
    elif kind=='collapse':p.drawLine(5,10,15,10)
    elif kind=='close':
        p.drawLine(6,6,14,14);p.drawLine(14,6,6,14)
    elif kind=='checkin':
        p.drawRoundedRect(QRectF(4,5,12,11),2,2);p.drawLine(4,8,16,8)
        p.drawLine(7,3,7,6);p.drawLine(13,3,13,6)
        p.drawLine(7,12,9,14);p.drawLine(9,14,13,10)
    elif kind=='checked':
        p.drawLine(5,10,9,14);p.drawLine(9,14,16,6)
    p.end();return QIcon(pixmap)


def action_button(kind,tip):
    button=QPushButton();button.setIcon(action_icon(kind));button.setFixedSize(22,24)
    button.setToolTip(tip);button.setAccessibleName(tip);button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    button.setStyleSheet('QPushButton{background:transparent;border:0;border-radius:6px;padding:0;} '
                         'QPushButton:hover{background:#e4f1fb;} QPushButton:pressed{background:#d5eafa;}')
    return button
