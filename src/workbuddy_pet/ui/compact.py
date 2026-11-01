"""Persistent compact window: two header actions and existing local data."""
import math
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPainter,QPainterPath,QPen,QColor,QFontMetrics
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton
from .icons import action_button
from .theme import palette_for


class TrendChart(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.series=();self.theme_key='gray';self.setFixedHeight(43)
        self.setAccessibleName('近7天本机积分趋势')

    def set_series(self,series,message=''):
        self.series=tuple(series)
        self.setToolTip(('\n'.join(f'{x.day}  {x.credit:,.3f} 积分 · {x.requests} 次请求' for x in series)+'\n' if series else '')+message)
        self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);colors=palette_for(self.theme_key)
        if not self.series:
            p.setPen(QColor('#7b8190'));p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'暂无可用趋势');return
        rect=QRectF(5,5,max(1,self.width()-10),self.height()-10)
        maximum=max(1,max(x.credit for x in self.series))
        points=[QPointF(rect.left()+i*rect.width()/max(1,len(self.series)-1),rect.bottom()-x.credit/maximum*rect.height()) for i,x in enumerate(self.series)]
        line=QPainterPath(points[0])
        for point in points[1:]:line.lineTo(point)
        area=QPainterPath(line);area.lineTo(rect.right(),rect.bottom());area.lineTo(rect.left(),rect.bottom());area.closeSubpath()
        fill=QColor(colors.accent);fill.setAlpha(24);p.fillPath(area,fill)
        p.setPen(QPen(QColor(colors.border),1));p.drawLine(rect.bottomLeft(),rect.bottomRight())
        p.setPen(QPen(QColor(colors.accent),1.8));p.drawPath(line)
        p.setBrush(QColor(colors.accent));p.setPen(Qt.PenStyle.NoPen)
        for point in points:p.drawEllipse(point,2,2)


class CompactPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.theme_key='gray'
        layout=QVBoxLayout(self);layout.setContentsMargins(12,9,12,9);layout.setSpacing(5)
        header=QHBoxLayout();header.setSpacing(4)
        self.unread=QLabel('WorkBuddy');self.unread.setTextFormat(Qt.TextFormat.PlainText)
        self.capsule_button=action_button('collapse','切回胶囊模式')
        self.expand_button=action_button('details','打开数据看板')
        self.header_buttons=(self.capsule_button,self.expand_button)
        for button in self.header_buttons:button.setFixedSize(24,24)
        header.addWidget(self.unread);header.addStretch()
        for button in self.header_buttons:header.addWidget(button)
        layout.addLayout(header)
        self.session=QPushButton('打开 WorkBuddy ↗');self.session.setFixedHeight(24)
        layout.addWidget(self.session)
        self.state=QLabel('待命');self.state.setFixedHeight(18);self.state.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.state)
        row=QHBoxLayout();row.setSpacing(7)
        self.metric_frames=[]
        self.remaining,self.balance_note=self.create_metric(row,'剩余积分','个人账户')
        self.today,self.today_note=self.create_metric(row,'今日消耗','本机记录')
        layout.addLayout(row)
        footer=QHBoxLayout();self.trend_caption=QLabel('近7天 · 本机积分');self.trend_dates=QLabel('')
        footer.addWidget(self.trend_caption);footer.addStretch();footer.addWidget(self.trend_dates);layout.addLayout(footer)
        self.chart=TrendChart(self);layout.addWidget(self.chart)
        self.apply_theme('gray')

    def create_metric(self,row,title,note):
        frame=QWidget();frame.setObjectName('windowMetric');box=QVBoxLayout(frame);box.setContentsMargins(9,6,9,6);box.setSpacing(1)
        label=QLabel(title);label.setStyleSheet('font-size:10px;color:#6c7482;')
        number=QLabel('—');number.setMinimumWidth(0);number.setFixedHeight(29)
        foot=QLabel(note);foot.setStyleSheet('font-size:10px;color:#6c7482;')
        for widget in (label,number,foot):box.addWidget(widget)
        row.addWidget(frame,1);self.metric_frames.append(frame);return number,foot

    def apply_theme(self,key):
        self.theme_key=key;p=palette_for(key)
        self.unread.setStyleSheet(f'font-size:11px;font-weight:600;color:{p.accent};')
        self.session.setStyleSheet(f'QPushButton{{text-align:left;background:{p.soft};border:1px solid {p.border};border-radius:5px;padding:2px 6px;color:{p.accent};font-size:11px;}} QPushButton:hover{{border-color:{p.accent};}}')
        self.state.setStyleSheet('color:#545d6c;font-size:11px;')
        for frame in self.metric_frames:frame.setStyleSheet(f'QWidget#windowMetric{{background:{p.soft};border-radius:9px;}}')
        for number in (self.remaining,self.today):number.setStyleSheet('font-family:"Segoe UI","Microsoft YaHei UI";font-size:23px;font-weight:800;color:#273345;')
        for label in (self.trend_caption,self.trend_dates):label.setStyleSheet('color:#6c7482;font-size:10px;')
        self.chart.theme_key=key;self.chart.update()
        for number in (self.remaining,self.today):self.number(number,number.text())

    def number(self,label,text):
        label.setText(text);label.setToolTip(text)
        # Keep the number legible without changing either metric column's width.
        font=label.font();font.setPixelSize(23);font.setBold(True)
        while font.pixelSize()>11 and QFontMetrics(font).horizontalAdvance(text)>112:font.setPixelSize(font.pixelSize()-1)
        label.setFont(font)
        label.setStyleSheet(f'font-family:"Segoe UI","Microsoft YaHei UI";font-size:{font.pixelSize()}px;font-weight:800;color:#273345;')

    def set_balance(self,value,note):
        self.number(self.remaining,f'{math.floor(value):,}' if value is not None else '—');self.remaining.setToolTip(self.remaining.text()+"\n"+note)

    def set_context(self,name,status,reminders,tooltip):
        self.unread.setText(f'{len(reminders)} 条待查看' if reminders else 'WorkBuddy')
        self.session.setText(self.session.fontMetrics().elidedText((name or '打开 WorkBuddy')+' ↗',Qt.TextElideMode.ElideRight,266));self.session.setToolTip(name)
        self.state.setText(self.state.fontMetrics().elidedText(status,Qt.TextElideMode.ElideRight,276));self.state.setToolTip(tooltip)

    def set_snapshot(self,snapshot):
        self.number(self.today,f'{snapshot.today_credit:,.3f}' if snapshot.available else '—')
        self.today_note.setText(f'本机 · {snapshot.today_requests} 次请求' if snapshot.available else '暂不可读')
        self.today.setToolTip(self.today.text()+"\n"+snapshot.message)
        series=snapshot.daily_usage if snapshot.available else ()
        self.chart.set_series(series,snapshot.message+(f'；{snapshot.unknown_time} 次缺时间，未计入趋势' if snapshot.unknown_time else ''))
        self.trend_dates.setText(series[0].day[5:].replace('-','/')+'—'+series[-1].day[5:].replace('-','/') if series else '')
