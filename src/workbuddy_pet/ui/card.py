"""Compact opaque card with separate navigation and content surfaces."""
import math
import time
from PySide6.QtCore import Qt,QEvent,Signal,QRectF
from PySide6.QtGui import QColor,QPainter,QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabBar,
    QStackedWidget,QScrollArea,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,
    QAbstractItemView,QLineEdit,QTextEdit,QApplication,QFrame)

from ..state import DisplayState
from .pet import LABELS,SUBTITLES,mascot_icon

PAGE_KEYS=('details','data','chat','materials','settings')


class PageTabs(QWidget):
    """Navigation is outside the scrolled page and has no native baseline."""
    currentChanged=Signal(int)

    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(6)
        self.bar=QTabBar();self.bar.setDrawBase(False);self.bar.setExpanding(True)
        self.bar.setUsesScrollButtons(False);self.bar.setFixedHeight(30)
        self.bar.setStyleSheet('QTabBar::tab{height:28px;padding:0 6px;color:#6d8498;border:0;background:#fbfeff;font-size:11px;} '
            'QTabBar::tab:selected{background:#e6f2fb;color:#226d9f;border-radius:7px;} '
            'QTabBar::tab:hover{background:#eef6fc;}')
        self.pages=QStackedWidget();self.pages.setObjectName('cardPages');self.pages.setMinimumSize(0,0)
        self.pages.setStyleSheet('QStackedWidget#cardPages{background:#fbfeff;border:0;}')
        layout.addWidget(self.bar);layout.addWidget(self.pages,1)
        self.bar.currentChanged.connect(self.pages.setCurrentIndex);self.bar.currentChanged.connect(self.currentChanged)

    def addTab(self,widget,name):
        widget.setObjectName('cardPage')
        widget.setStyleSheet(widget.styleSheet()+'\nQWidget#cardPage{background:#fbfeff;}')
        scroll=QScrollArea();scroll.setObjectName('cardScroll');scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet('QScrollArea#cardScroll{background:#fbfeff;border:0;}')
        scroll.viewport().setAutoFillBackground(True)
        palette=scroll.viewport().palette();palette.setColor(palette.ColorRole.Window,QColor('#fbfeff'));scroll.viewport().setPalette(palette)
        scroll.setWidget(widget);self.pages.addWidget(scroll)
        return self.bar.addTab(name)

    def setCurrentIndex(self,index):self.bar.setCurrentIndex(index)
    def currentIndex(self):return self.bar.currentIndex()
    def count(self):return self.bar.count()
    def tabText(self,index):return self.bar.tabText(index)
    def tabBar(self):return self.bar
    def widget(self,index):return self.pages.widget(index).widget()


