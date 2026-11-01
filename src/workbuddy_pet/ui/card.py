from .theme import STYLE,palette_for,style_for,tint_css
"""Compact opaque card with separate navigation and content surfaces."""
import math
import re
import time
from PySide6.QtCore import Qt,QEvent,Signal,QRectF,QSize,QPropertyAnimation,QEasingCurve
from PySide6.QtGui import QColor,QPainter,QPen,QFontMetrics
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabBar,
    QStackedWidget,QScrollArea,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,
    QAbstractItemView,QLineEdit,QTextEdit,QApplication,QFrame,QGraphicsDropShadowEffect)

from ..state import DisplayState
from .pet import LABELS,SUBTITLES,mascot_icon
from .icons import action_button,action_icon

PAGE_KEYS=('details','data','materials','settings')
MODE_SIZES={'capsule':(342,36),'summary':(380,540),'expanded':(380,540),'window':(304,238)}


class PageTabs(QWidget):
    """Navigation is outside the scrolled page and has no native baseline."""
    currentChanged=Signal(int)

    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(6)
        self.bar=QTabBar();self.bar.setDrawBase(False);self.bar.setExpanding(True)
        self.bar.setUsesScrollButtons(False);self.bar.setFixedHeight(38)
        self.bar.setStyleSheet('QTabBar{background:#f3f3f3;border-radius:7px;} '
            'QTabBar::tab{height:26px;margin:3px;padding:0 10px;color:#737373;border:1px solid transparent;border-radius:5px;} '
            'QTabBar::tab:selected{background:white;color:#202020;border-color:#e7e7e7;} '
            'QTabBar::tab:hover:!selected{color:#333333;background:#ebebeb;}')
        self.pages=QStackedWidget();self.pages.setObjectName('cardPages');self.pages.setMinimumSize(0,0)
        self.pages.setStyleSheet('QStackedWidget#cardPages{background:#ffffff;border:0;}')
        layout.addWidget(self.bar);layout.addWidget(self.pages,1)
        self.bar.currentChanged.connect(self.pages.setCurrentIndex);self.bar.currentChanged.connect(self.currentChanged)

    def addTab(self,widget,name):
        widget.setObjectName('cardPage')
        widget.setStyleSheet(widget.styleSheet()+'\nQWidget#cardPage{background:#ffffff;}')
        scroll=QScrollArea();scroll.setObjectName('cardScroll');scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet('QScrollArea#cardScroll{background:#ffffff;border:0;}')
        scroll.viewport().setAutoFillBackground(True)
        palette=scroll.viewport().palette();palette.setColor(palette.ColorRole.Window,QColor('#ffffff'));scroll.viewport().setPalette(palette)
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
    refresh_requested=Signal()
    checkin_requested=Signal()
    chat_requested=Signal()
    quick_requested=Signal()
    page_requested=Signal(str)
    avatar_requested=Signal()
    quit_requested=Signal()

    def __init__(self,demo=False):
        super().__init__(None,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle('WorkBuddy 小搭子 · 卡片');self.setWindowIcon(mascot_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(STYLE)
        self.pointer_open=False
        self.panel_fade=QPropertyAnimation(self,b'windowOpacity',self)
        self.panel_fade.setDuration(160);self.panel_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.window_mode=False;self.theme_key='gray';self.capsule_transparent=False
        self.minimal=False;self.mode='summary';self.compact=False;self.demo=demo;self.display=DisplayState()
        self.last_interaction=time.monotonic();self.drag_origin=None;self.pressed=None;self.child_drag=None
        self.local_sessions={};self.current_session=None;self.balance=None
        self.interaction_text='';self.interaction_until=0
        self.quick_action='checkin';self.last_checkin=None
        from .menu import module_menu
        self.context_menu,self.show_avatar_action=module_menu(self,self.page_requested,self.quit_requested,self.avatar_requested)
        self.root_layout=QVBoxLayout(self);self.root_layout.setContentsMargins(0,0,0,0);self.root_layout.setSpacing(0)
        self.compact_bar=QWidget();compact=QHBoxLayout(self.compact_bar);compact.setContentsMargins(0,0,0,0);compact.setSpacing(6)
        self.signin_button=QPushButton();self.signin_button.setFixedSize(36,36);self.signin_button.setIconSize(QSize(20,20))
        self.signin_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.signin_button.setAccessibleName('WorkBuddy 每日签到')
        self.signin_button.clicked.connect(self.quick_requested)
        self.signin_button.setIcon(action_icon('checkin'))
        self.signin_button.setStyleSheet('background:#ffffff;border:1px solid #f5f5f5;border-radius:18px;padding:7px;')
        self.signin_button.setToolTip('每日签到：等待状态，点击设置授权')
        self.capsule=QPushButton();self.capsule.setFixedSize(200,36);self.capsule.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.capsule.setAccessibleName('打开 WorkBuddy 数据看板')
        self.capsule.setStyleSheet('background:white;border:1px solid rgba(0,0,0,24);border-radius:18px;color:#202020;font-size:12px;font-weight:600;')
        self.capsule.clicked.connect(self.open_from_capsule)
        self.balance_badge=QPushButton('积分待同步');self.balance_badge.setFixedSize(94,36);self.balance_badge.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.balance_badge.setStyleSheet('background:#f5f5f5;border-radius:18px;color:#666666;font-size:11px;font-weight:700;padding:3px;')
        self.balance_badge.clicked.connect(self.balance_requested)
        compact.addWidget(self.signin_button);compact.addWidget(self.capsule);compact.addWidget(self.balance_badge);self.root_layout.addWidget(self.compact_bar)
        from .compact import CompactPanel
        self.window_panel=CompactPanel(self)
        self.window_panel.capsule_button.clicked.connect(lambda:self.page_requested.emit('presentation:capsule'))
        self.window_panel.expand_button.clicked.connect(lambda:self.open_page('details'))
        self.window_panel.session.clicked.connect(lambda:self.conversation_requested.emit(self.current_session) if self.current_session else self.open_requested.emit())
        self.root_layout.addWidget(self.window_panel)
        self.full=QWidget();full=QVBoxLayout(self.full);full.setContentsMargins(0,0,0,0);full.setSpacing(8)
        self.expanded=QWidget();expanded=QVBoxLayout(self.expanded);expanded.setContentsMargins(12,8,12,10);expanded.setSpacing(6)
        row=QHBoxLayout();self.page_title=QLabel('WorkBuddy');self.page_title.setStyleSheet('font-size:14px;font-weight:600;')
        self.back_button=action_button('close','收起看板');self.back_button.clicked.connect(lambda:self.set_compact(True,manual=True))
        self.settings_save=QPushButton('保存');self.settings_save.setProperty('primary',True);self.settings_save.setFixedSize(76,28);self.settings_save.hide()
        row.addWidget(self.page_title);row.addStretch();row.addWidget(self.settings_save);row.addWidget(self.back_button);expanded.addLayout(row)
        self.divider=QFrame();self.divider.setFixedHeight(1);self.divider.setStyleSheet('background:#f5f5f5;border:0;');expanded.addWidget(self.divider)
        self.tabs=PageTabs();expanded.addWidget(self.tabs,1);full.addWidget(self.expanded,1)
        self.tabs.currentChanged.connect(self.update_page_title)
        self.summary=QWidget();self.summary.setFixedHeight(188)
        summary=QVBoxLayout(self.summary);summary.setContentsMargins(12,8,12,8);summary.setSpacing(4)
        self.header=QWidget();header=QHBoxLayout(self.header);header.setContentsMargins(0,0,0,0);header.setSpacing(6)
        header.setSpacing(2)
        self.brand=QLabel('WorkBuddy'+(' · 演示' if demo else ''));self.brand.setStyleSheet('font-size:11px;color:#666666;font-weight:600;')
        self.refresh_button=action_button('refresh','刷新积分和本机统计');self.refresh_button.clicked.connect(self.refresh_requested)
        self.details_button=action_button('details','任务详情');self.details_button.clicked.connect(lambda:self.open_page('details'))
        self.data_button=action_button('data','展开数据看板');self.data_button.clicked.connect(self.open_data)
        self.chat_button=action_button('chat','在 WorkBuddy 中聊天 ↗');self.chat_button.clicked.connect(self.chat_requested)
        self.settings_button=action_button('settings','设置与连接');self.settings_button.clicked.connect(lambda:self.open_page('settings'))
        self.collapse_button=action_button('collapse','收起小卡，保留桌宠')
        self.collapse_button.clicked.connect(lambda:self.set_compact(True,manual=True))
        header.addWidget(self.brand);header.addStretch()
        for button in (self.refresh_button,self.details_button,self.data_button,self.chat_button,self.settings_button,self.collapse_button):header.addWidget(button)
        summary.addWidget(self.header)
        self.title=QLabel();self.title.setStyleSheet('font-size:11px;color:#666666;')
        self.subtitle=QLabel();self.subtitle.setTextFormat(Qt.TextFormat.PlainText);self.subtitle.setFixedHeight(18)
        self.subtitle.setStyleSheet('font-size:11px;color:#666666;')
        self.subtitle.hide()
        self.session_link=QPushButton();self.session_link.setFixedHeight(24);self.session_link.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.session_link.setStyleSheet('text-align:left;background:transparent;border:0;color:#202020;padding:0;font-size:12px;font-weight:600;')
        self.session_link.clicked.connect(lambda:self.conversation_requested.emit(self.current_session) if self.current_session else self.open_requested.emit())
        summary.addWidget(self.session_link);summary.addWidget(self.title);summary.addWidget(self.subtitle)
        metrics=QHBoxLayout();metrics.setSpacing(8)
        self.remaining_value,self.remaining_note=self.add_metric(metrics,'剩余积分','待同步','个人账户')
        self.today_value,self.today_note=self.add_metric(metrics,'今日消耗','待同步','本机记录')
        summary.addLayout(metrics,1)
        row=QHBoxLayout();row.setSpacing(6)
        self.open_button=QPushButton('打开 WorkBuddy ↗');self.open_button.clicked.connect(self.open_requested)
        self.materials_button=QPushButton('素材');self.materials_button.clicked.connect(lambda:self.open_page('materials'))
        self.ack=QPushButton('已读');self.ack.clicked.connect(self.acknowledged)
        for button in (self.open_button,self.materials_button,self.ack):button.setFixedHeight(22)
        row.addWidget(self.open_button);row.addStretch();row.addWidget(self.materials_button);row.addWidget(self.ack);summary.addLayout(row)
        self.root_layout.addWidget(self.full,1)
        self.details=QWidget();detail=QVBoxLayout(self.details);detail.setContentsMargins(4,6,4,4);detail.setSpacing(8)
        detail.addWidget(self.summary)
        self.header.hide();self.materials_button.hide()
        self.open_button.setProperty('primary',True);self.open_button.setFixedHeight(30)
        self.ack.setText('标记已读');self.ack.setFixedHeight(30)
        self.connection=QLabel();self.connection.setWordWrap(True);detail.addWidget(self.connection)
        help_text=QLabel('任务操作与确认在 WorkBuddy 中完成。')
        help_text.setWordWrap(True);help_text.setStyleSheet('font-size:11px;color:#666666;');detail.addWidget(help_text)
        recent=QLabel('最近会话');recent.setStyleSheet('font-weight:600;padding-top:8px;');detail.addWidget(recent)
        self.session_list=QWidget();self.sessions_layout=QVBoxLayout(self.session_list);self.sessions_layout.setContentsMargins(0,0,0,0)
        self.sessions_layout.addWidget(QLabel('正在读取本机会话…'));detail.addWidget(self.session_list);detail.addStretch()
        self.tabs.addTab(self.details,'概览')
        self.stats=QWidget();stats=QVBoxLayout(self.stats);stats.setContentsMargins(4,6,4,4);stats.setSpacing(8)
        row=QHBoxLayout();self.range=QComboBox()
        for name,days in (('全部',None),('最近7天',7),('最近30天',30)):self.range.addItem(name,days)
        row.addWidget(self.range)
        self.data_refresh=refresh=QPushButton('刷新');refresh.clicked.connect(lambda:self.data_requested.emit(self.range.currentData()));row.addWidget(refresh)
        stats.addLayout(row);self.data_status=QLabel('');stats.addWidget(self.data_status)
        self.range.currentIndexChanged.connect(lambda:self.data_requested.emit(self.range.currentData()))
        self.total=QLabel('正在读取本机统计…');self.total.setStyleSheet('font-size:16px;font-weight:800;');stats.addWidget(self.total)
        self.scope=QLabel();self.scope.setWordWrap(True);stats.addWidget(self.scope)
        self.balance_label=QLabel();self.balance_label.setWordWrap(True);self.balance_label.setStyleSheet('font-weight:700;');stats.addWidget(self.balance_label)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['模型','请求','积分'])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1,54);self.table.setColumnWidth(2,88);self.table.setMinimumHeight(110);self.table.setMaximumHeight(180)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.verticalHeader().hide()
        for i in range(3):self.table.horizontalHeaderItem(i).setTextAlignment((Qt.AlignmentFlag.AlignRight if i else Qt.AlignmentFlag.AlignLeft)|Qt.AlignmentFlag.AlignVCenter)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True);self.table.setShowGrid(False)
        self.table.setStyleSheet('QTableWidget{background:white;border:1px solid #f5f5f5;gridline-color:#f5f5f5;} '
            'QHeaderView::section{background:#ffffff;padding:5px;border:0;color:#666666;}');stats.addWidget(self.table)
        self.missing=QLabel();self.missing.setWordWrap(True);self.missing.setStyleSheet('font-size:11px;color:#808080;');stats.addWidget(self.missing);stats.addStretch(1)
        self.tabs.addTab(self.stats,'用量')
        self.set_balance(None);self.set_display(DisplayState());self.set_compact(False);self.observe_activity();self.apply_appearance('gray',False)

    @staticmethod
    def add_metric(row,heading,value,note):
        frame=QWidget();frame.setObjectName('metric')
        frame.setStyleSheet('QWidget#metric{background:transparent;border:0;}')
        layout=QVBoxLayout(frame);layout.setContentsMargins(10,6,10,6);layout.setSpacing(0)
        caption=QLabel(heading);caption.setStyleSheet('font-size:11px;color:#666666;')
        number=QLabel(value);number.setStyleSheet('font-size:21px;font-weight:800;color:#202020;')
        number.setMinimumWidth(0)
        foot=QLabel(note);foot.setStyleSheet('font-size:11px;color:#808080;')
        layout.addWidget(caption);layout.addWidget(number);layout.addWidget(foot);row.addWidget(frame,1)
        return number,foot

    def update_page_title(self,index):
        self.page_title.setText('WorkBuddy · 演示' if self.demo else 'WorkBuddy')
        self.settings_save.setVisible(index==3)
        if index>0 and not self.compact:self.mode='expanded'
        if index==1 and hasattr(self,'range'):self.data_requested.emit(self.range.currentData())

    def add_page(self,widget,name):self.tabs.addTab(widget,name);self.observe_activity()

    def observe_activity(self):
        self.installEventFilter(self)
        for widget in self.findChildren(QWidget):widget.installEventFilter(self)

    def eventFilter(self,watched,event):
        if event.type()==QEvent.Type.KeyPress:self.pointer_open=False
        if watched is self.capsule and event.type()==QEvent.Type.MouseButtonRelease:
            self.pointer_open=event.button()==Qt.MouseButton.LeftButton

        if self.compact and event.type()==QEvent.Type.ContextMenu and (watched in (self,self.compact_bar,self.capsule,self.balance_badge,self.signin_button,self.window_panel) or self.window_panel.isAncestorOf(watched)):
            self.child_drag=None;self.pressed=None
            self.context_menu.popup(event.globalPos());event.accept();return True
        if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.KeyPress,QEvent.Type.Wheel):self.last_interaction=time.monotonic()
        if self.compact and watched in (self.capsule,self.balance_badge,self.signin_button):
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
                self.child_drag=(event.globalPosition().toPoint(),self.pos(),False)
            elif event.type()==QEvent.Type.MouseMove and self.child_drag and event.buttons() & Qt.MouseButton.LeftButton:
                origin,position,dragged=self.child_drag;delta=event.globalPosition().toPoint()-origin
                if dragged or delta.manhattanLength()>6:
                    self.child_drag=(origin,position,True);self.move(position+delta);self.moved.emit(self.x(),self.y());return True
            elif event.type()==QEvent.Type.MouseButtonRelease and self.child_drag:
                dragged=self.child_drag[2];self.child_drag=None
                if dragged:self.pointer_open=False;watched.setDown(False);return True
        return super().eventFilter(watched,event)

    def open_page(self,key):
        if key=='chat':self.chat_requested.emit();return
        if key not in PAGE_KEYS:return
        index=PAGE_KEYS.index(key);changed=index!=self.tabs.currentIndex()
        if index<self.tabs.count():self.tabs.setCurrentIndex(index)
        self.set_mode('expanded',manual=True)
        if key=='data' and not changed:self.data_requested.emit(self.range.currentData())

    def open_from_capsule(self):
        animate=self.pointer_open;self.pointer_open=False
        self.open_page('details')
        from ..windows import ui_animations_enabled
        if animate and ui_animations_enabled():
            self.panel_fade.stop();self.setWindowOpacity(.0)
            self.panel_fade.setStartValue(.0);self.panel_fade.setEndValue(1.0);self.panel_fade.start()

    def set_data_busy(self,busy):
        self.data_status.setText('正在更新…' if busy else '已更新 · '+time.strftime('%H:%M:%S'))
        self.data_refresh.setEnabled(not busy)
        self.table.setEnabled(not busy);self.total.setEnabled(not busy)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:
            self.set_compact(True,manual=True);event.accept();return
        super().keyPressEvent(event)

    def open_data(self):self.open_page('data')

    def open_summary(self,checked=False,*,manual=False):self.set_mode('summary',manual=manual)

    def set_compact(self,value,manual=False):self.set_mode('window' if self.window_mode else 'capsule' if value else 'summary',manual=manual)

    def set_mode(self,mode,manual=False):
        if mode not in MODE_SIZES:return
        self.panel_fade.stop();self.setWindowOpacity(1.0)
        self.mode=mode;self.compact=mode in ('capsule','window')
        self.signin_button.setVisible(not self.minimal);self.capsule.setVisible(not self.minimal)
        self.balance_badge.setFixedHeight(48 if self.minimal else 36)
        self.style_capsule();self.resize_balance_badge()
        self.full.setVisible(not self.compact);self.compact_bar.setVisible(mode=='capsule')
        self.window_panel.setVisible(mode=='window');self.expanded.setVisible(not self.compact)
        if mode=='summary':self.tabs.setCurrentIndex(0)
        if mode=='capsule':self.setFixedSize(self.capsule_width(),48 if self.minimal else 36)
        else:self.setFixedSize(*MODE_SIZES[mode])
        self.root_layout.activate();self.update_session_link();self.last_interaction=time.monotonic()
        if manual:self.compact_changed.emit(self.compact)
        self.resized.emit();self.update()

    def apply_appearance(self,key,transparent):
        self.theme_key=key if key in ('gray','blue','red') else 'gray'
        self.capsule_transparent=bool(transparent);self.setStyleSheet(style_for(self.theme_key))
        special=(self.capsule,self.signin_button,self.balance_badge,self.window_panel)
        for widget in self.findChildren(QWidget):
            if widget in special or self.window_panel.isAncestorOf(widget):continue
            css=getattr(widget,'_neutral_css',None)
            if css is None:css=widget.styleSheet();widget._neutral_css=css
            if css:widget.setStyleSheet(tint_css(css,self.theme_key))
        p=palette_for(self.theme_key)
        self.tabs.bar.setStyleSheet(tint_css(self.tabs.bar._neutral_css,self.theme_key).replace('color:#202020',f'color:{p.accent}'))
        self.page_title.setStyleSheet(f'font-size:14px;font-weight:600;color:{p.accent};')
        for frame in self.findChildren(QWidget,'metric'):
            frame.setStyleSheet(f'QWidget#metric{{background:{p.soft};border:0;border-radius:8px;}}')
        self.window_panel.apply_theme(self.theme_key);self.style_capsule();self.resize_balance_badge();self.update()

    def style_capsule(self):
        p=palette_for(self.theme_key);clear=self.capsule_transparent and not self.minimal
        # Alpha 1 retains native layered-window hit testing while looking transparent.
        bg='rgba(255,255,255,0.004)' if clear else p.background
        border='transparent' if clear else p.border
        for button,radius,size,weight in ((self.signin_button,18,12,600),(self.capsule,18,12,600),(self.balance_badge,24 if self.minimal else 18,13,800)):
            padding='7px' if button is self.signin_button else '0px'
            button.setStyleSheet(f'QPushButton{{background:{bg};border:1px solid {border};border-radius:{radius}px;color:{p.accent};font-size:{size}px;font-weight:{weight};padding:{padding};}} QPushButton:hover{{background:{p.soft};}} QPushButton:focus{{border-color:{p.accent};}}')
            effect=button.graphicsEffect()
            if clear and effect is None:
                effect=QGraphicsDropShadowEffect(button);effect.setBlurRadius(3);effect.setOffset(0,0);effect.setColor(QColor(255,255,255,230));button.setGraphicsEffect(effect)
            if effect:effect.setEnabled(clear)

    def fit_height(self,maximum):
        if self.compact:return
        minimum=320
        height=min(MODE_SIZES[self.mode][1],max(minimum,maximum))
        if self.height()!=height:self.setFixedHeight(height);self.root_layout.activate()

    def show_interaction(self,text,seconds=4):
        self.interaction_text=str(text)[:100];self.interaction_until=time.monotonic()+seconds
        self.last_interaction=time.monotonic();self.update_session_link()

    def clear_interaction(self):
        self.interaction_text='';self.interaction_until=0;self.update_session_link()

    def set_checkin(self,snapshot):
        self.last_checkin=snapshot
        if self.quick_action!='checkin':return
        self.signin_button.setEnabled(True)
        self.signin_button.setProperty('checkinState',snapshot.state)
        self.signin_button.setIcon(action_icon('checked' if snapshot.checked else 'checkin'))
        note=snapshot.message
        if snapshot.daily_credit is not None:note+=f'\n基础签到积分：{snapshot.daily_credit:g}'
        if snapshot.awarded is not None:note+=f'\n本次领取：{snapshot.awarded:g} 积分'
        self.signin_button.setToolTip(note)

    def set_checkin_busy(self,claiming=False):
        if self.quick_action!='checkin':return
        self.signin_button.setEnabled(False);self.signin_button.setIcon(action_icon('refresh'))
        self.signin_button.setToolTip('正在签到，请稍候…' if claiming else '正在查询签到状态…')

    def set_quick_action(self,action,url=''):
        self.quick_action=action
        self.signin_button.setEnabled(True)
        if action=='checkin':
            self.signin_button.setIcon(action_icon('checkin'))
            self.signin_button.setToolTip('每日签到：仅点击时领取')
            if self.last_checkin:self.set_checkin(self.last_checkin)
        else:
            labels={'website':'打开 WorkBuddy 官网','custom':'打开自定义网页','refresh':'刷新积分和统计'}
            self.signin_button.setIcon(action_icon('refresh' if action=='refresh' else 'website'))
            self.signin_button.setToolTip(labels.get(action,'快捷操作')+('\n'+url if action=='custom' else ''))
        self.signin_button.setAccessibleName(self.signin_button.toolTip())

    def capsule_width(self):return 48 if self.minimal else 36+200+self.balance_badge.width()+12

    def resize_balance_badge(self):
        if self.minimal:
            self.balance_badge.setText(str(math.floor(self.balance)) if self.balance is not None else '—')
        width=48 if self.minimal else max(42,self.balance_badge.fontMetrics().horizontalAdvance(self.balance_badge.text())+22)
        font=self.balance_badge.font();font.setPixelSize(13);font.setBold(True)
        while self.minimal and font.pixelSize()>7 and QFontMetrics(font).horizontalAdvance(self.balance_badge.text())>42:
            font.setPixelSize(font.pixelSize()-1)
        self.balance_badge.setFont(font)
        self.balance_badge.setStyleSheet(re.sub(r'font-size:\d+px',f'font-size:{font.pixelSize()}px',self.balance_badge.styleSheet()))
        self.balance_badge.setFixedWidth(width)
        if self.mode=='capsule':
            self.setFixedSize(self.capsule_width(),48 if self.minimal else 36);self.root_layout.activate();self.resized.emit()

    def maybe_collapse(self,settings,now=None):
        now=time.monotonic() if now is None else now;focus=QApplication.focusWidget()
        editing=isinstance(focus,(QLineEdit,QTextEdit)) and not focus.isReadOnly() and self.isAncestorOf(focus)
        busy=getattr(getattr(self,'materials',None),'job',None)
        if settings.auto_collapse and self.mode=='summary' and not self.compact and self.display.state=='idle' and not self.display.reminders and not editing and not busy and not self.underMouse() and now-self.last_interaction>=settings.collapse_seconds:self.set_compact(True)

    def set_display(self,display):
        self.display=display;title,subtitle=LABELS[display.state],SUBTITLES[display.state]
        if display.connection=='disconnected':title,subtitle='等待 WorkBuddy 连接','打开设置，完成首次连接'
        elif display.connection=='stale':subtitle='任务状态已过期，暂以待机显示；请打开 WorkBuddy 确认'
        self.title.setText(title);self.title.setToolTip(subtitle);self.ack.setVisible(bool(display.reminders))
        labels={'connected':'已连接','disconnected':'未连接','stale':'暂未收到新的任务状态'}
        self.connection.setText(labels.get(display.connection,display.connection)+f' · {display.session_count} 个任务');self.update_session_link()

    def update_session_link(self):
        selected=self.local_sessions.get(self.display.session_id)
        if not self.display.session_id and self.local_sessions:selected=next(iter(self.local_sessions.values()))
        self.current_session=self.display.session_id or (selected.id if selected else None)
        name=selected.title if selected else '当前会话' if self.current_session else ''
        self.session_link.setText(self.session_link.fontMetrics().elidedText(name+' ↗' if name else '尚无会话 · 打开 WorkBuddy ↗',Qt.TextElideMode.ElideRight,self.width()-28));self.session_link.setToolTip(name)
        short={'idle':'待命','thinking':'思考中','working':'执行中','waiting':'等回复','review':'待确认','done':'已完成','failed':'需查看'}[self.display.state]
        if self.display.connection=='disconnected':short='待连接'
        text=short+(' · '+name if name else '')
        interacting=bool(self.interaction_text) and time.monotonic()<self.interaction_until
        shown=self.interaction_text if interacting else text
        self.capsule.setText(self.capsule.fontMetrics().elidedText(shown,Qt.TextElideMode.ElideRight,186))
        self.capsule.setToolTip((shown+'\n当前任务：' if interacting else '')+text+'\n点击打开数据看板')
        self.window_panel.set_context(name,self.interaction_text if interacting else self.title.text(),self.display.reminders,self.title.toolTip())
        self.subtitle.setVisible(interacting)
        if interacting:self.subtitle.setText(self.subtitle.fontMetrics().elidedText(self.interaction_text,Qt.TextElideMode.ElideRight,self.width()-28))

    def set_balance(self,value,source_note='WorkBuddy 余额需要客户端授权接口；本机消耗记录不能推算剩余积分'):
        valid=type(value) in (int,float) and math.isfinite(value) and value>=0
        self.balance=value if valid else None
        text=f'{math.floor(value):,}' if valid else '待同步'
        self.balance_badge.setText(text);self.resize_balance_badge()
        self.balance_badge.setToolTip(('剩余可用积分：'+text+'\n' if valid else '')+source_note)
        self.balance_label.setText('剩余可用积分：'+text);self.balance_label.setToolTip(source_note)
        self.remaining_value.setText(text)
        self.remaining_value.setToolTip(self.balance_badge.toolTip())
        self.remaining_note.setToolTip(source_note)
        self.window_panel.set_balance(self.balance,self.balance_badge.toolTip())

    def set_snapshot(self,snapshot,active_ids=()):
        self.set_data_busy(False)
        self.window_panel.set_snapshot(snapshot)
        if not snapshot.available:self.data_status.setText('更新失败 · 可重新刷新')
        self.local_sessions={s.id:s for s in snapshot.sessions};self.update_session_link()
        self.total.setText(f'{snapshot.total_credit:,.3f} 积分 · {snapshot.request_count} 次请求' if snapshot.available else '统计暂不可用')
        self.scope.setText(snapshot.message)
        self.today_value.setText(f'{snapshot.today_credit:,.3f}' if snapshot.available else '待同步')
        self.today_note.setText(f'本机 · {snapshot.today_requests} 次请求' if snapshot.available else self.today_note.fontMetrics().elidedText(snapshot.message.split('，')[0],Qt.TextElideMode.ElideRight,130))
        self.today_note.setToolTip(snapshot.message)
        self.today_value.setToolTip(f'{snapshot.today_date} 本地零点至今\n仅本机记录，非完整账单；{snapshot.unknown_time} 次缺时间未计入今日')
        self.missing.setText(f'{snapshot.unknown_model} 次缺模型，{snapshot.unknown_time} 次缺时间。缺时间不进入日期筛选；上下文不累计为消耗。')
        self.missing.setVisible(bool(snapshot.unknown_model or snapshot.unknown_time))
        self.table.setRowCount(len(snapshot.models))
        for row,model in enumerate(snapshot.models):
            for col,text in enumerate((model.model,str(model.requests),f'{model.credit:.3f}')):
                item=QTableWidgetItem(text);item.setToolTip(text)
                item.setTextAlignment((Qt.AlignmentFlag.AlignRight if col else Qt.AlignmentFlag.AlignLeft)|Qt.AlignmentFlag.AlignVCenter)
                if col==2:
                    font=item.font();font.setBold(True);item.setFont(font)
                self.table.setItem(row,col,item)
        while self.sessions_layout.count():
            item=self.sessions_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        sessions=sorted(snapshot.sessions,key=lambda s:s.id not in active_ids)[:12]
        for session in sessions:
            button=QPushButton();button.setFixedHeight(30)
            button.setStyleSheet('text-align:left;background:transparent;border:0;border-bottom:1px solid #eeeeee;border-radius:0;padding:4px 0;')
            button.setText(button.fontMetrics().elidedText(session.title+' ↗',Qt.TextElideMode.ElideRight,270));button.setToolTip(session.title)
            button.clicked.connect(lambda checked=False,sid=session.id:self.conversation_requested.emit(sid));self.sessions_layout.addWidget(button)
            label=QLabel(f'会话积分 {session.credit:.3f}'+(f' · 上下文 {session.context_used:,}/{session.context_size:,}' if session.context_size else ''))
            label.setWordWrap(True);label.setStyleSheet('color:#737373;font-size:11px;');self.sessions_layout.addWidget(label)
        if not sessions:self.sessions_layout.addWidget(QLabel('尚无可读取的本机会话'))
        self.observe_activity()

    def paintEvent(self,event):
        painter=QPainter(self);painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(),Qt.GlobalColor.transparent);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors=palette_for(self.theme_key)
        painter.setPen(QPen(QColor(colors.border),1));painter.setBrush(QColor(colors.background))
        if self.mode!='capsule':
            for surface in (self.window_panel if self.mode=='window' else self.expanded,):
                if surface.isHidden():continue
                rect=QRectF(surface.geometry()).adjusted(.5,.5,-.5,-.5)
                painter.drawRoundedRect(rect,15 if self.mode=='window' else 10,15 if self.mode=='window' else 10)
        painter.end()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.pressed=event.globalPosition().toPoint();self.drag_origin=self.pos()

    def mouseMoveEvent(self,event):
        if self.pressed is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta=event.globalPosition().toPoint()-self.pressed
            if delta.manhattanLength()>6:self.move(self.drag_origin+delta);self.moved.emit(self.x(),self.y())

    def mouseReleaseEvent(self,event):
        if self.pressed is not None:
            delta=event.globalPosition().toPoint()-self.pressed
            if delta.manhattanLength()<=6 and self.mode=='capsule':self.open_page('details')
            self.pressed=None

    def resizeEvent(self,event):super().resizeEvent(event);self.resized.emit()

    def set_avatar_hidden(self,hidden,card_only=False):
        self.show_avatar_action.setVisible(True)
        self.show_avatar_action.setText('显示桌宠' if hidden else '收成胶囊')
        self.show_avatar_action.setToolTip('显示人物并退出仅卡片模式，不自动下载素材' if card_only else
                                         '显示人物，必要时整组上移' if hidden else '隐藏人物，仅保留胶囊')
