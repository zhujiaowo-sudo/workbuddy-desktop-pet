"""One navigation model for the character and capsule."""
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu
from .theme import MENU,THEME_NAMES
from ..settings import DISPLAY_MODES


def module_menu(parent,page_requested,quit_requested,avatar_requested=None):
    menu=QMenu(parent);menu.setStyleSheet(MENU)
    for label,key in (('打开 WorkBuddy','open'),('数据看板','details')):
        action=menu.addAction(label);action.setData(key)
        action.triggered.connect(lambda checked=False,k=key:page_requested.emit(k))
    menu.addSeparator()
    menu.character_menu=menu.addMenu('角色')
    modes=menu.addMenu('显示');menu.mode_actions={};group=QActionGroup(menu);group.setExclusive(True)
    for label,key in DISPLAY_MODES:
        action=modes.addAction(label);action.setCheckable(True);group.addAction(action)
        action.triggered.connect(lambda checked=False,k=key:page_requested.emit('mode:'+k))
        menu.mode_actions[key]=action
    appearance=menu.addMenu('外观');menu.theme_actions={};themes=QActionGroup(menu);themes.setExclusive(True)
    for label,key in THEME_NAMES:
        action=appearance.addAction(label);action.setCheckable(True);themes.addAction(action)
        action.triggered.connect(lambda checked=False,k=key:page_requested.emit('theme:'+k));menu.theme_actions[key]=action
    appearance.addSeparator();menu.transparent_action=appearance.addAction('胶囊透明底');menu.transparent_action.setCheckable(True)
    menu.transparent_action.triggered.connect(lambda checked:page_requested.emit('transparent:'+str(int(checked))))
    settings=menu.addAction('设置');settings.setData('settings');settings.triggered.connect(lambda:page_requested.emit('settings'))
    menu.addSeparator();menu.addAction('退出桌宠',quit_requested.emit)
    # Retain the internal visibility action for legacy callers; navigation lives in Display.
    avatar=QAction('收成胶囊',menu);avatar.setData('capsule')
    avatar.triggered.connect(avatar_requested.emit if avatar_requested is not None else lambda:page_requested.emit('capsule'))
    return menu,avatar
