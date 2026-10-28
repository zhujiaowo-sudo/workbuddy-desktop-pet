import time

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton,QTextEdit

from workbuddy_pet.events import Event
from workbuddy_pet.settings import Settings,save_settings


def controller_for_test(root,qt_app,monkeypatch):
    import workbuddy_pet.app as application
    calls=[]
    monkeypatch.setattr(application,'open_conversation',lambda identifier:calls.append(('conversation',identifier)))
    monkeypatch.setattr(application,'open_workbuddy',lambda path:calls.append(('app',path.name)) or True)
    save_settings(root,Settings(workbuddy_path=str(root/'WorkBuddy.exe'),notifications=False))
    controller=application.Controller(qt_app,root,True,root/'absent')
    controller.demo_timer.stop();controller.timer.stop();controller.sessions={}
    controller.bubble.set_mode('summary')
    return controller,calls


def test_chat_entries_jump_to_current_workbuddy_without_embedded_panel(tmp_path,qt_app,monkeypatch):
    controller,calls=controller_for_test(tmp_path,qt_app,monkeypatch)
    controller.consume([Event('start',time.time(),'synthetic-conversation','UserPromptSubmit')])
    assert controller.bubble.tabs.count()==4 and not hasattr(controller.bubble,'chat')
    assert all(editor.isReadOnly() for editor in controller.bubble.findChildren(QTextEdit))
    assert all(button.text()!='发送' for button in controller.bubble.findChildren(QPushButton))
    menu=next(action for action in controller.pet.context_menu.actions() if action.data()=='chat')
    entries=(lambda:QTest.mouseClick(controller.bubble.chat_button,Qt.MouseButton.LeftButton),
             menu.trigger,lambda:controller.open_page('chat'),lambda:controller.bubble.open_page('chat'))
    for entry in entries:
        before=(controller.bubble.mode,controller.bubble.tabs.currentIndex())
        calls.clear();entry()
        assert calls==[('conversation','synthetic-conversation'),('app','WorkBuddy.exe')]
        assert (controller.bubble.mode,controller.bubble.tabs.currentIndex())==before
    controller.shutdown()


def test_chat_without_current_session_opens_main_workbuddy(tmp_path,qt_app,monkeypatch):
    controller,calls=controller_for_test(tmp_path,qt_app,monkeypatch)
    controller.open_page('chat')
    assert calls==[('app','WorkBuddy.exe')] and controller.bubble.mode=='summary'
    controller.shutdown()


def test_chat_cli_dispatches_external_open_only(tmp_path,monkeypatch):
    from workbuddy_pet import app,cli
    calls=[]
    monkeypatch.setattr(app,'run_app',lambda *args,**kwargs:calls.append(kwargs) or 0)
    assert cli.main(['--root',str(tmp_path),'--chat'])==0
    assert calls[0]['open_chat'] is True
