"""Shared module navigation for both the character and detached capsule."""
from PySide6.QtWidgets import QMenu


def module_menu(parent,page_requested,quit_requested,avatar_requested=None):
    menu=QMenu(parent)
    menu.setStyleSheet('QMenu{background:#fbfeff;border:1px solid #d9e7f1;padding:5px;} QMenu::item{padding:7px 18px;color:#2b506d;} QMenu::item:selected{background:#e7f2fb;border-radius:5px;}')
    avatar=menu.addAction('收成胶囊');avatar.setData('capsule')
    avatar.triggered.connect(avatar_requested.emit if avatar_requested is not None else lambda:page_requested.emit('capsule'))
    menu.addSeparator()
    for label,key in (('数据小卡','summary'),('任务详情','details'),('积分与模型','data'),('在 WorkBuddy 中聊天 ↗','chat'),('角色与素材','materials'),('设置与连接','settings')):
        action=menu.addAction(label);action.setData(key)
        action.triggered.connect(lambda checked=False,page=key:page_requested.emit(page))
    materials=next(a for a in menu.actions() if a.data()=='materials')
    submenu=QMenu('角色与素材',menu);materials.setMenu(submenu)
    menu.character_menu=submenu
    modes=menu.addMenu('显示模式')
    menu.mode_actions={}
    for label,key in (('极简模式','minimal'),('胶囊模式','standard')):
        action=modes.addAction(label);action.setCheckable(True)
        action.triggered.connect(lambda checked=False,k=key:page_requested.emit('mode:'+k))
        menu.mode_actions[key]=action
    menu.addSeparator();menu.addAction('退出桌宠',quit_requested.emit)
    return menu,avatar
