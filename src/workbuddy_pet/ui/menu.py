"""Shared module navigation for both the character and detached capsule."""
from PySide6.QtWidgets import QMenu


def module_menu(parent,page_requested,quit_requested,avatar_requested=None):
    menu=QMenu(parent)
    menu.setStyleSheet('QMenu{background:#fbfeff;border:1px solid #d9e7f1;padding:5px;} QMenu::item{padding:7px 18px;color:#2b506d;} QMenu::item:selected{background:#e7f2fb;border-radius:5px;}')
    avatar=None
    if avatar_requested is not None:
        avatar=menu.addAction('显示桌宠',avatar_requested.emit);avatar.setData('show-avatar')
        menu.addSeparator()
    for label,key in (('数据小卡','summary'),('任务详情','details'),('积分与模型','data'),('在 WorkBuddy 中聊天 ↗','chat'),('角色与素材','materials'),('设置与连接','settings')):
        action=menu.addAction(label);action.setData(key)
        action.triggered.connect(lambda checked=False,page=key:page_requested.emit(page))
    menu.addSeparator()
    action=menu.addAction('收成胶囊');action.setData('capsule')
    action.triggered.connect(lambda:page_requested.emit('capsule'))
    menu.addSeparator();menu.addAction('退出桌宠',quit_requested.emit)
    return menu,avatar
