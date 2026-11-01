"""One navigation model for the character and capsule."""
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu
from .theme import MENU


def module_menu(parent,page_requested,quit_requested,avatar_requested=None):
    menu=QMenu(parent);menu.setStyleSheet(MENU)
    for label,key in (('打开 WorkBuddy','open'),('数据看板','details')):
        action=menu.addAction(label);action.setData(key)
        action.triggered.connect(lambda checked=False,k=key:page_requested.emit(k))
    menu.addSeparator()
    menu.character_menu=menu.addMenu('角色')
    modes=menu.addMenu('显示');menu.mode_actions={};group=QActionGroup(menu);group.setExclusive(True)
    for label,key in (('桌宠＋胶囊','standard'),('桌宠＋积分','minimal'),('仅胶囊','detached')):
        action=modes.addAction(label);action.setCheckable(True);group.addAction(action)
        action.triggered.connect(lambda checked=False,k=key:page_requested.emit('mode:'+k))
        menu.mode_actions[key]=action
    settings=menu.addAction('设置');settings.setData('settings');settings.triggered.connect(lambda:page_requested.emit('settings'))
    menu.addSeparator();menu.addAction('退出桌宠',quit_requested.emit)
    # Retain the internal visibility action for legacy callers; navigation lives in Display.
    avatar=QAction('收成胶囊',menu);avatar.setData('capsule')
    avatar.triggered.connect(avatar_requested.emit if avatar_requested is not None else lambda:page_requested.emit('capsule'))
    return menu,avatar
