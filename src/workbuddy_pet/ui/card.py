import time
from PySide6.QtCore import Qt,QEvent,Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,QScrollArea,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QLineEdit,QTextEdit,QApplication

from ..state import DisplayState
from .pet import StatusBubble


class CardWindow(StatusBubble):
    data_requested=Signal(object)
    conversation_requested=Signal(str)
    moved=Signal(int,int)
    compact_changed=Signal(bool)
    resized=Signal()

    def __init__(self,demo=False):
        super().__init__(demo)
        self.setWindowTitle('WorkBuddy 小搭子 · 卡片')
        self.compact=False
        self.last_interaction=time.monotonic()
        self.display=DisplayState()
        self.drag_origin=None
        self.pressed=None
        self.base_widgets=self.findChildren(QWidget)
        self.local_sessions={}
        self.current_session=None
        self.capsule=QPushButton('● 小搭子 · 随时待命')
        self.capsule.setFixedHeight(44)
        self.capsule.setStyleSheet('font-size:13px;font-weight:600;background:#eaf4fc;color:#285b81;border-radius:20px;')
        self.capsule.clicked.connect(lambda:self.set_compact(False))
        self.layout().insertWidget(0,self.capsule)
        self.session_link=QPushButton('')
        self.session_link.setStyleSheet('text-align:left;color:#2c7eb7;background:#edf6fc;')
        self.session_link.clicked.connect(lambda:self.conversation_requested.emit(self.current_session) if self.current_session else None)
        self.layout().insertWidget(4,self.session_link)
        self.session_link.hide()
        self.tabs=QTabWidget();self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet('QTabWidget::pane{border:0;} QTabBar::tab{padding:9px 13px;color:#71869a;background:transparent;} QTabBar::tab:selected{color:#246b9e;background:#e7f2fb;border-radius:8px;} QTableWidget{background:white;border:1px solid #deebf4;border-radius:8px;gridline-color:#eef4f9;} QHeaderView::section{background:#f0f6fb;padding:6px;border:0;color:#56748d;}')
        self.layout().addWidget(self.tabs)
        self.details=QWidget();detail=QVBoxLayout(self.details)
        self.connection=QLabel();self.connection.setWordWrap(True);detail.addWidget(self.connection)
        self.session_list=QWidget();self.sessions_layout=QVBoxLayout(self.session_list);self.sessions_layout.setContentsMargins(0,0,0,0)
        self.sessions_layout.addWidget(QLabel('会话名称与使用详情将在本地数据读取完成后显示。'))
        help_text=QLabel('任务开始、工具执行和完成时，小搭子会跟随状态变化。需要确认的操作仍在 WorkBuddy 内处理。')
        help_text.setWordWrap(True);detail.addWidget(help_text)
        session_scroll=QScrollArea();session_scroll.setWidgetResizable(True);session_scroll.setFrameShape(QScrollArea.Shape.NoFrame);session_scroll.setWidget(self.session_list)
        session_scroll.setStyleSheet('QScrollArea,QScrollArea QWidget{background:transparent;}')
        detail.addWidget(session_scroll,1)
        self.tabs.addTab(self.details,'详情')
        self.stats=QWidget();stats=QVBoxLayout(self.stats)
        row=QHBoxLayout();self.range=QComboBox()
        for name,days in (('全部',None),('最近7天',7),('最近30天',30)):self.range.addItem(name,days)
        row.addWidget(self.range)
        refresh=QPushButton('刷新本地数据');refresh.clicked.connect(lambda:self.data_requested.emit(self.range.currentData()));row.addWidget(refresh);stats.addLayout(row)
        self.range.currentIndexChanged.connect(lambda:self.data_requested.emit(self.range.currentData()))
        self.total=QLabel('正在读取本机统计…');self.total.setStyleSheet('font-size:18px;font-weight:600;');stats.addWidget(self.total)
        self.scope=QLabel();self.scope.setWordWrap(True);stats.addWidget(self.scope)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['模型','请求数','积分'])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1,65);self.table.setColumnWidth(2,75)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().hide();stats.addWidget(self.table)
        self.missing=QLabel();self.missing.setWordWrap(True);stats.addWidget(self.missing)
        self.tabs.addTab(self.stats,'数据')
        footer=QHBoxLayout()
        self.collapse_button=QPushButton('收成胶囊');self.collapse_button.clicked.connect(lambda:self.set_compact(not self.compact,manual=True));footer.addWidget(self.collapse_button)
        self.data_button=QPushButton('积分与模型');self.data_button.clicked.connect(self.open_data);footer.addWidget(self.data_button)
        self.layout().addLayout(footer)
        self.installEventFilter(self)
        self.set_compact(False)

    def add_page(self,widget,name):
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame);scroll.setWidget(widget)
        scroll.setStyleSheet('QScrollArea,QScrollArea QWidget{background:transparent;} QLineEdit,QTextEdit,QSpinBox{background:white;}')
        self.tabs.addTab(scroll,name)
        self.observe_activity()

    def observe_activity(self):
        for widget in self.findChildren(QWidget):widget.installEventFilter(self)

    def eventFilter(self,watched,event):
        if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.KeyPress,QEvent.Type.Wheel):self.last_interaction=time.monotonic()
        return super().eventFilter(watched,event)

    def open_data(self):
        self.set_compact(False);self.tabs.setCurrentIndex(1);self.data_requested.emit(self.range.currentData())

    def set_compact(self,value,manual=False):
        self.compact=bool(value)
        for widget in self.base_widgets:widget.setVisible(not value)
        self.capsule.setVisible(value)
        self.session_link.setVisible(not value and self.current_session is not None)
        self.collapse_button.setVisible(not value);self.data_button.setVisible(not value)
        self.tabs.setVisible(not value);self.subtitle.setVisible(not value)
        self.ack.setVisible(not value and bool(self.display.reminders))
        self.collapse_button.setText('展开卡片' if value else '收成胶囊')
        self.setFixedWidth(270 if value else 430)
        self.setMinimumHeight(0);self.setMaximumHeight(16777215)
        self.tabs.setMinimumHeight(340)
        self.tabs.setMaximumHeight(450)
        self.adjustSize()
        if value:self.setFixedHeight(72)
        self.last_interaction=time.monotonic()
        if manual:self.compact_changed.emit(bool(value))

    def maybe_collapse(self,settings,now=None):
        now=time.monotonic() if now is None else now
        focus=QApplication.focusWidget()
        editing=isinstance(focus,(QLineEdit,QTextEdit)) and not focus.isReadOnly() and self.isAncestorOf(focus)
        busy=getattr(getattr(self,'chat',None),'job',None) or getattr(getattr(self,'materials',None),'job',None)
        if settings.auto_collapse and not self.compact and self.display.state=='idle' and not self.display.reminders and not editing and not busy and not self.underMouse() and now-self.last_interaction>=settings.collapse_seconds:
            self.set_compact(True)

    def set_display(self,display):
        self.display=display
        super().set_display(display)
        self.subtitle.setVisible(not getattr(self,'compact',False))
        self.ack.setVisible(not getattr(self,'compact',False) and bool(display.reminders))
        if hasattr(self,'connection'):
            labels={'connected':'已收到 WorkBuddy 事件','disconnected':'等待 WorkBuddy 连接','stale':'任务状态可能已过期'}
            self.connection.setText(labels.get(display.connection,display.connection)+f'  ·  {display.session_count} 个任务会话')
            self.update_session_link()

    def update_session_link(self):
        selected=self.local_sessions.get(self.display.session_id)
        if selected is None and self.local_sessions:selected=next(iter(self.local_sessions.values()))
        self.current_session=selected.id if selected else None
        name=selected.title if selected else ''
        self.session_link.setText(name+'  ↗' if selected else '')
        self.session_link.setVisible(not self.compact and selected is not None)
        self.capsule.setText('● '+self.title.text()[:13]+(' · '+name[:8] if name else ''))

    def set_snapshot(self,snapshot,active_ids=()):
        self.local_sessions={s.id:s for s in snapshot.sessions}
        self.update_session_link()
        self.total.setText(f'{snapshot.total_credit:,.3f} 积分  ·  {snapshot.request_count} 次请求' if snapshot.available else '统计暂不可用')
        self.scope.setText(snapshot.message)
        self.missing.setText(f'全部记录中：{snapshot.unknown_model} 次请求缺模型，{snapshot.unknown_time} 次缺时间。缺时间的记录不进入日期筛选。上下文占用不作为累计消耗。')
        self.table.setRowCount(len(snapshot.models))
        for row,model in enumerate(snapshot.models):
            for col,text in enumerate((model.model,str(model.requests),f'{model.credit:.3f}')):
                self.table.setItem(row,col,QTableWidgetItem(text))
        while self.sessions_layout.count():
            item=self.sessions_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        sessions=sorted(snapshot.sessions,key=lambda s:s.id not in active_ids)[:12]
        for session in sessions:
            button=QPushButton(session.title+'  ↗');button.setToolTip('打开此 WorkBuddy 对话')
            button.clicked.connect(lambda checked=False,sid=session.id:self.conversation_requested.emit(sid));self.sessions_layout.addWidget(button)
            context=f'  · 上下文 {session.context_used:,}/{session.context_size:,}' if session.context_size else ''
            self.sessions_layout.addWidget(QLabel(f'会话积分 {session.credit:.3f}'+context))
        if not sessions:self.sessions_layout.addWidget(QLabel('尚无可读取的本机会话'))
        self.observe_activity()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.pressed=event.globalPosition().toPoint();self.drag_origin=self.pos()

    def mouseMoveEvent(self,event):
        if self.pressed is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta=event.globalPosition().toPoint()-self.pressed
            if delta.manhattanLength()>6:self.move(self.drag_origin+delta);self.moved.emit(self.x(),self.y())

    def mouseReleaseEvent(self,event):
        if self.pressed is not None:
            delta=event.globalPosition().toPoint()-self.pressed
            if delta.manhattanLength()<=6 and self.compact:self.set_compact(False)
            self.pressed=None

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.resized.emit()