class CardWindow(QWidget):
    open_requested=Signal()
    settings_requested=Signal()
    acknowledged=Signal()
    data_requested=Signal(object)
    conversation_requested=Signal(str)
    moved=Signal(int,int)
    compact_changed=Signal(bool)
    resized=Signal()
    balance_requested=Signal()

    def __init__(self,demo=False):
        super().__init__(None,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle('WorkBuddy 小搭子 · 卡片');self.setWindowIcon(mascot_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet('QLabel{color:#2d4a62;} QPushButton{border:0;border-radius:7px;padding:5px 7px;font-size:11px;color:#3179aa;background:#edf6fc;} '
            'QPushButton:hover{background:#dfeefa;} QLineEdit,QTextEdit,QSpinBox{background:white;}')
        self.compact=False;self.demo=demo;self.display=DisplayState()
        self.last_interaction=time.monotonic();self.drag_origin=None;self.pressed=None
        self.local_sessions={};self.current_session=None;self.balance=None
        self.root_layout=QVBoxLayout(self);self.root_layout.setContentsMargins(14,10,14,12);self.root_layout.setSpacing(0)
        self.compact_bar=QWidget();compact=QHBoxLayout(self.compact_bar);compact.setContentsMargins(0,0,0,0);compact.setSpacing(6)
        self.capsule=QPushButton();self.capsule.setFixedHeight(32);self.capsule.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.capsule.setAccessibleName('展开 WorkBuddy 卡片')
        self.capsule.setStyleSheet('background:#e9f4fc;border-radius:16px;color:#28628b;font-size:11px;font-weight:600;')
        self.capsule.clicked.connect(lambda:self.set_compact(False))
        self.balance_badge=QPushButton('积分待同步');self.balance_badge.setFixedSize(86,32);self.balance_badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.balance_badge.setStyleSheet('background:#edf7f2;border-radius:14px;color:#49806b;font-size:10px;padding:3px;')
        self.balance_badge.clicked.connect(self.balance_requested)
        compact.addWidget(self.capsule,1);compact.addWidget(self.balance_badge);self.root_layout.addWidget(self.compact_bar)
        self.full=QWidget();full=QVBoxLayout(self.full);full.setContentsMargins(0,0,0,0);full.setSpacing(6)
        self.header=QWidget();header=QHBoxLayout(self.header);header.setContentsMargins(0,0,0,0);header.setSpacing(6)
        self.brand=QLabel('WORKBUDDY / 小搭子'+(' · 演示' if demo else ''));self.brand.setStyleSheet('font-size:9px;color:#7896ac;')
        self.collapse_button=QPushButton('收起');self.collapse_button.setFixedSize(42,24)
        self.collapse_button.setToolTip('收成胶囊');self.collapse_button.setAccessibleName('收成胶囊')
        self.collapse_button.clicked.connect(lambda:self.set_compact(True,manual=True))
        header.addWidget(self.brand);header.addStretch();header.addWidget(self.collapse_button);full.addWidget(self.header)
        self.title=QLabel();self.title.setStyleSheet('font-size:14px;font-weight:600;')
        self.subtitle=QLabel();self.subtitle.setWordWrap(True);self.subtitle.setStyleSheet('font-size:10px;color:#8197a8;')
        full.addWidget(self.title);full.addWidget(self.subtitle)
        self.session_link=QPushButton();self.session_link.setFixedHeight(24);self.session_link.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.session_link.setStyleSheet('text-align:left;background:#eef7fd;color:#2f7dad;padding:4px 7px;')
        self.session_link.clicked.connect(lambda:self.conversation_requested.emit(self.current_session) if self.current_session else None)
        full.addWidget(self.session_link)
        row=QHBoxLayout();row.setSpacing(6)
        self.open_button=QPushButton('打开 WorkBuddy ↗');self.open_button.clicked.connect(self.open_requested)
        self.data_button=QPushButton('积分与模型');self.data_button.clicked.connect(self.open_data)
        self.ack=QPushButton('已读');self.ack.clicked.connect(self.acknowledged)
        row.addWidget(self.open_button);row.addWidget(self.data_button);row.addStretch();row.addWidget(self.ack);full.addLayout(row)
        self.divider=QFrame();self.divider.setFixedHeight(1);self.divider.setStyleSheet('background:#e1ebf3;border:0;');full.addWidget(self.divider)
        self.tabs=PageTabs();full.addWidget(self.tabs,1);self.root_layout.addWidget(self.full,1)
        self.details=QWidget();detail=QVBoxLayout(self.details);detail.setContentsMargins(4,6,4,4);detail.setSpacing(8)
        self.connection=QLabel();self.connection.setWordWrap(True);detail.addWidget(self.connection)
        help_text=QLabel('任务开始、执行和完成时，小搭子会同步状态。确认操作仍在 WorkBuddy 中处理。')
        help_text.setWordWrap(True);help_text.setStyleSheet('font-size:11px;color:#7891a5;');detail.addWidget(help_text)
        self.session_list=QWidget();self.sessions_layout=QVBoxLayout(self.session_list);self.sessions_layout.setContentsMargins(0,0,0,0)
        self.sessions_layout.addWidget(QLabel('正在读取本机会话…'));detail.addWidget(self.session_list);detail.addStretch()
        self.tabs.addTab(self.details,'详情')
        self.stats=QWidget();stats=QVBoxLayout(self.stats);stats.setContentsMargins(4,6,4,4);stats.setSpacing(8)
        row=QHBoxLayout();self.range=QComboBox()
        for name,days in (('全部',None),('最近7天',7),('最近30天',30)):self.range.addItem(name,days)
        row.addWidget(self.range)
        refresh=QPushButton('刷新');refresh.clicked.connect(lambda:self.data_requested.emit(self.range.currentData()));row.addWidget(refresh)
        stats.addLayout(row);self.range.currentIndexChanged.connect(lambda:self.data_requested.emit(self.range.currentData()))
        self.total=QLabel('正在读取本机统计…');self.total.setStyleSheet('font-size:16px;font-weight:600;');stats.addWidget(self.total)
        self.scope=QLabel();self.scope.setWordWrap(True);stats.addWidget(self.scope)
        self.balance_label=QLabel();self.balance_label.setWordWrap(True);stats.addWidget(self.balance_label)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['模型','请求','积分'])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1,44);self.table.setColumnWidth(2,65);self.table.setMinimumHeight(110);self.table.setMaximumHeight(180)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setStyleSheet('QTableWidget{background:white;border:1px solid #e3edf5;gridline-color:#edf4f8;} '
            'QHeaderView::section{background:#eff6fb;padding:5px;border:0;color:#58788e;}');stats.addWidget(self.table)
        self.missing=QLabel();self.missing.setWordWrap(True);self.missing.setStyleSheet('font-size:10px;color:#8194a4;');stats.addWidget(self.missing)
        self.tabs.addTab(self.stats,'数据')
        self.set_balance(None);self.set_display(DisplayState());self.set_compact(False);self.observe_activity()

    def add_page(self,widget,name):self.tabs.addTab(widget,name);self.observe_activity()

    def observe_activity(self):
        self.installEventFilter(self)
        for widget in self.findChildren(QWidget):widget.installEventFilter(self)

    def eventFilter(self,watched,event):
        if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.KeyPress,QEvent.Type.Wheel):self.last_interaction=time.monotonic()
        return super().eventFilter(watched,event)

    def open_page(self,key):
        if key not in PAGE_KEYS:return
        index=PAGE_KEYS.index(key)
        if index<self.tabs.count():self.tabs.setCurrentIndex(index)
        self.set_compact(False)
        if key=='data':self.data_requested.emit(self.range.currentData())

    def open_data(self):self.open_page('data')

    def set_compact(self,value,manual=False):
        self.compact=bool(value);self.full.setVisible(not value);self.compact_bar.setVisible(value)
        self.root_layout.setContentsMargins(*((8,10,8,10) if value else (14,10,14,12)))
        self.setFixedSize(272,52) if value else self.setFixedSize(360,440)
        self.update_session_link();self.last_interaction=time.monotonic()
        if manual:self.compact_changed.emit(bool(value))
        self.update()

    def maybe_collapse(self,settings,now=None):
        now=time.monotonic() if now is None else now;focus=QApplication.focusWidget()
        editing=isinstance(focus,(QLineEdit,QTextEdit)) and not focus.isReadOnly() and self.isAncestorOf(focus)
        busy=getattr(getattr(self,'chat',None),'job',None) or getattr(getattr(self,'materials',None),'job',None)
        if settings.auto_collapse and not self.compact and self.display.state=='idle' and not self.display.reminders and not editing and not busy and not self.underMouse() and now-self.last_interaction>=settings.collapse_seconds:self.set_compact(True)

    def set_display(self,display):
        self.display=display;title,subtitle=LABELS[display.state],SUBTITLES[display.state]
        if display.connection=='disconnected':title,subtitle='等待 WorkBuddy 连接','打开设置，完成首次连接'
        elif display.connection=='stale':subtitle='暂时没有新进展，可打开 WorkBuddy 查看'
        self.title.setText(title);self.subtitle.setText(subtitle);self.ack.setVisible(bool(display.reminders))
        labels={'connected':'已收到 WorkBuddy 事件','disconnected':'等待 WorkBuddy 连接','stale':'任务状态可能已过期'}
        self.connection.setText(labels.get(display.connection,display.connection)+f' · {display.session_count} 个任务');self.update_session_link()

    def update_session_link(self):
        selected=self.local_sessions.get(self.display.session_id)
        if selected is None and self.local_sessions:selected=next(iter(self.local_sessions.values()))
        self.current_session=selected.id if selected else None;name=selected.title if selected else ''
        self.session_link.setVisible(selected is not None)
        self.session_link.setText(self.session_link.fontMetrics().elidedText(name+' ↗',Qt.TextElideMode.ElideRight,304));self.session_link.setToolTip(name)
        short={'idle':'待命','thinking':'思考中','working':'执行中','waiting':'等回复','review':'待确认','done':'已完成','failed':'需查看'}[self.display.state]
        if self.display.connection=='disconnected':short='待连接'
        text=short+(' · '+name if name else '')
        self.capsule.setText(self.capsule.fontMetrics().elidedText(text,Qt.TextElideMode.ElideRight,148));self.capsule.setToolTip(text+'\n点击展开卡片')

    def set_balance(self,value,source_note='WorkBuddy 余额需要客户端授权接口；本机消耗记录不能推算剩余积分'):
        valid=type(value) in (int,float) and math.isfinite(value) and value>=0
        self.balance=value if valid else None
        text=f'余 {value:,.2f}' if valid else '积分待同步'
        self.balance_badge.setText(self.balance_badge.fontMetrics().elidedText(text,Qt.TextElideMode.ElideRight,80))
        self.balance_badge.setToolTip((f'剩余可用积分：{value:,.2f}\n' if valid else '')+source_note)
        self.balance_label.setText(f'剩余可用积分：{value:,.2f}' if valid else '剩余可用积分：待同步');self.balance_label.setToolTip(source_note)

    def set_snapshot(self,snapshot,active_ids=()):
        self.local_sessions={s.id:s for s in snapshot.sessions};self.update_session_link()
        self.total.setText(f'{snapshot.total_credit:,.3f} 积分 · {snapshot.request_count} 次请求' if snapshot.available else '统计暂不可用')
        self.scope.setText(snapshot.message)
        self.missing.setText(f'{snapshot.unknown_model} 次缺模型，{snapshot.unknown_time} 次缺时间。缺时间不进入日期筛选；上下文不累计为消耗。')
        self.table.setRowCount(len(snapshot.models))
        for row,model in enumerate(snapshot.models):
            for col,text in enumerate((model.model,str(model.requests),f'{model.credit:.3f}')):self.table.setItem(row,col,QTableWidgetItem(text))
        while self.sessions_layout.count():
            item=self.sessions_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        sessions=sorted(snapshot.sessions,key=lambda s:s.id not in active_ids)[:12]
        for session in sessions:
            button=QPushButton();button.setFixedHeight(26)
            button.setText(button.fontMetrics().elidedText(session.title+' ↗',Qt.TextElideMode.ElideRight,270));button.setToolTip(session.title)
            button.clicked.connect(lambda checked=False,sid=session.id:self.conversation_requested.emit(sid));self.sessions_layout.addWidget(button)
            label=QLabel(f'会话积分 {session.credit:.3f}'+(f' · 上下文 {session.context_used:,}/{session.context_size:,}' if session.context_size else ''))
            label.setWordWrap(True);self.sessions_layout.addWidget(label)
        if not sessions:self.sessions_layout.addWidget(QLabel('尚无可读取的本机会话'))
        self.observe_activity()

    def paintEvent(self,event):
        painter=QPainter(self);painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(),Qt.GlobalColor.transparent);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#d8e8f3'),1));painter.setBrush(QColor('#fbfeff'))
        painter.drawRoundedRect(QRectF(.5,.5,self.width()-1,self.height()-1),18,18);painter.end()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.pressed=event.globalPosition().toPoint();self.drag_origin=self.pos()

    def mouseMoveEvent(self,event):
        if self.pressed is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta=event.globalPosition().toPoint()-self.pressed
            if delta.manhattanLength()>6:self.move(self.drag_origin+delta);self.moved.emit(self.x(),self.y())

    def mouseReleaseEvent(self,event):
        if self.pressed is not None:
            delta=event.globalPosition().toPoint()-self.pressed
            if delta.manhattanLength()<=6 and self.compact:self.set_compact(False)
            self.pressed=None

    def resizeEvent(self,event):super().resizeEvent(event);self.resized.emit()
