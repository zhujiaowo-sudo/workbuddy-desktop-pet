import json,time
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from workbuddy_pet.settings import Settings,save_settings
from workbuddy_pet.materials import MaterialLibrary,STATES
from workbuddy_pet.events import Event
from workbuddy_pet.state import derive_display


def test_click_response_restores_real_task_animation_without_changing_events(tmp_path,qt_app):
    from workbuddy_pet.app import Controller
    source=tmp_path/'source';source.mkdir()
    for state in STATES:Image.new('RGBA',(16,16),'blue').save(source/(state+'.png'))
    (source/'manifest.json').write_text(json.dumps({'schema':1,'id':'s','name':'s','author':'s','version':'1',
        'license':'CC0-1.0','quality':'light','actions':{s:{'file':s+'.png'} for s in STATES}}))
    pack=MaterialLibrary(tmp_path/'characters').import_pack(source)
    save_settings(tmp_path,Settings(character=pack.key,notifications=False,compact=True))
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    assert controller.bubble.materials.choices.currentData()==pack.key
    controller.demo_timer.stop();controller.timer.stop()
    now=time.time();controller.consume([Event('a',now,'s','UserPromptSubmit'),Event('b',now+.01,'s','PreToolUse')])
    before=dict(controller.sessions)
    QTest.mouseClick(controller.pet,Qt.MouseButton.LeftButton,pos=QPoint(80,90))
    assert controller.bubble.compact and controller.active_interaction is not None
    assert controller.sessions==before and controller.player.identity[1]=='done.png'
    assert '摸摸' in controller.bubble.capsule.text()
    controller.refresh();assert '摸摸' in controller.bubble.capsule.text()
    controller.consume([Event('c',now+.02,'s','PostToolUse')])
    assert derive_display(controller.sessions,now+.03).state=='thinking'
    assert controller.player.identity[1]=='done.png'
    controller.finish_interaction()
    assert controller.player.identity[1]=='thinking.png' and not controller.bubble.interaction_text
    controller.interact();assert controller.interaction_index==1
    controller.last_pet_click-=1;controller.interact();assert controller.interaction_index==2
    assert controller.player.identity[1]=='waiting.png'
    controller.open_page('data');assert controller.active_interaction is None and controller.bubble.mode=='expanded'
    controller.shutdown()


def test_disabled_checkin_never_reads_or_claims(tmp_path,qt_app,monkeypatch):
    import workbuddy_pet.app as application
    calls=[]
    monkeypatch.setattr(application,'read_checkin',lambda home:calls.append('read'))
    monkeypatch.setattr(application,'perform_checkin',lambda *args:calls.append('claim'))
    controller=application.Controller(qt_app,tmp_path,False,workbuddy_home=tmp_path/'absent')
    controller.load_checkin();controller.checkin_clicked();qt_app.processEvents()
    assert not calls and controller.bubble.mode=='expanded'
    assert controller.bubble.signin_button.property('checkinState')=='disabled'
    controller.shutdown()


def test_idle_animation_yields_to_tasks_and_preserves_real_card(tmp_path,qt_app):
    from workbuddy_pet.app import Controller
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    controller.demo_timer.stop();controller.timer.stop();controller.sessions={}
    controller.bubble.set_compact(True);controller.refresh()
    text=controller.bubble.capsule.text()
    controller.idle_director.next_due=0;controller.refresh()
    assert controller.idle_director.active and controller.visual_action.startswith('leisure_')
    assert controller.bubble.capsule.text()==text and not controller.active_interaction
    now=time.time()
    controller.consume([Event('task',now,'task','UserPromptSubmit'),Event('tool',now+.01,'task','PreToolUse')])
    assert controller.visual_action=='working' and controller.idle_director.active is None
    # The default now supplies authored working frames, so synthetic props stay off.
    assert controller.pet.effect_action=='' and not controller.pet.timer.isActive()
    assert controller.active_pack.key=='builtin' and controller.player.stream_path is not None
    controller.interact();assert controller.active_interaction
    controller.consume([Event('confirm',now+.02,'task','PermissionRequest')])
    assert controller.visual_action=='review' and controller.active_interaction is None
    controller.sessions={};controller.refresh();controller.idle_director.next_due=0;controller.refresh()
    assert controller.idle_director.active
    controller.pet.press_position=QPoint(1,1);controller.refresh()
    assert controller.idle_director.active is None
    controller.pet.press_position=None;controller.idle_director.next_due=0
    controller.toggle_visible();controller.refresh()
    assert controller.idle_director.active is None and not controller.pet.timer.isActive()
    controller.shutdown()


def test_checkin_refresh_and_day_rollover_only_read_click_claims_once(tmp_path,qt_app,monkeypatch):
    import workbuddy_pet.app as application
    from workbuddy_pet.checkin import CheckinSnapshot
    calls=[]
    def read(home):calls.append('read');return CheckinSnapshot('available')
    def claim(home,cancel):calls.append('claim');return CheckinSnapshot('claimed',awarded=987654.321)
    monkeypatch.setattr(application,'read_checkin',read);monkeypatch.setattr(application,'perform_checkin',claim)
    save_settings(tmp_path,Settings(checkin_enabled=True,notifications=False))
    controller=application.Controller(qt_app,tmp_path,False,workbuddy_home=tmp_path/'absent')
    QTest.qWait(80);assert calls==['read']
    controller.checkin_day='previous-day';controller.refresh();QTest.qWait(80)
    assert calls==['read','read']
    controller.bubble.set_compact(True);qt_app.processEvents()
    QTest.mouseClick(controller.bubble.signin_button,Qt.MouseButton.LeftButton)
    controller.checkin_clicked()
    for _ in range(50):
        QTest.qWait(20)
        if controller.checkin_snapshot.checked:break
    assert calls.count('claim')==1 and controller.checkin_snapshot.checked
    assert '987654.321' not in (tmp_path/'runtime.json').read_text()
    assert '987654.321' not in (tmp_path/'settings.json').read_text()
    controller.shutdown()
