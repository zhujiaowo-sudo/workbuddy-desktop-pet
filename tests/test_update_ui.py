import time
from pathlib import Path

from PySide6.QtTest import QTest

from workbuddy_pet.app import Controller
from workbuddy_pet.update import Release,RELEASES


def settle(app,condition):
    deadline=time.monotonic()+3
    while not condition() and time.monotonic()<deadline:
        time.sleep(.01);app.processEvents()
    assert condition()


def test_update_requires_click_shows_plain_notes_and_preserves_app_on_helper_failure(tmp_path,qt_app,monkeypatch):
    import workbuddy_pet.ui.updates as ui
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent');controller.demo_timer.stop()
    manager=controller.updates;calls=[]
    release=Release('9.9.9','版本更新 <script>不执行</script>',RELEASES+'/download/v9.9.9/test.zip','test.zip',16,'0'*64)
    monkeypatch.setattr(ui,'check_latest',lambda _:release)
    monkeypatch.setattr(ui.sys,'frozen',True,raising=False)
    monkeypatch.setattr(ui,'download_release',lambda *args:calls.append('download') or tmp_path/'package.zip')
    monkeypatch.setattr(ui,'stage_package',lambda *args:tmp_path/'payload')
    monkeypatch.setattr(ui,'prepare_install',lambda *args,**kwargs:tmp_path/'plan.json')
    class FailedHelper:
        def poll(self):return 1
    monkeypatch.setattr(ui,'launch_install',lambda _:FailedHelper())
    try:
        manager.check(manual=True);settle(qt_app,lambda:manager.job is None)
        assert manager.phase=='available' and not calls and '9.9.9' in manager.dialog.heading.text()
        assert '<script>' in manager.dialog.notes.toPlainText()
        manager.dialog.restart.setChecked(False);manager.action()
        settle(qt_app,lambda:manager.job is None)
        assert calls==['download'] and manager.phase=='ready' and not controller.shutting_down
        manager.action()
        assert manager.phase=='error' and not controller.shutting_down and controller.bubble.isVisible()
    finally:controller.shutdown()


def test_later_pauses_ready_install_and_manual_action_still_works(tmp_path,qt_app,monkeypatch):
    import workbuddy_pet.ui.updates as ui
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    controller.demo_timer.stop();controller.timer.stop()
    manager=controller.updates;calls=[]
    class FailedHelper:
        def poll(self):return 1
    monkeypatch.setattr(ui,'launch_install',lambda _:calls.append('install') or FailedHelper())
    try:
        manager.phase='ready';manager.plan=tmp_path/'plan.json'
        manager.release=Release('9.9.9','','','',1,'0'*64)
        manager.dialog.show();manager.dialog.close()
        manager.auto_install()  # An already queued callback must also respect Later.
        assert calls==[] and manager.phase=='ready' and manager.plan is not None
        manager.action()
        assert calls==['install']
    finally:controller.shutdown()


def test_later_cancels_install_waiting_for_editing(tmp_path,qt_app,monkeypatch):
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    controller.demo_timer.stop();controller.timer.stop()
    manager=controller.updates;calls=[]
    monkeypatch.setattr(manager,'action',lambda:calls.append('install'))
    try:
        manager.phase='ready';controller.pet.press_position=object()
        manager.auto_install()
        assert not calls
        manager.cancel();controller.pet.press_position=None
        QTest.qWait(1100)
        assert not calls
    finally:controller.shutdown()
