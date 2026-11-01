import hashlib,time
from pathlib import Path
from PySide6.QtCore import Qt,QPoint,QEventLoop,QTimer
from PySide6.QtTest import QTest
from workbuddy_pet.builtin import builtin_pack
from workbuddy_pet.settings import Settings,save_settings


def wait(ms):
    loop=QEventLoop();QTimer.singleShot(ms,loop.quit);loop.exec()


def test_authored_pair_and_release_mapping():
    pack=builtin_pack('builtin-dragon-maid')
    assert {'drag_lift','drag_drop'}<=pack.actions.keys()
    assert not pack.action('drag_lift').loop and not pack.action('drag_drop').loop
    mapping=pack.action('drag_lift').release_frames
    assert len(mapping)==30 and mapping[0]==14 and mapping[-1]==0
    from workbuddy_pet.materials import OPTIONAL_IDLE_ACTIONS
    assert 'drag_lift' not in OPTIONAL_IDLE_ACTIONS


def test_stream_can_start_from_a_source_frame(qt_app):
    from workbuddy_pet.ui.animation import AnimationPlayer
    pack=builtin_pack('builtin-dragon-maid');p=AnimationPlayer()
    try:
        p.load(pack,'drag_drop',start_frame=25)
        deadline=time.monotonic()+2
        while not p.frames and time.monotonic()<deadline:wait(10)
        assert p.frame_number==25 and p.stream.frames.maxsize==6
        deadline=time.monotonic()+3
        while not p.ended and time.monotonic()<deadline:wait(20)
        assert p.ended and p.frame_number==29
        before=p.pixmap.cacheKey();wait(100);assert p.pixmap.cacheKey()==before
    finally:p.clear()


def test_drag_release_regrab_and_short_click(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(character='builtin-dragon-maid',notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop();c.sessions={};wait(120)
    try:
        c.refresh();QTest.mousePress(c.pet,Qt.MouseButton.LeftButton,pos=QPoint(50,50))
        assert c.drag_action is None
        QTest.mouseMove(c.pet,QPoint(70,55));wait(300)
        assert c.drag_action=='drag_lift' and c.pet.lift==0
        frame=c.player.frame_number
        QTest.mouseRelease(c.pet,Qt.MouseButton.LeftButton,pos=QPoint(70,55))
        assert c.drag_action=='drag_drop' and c.player.start_frame==c.active_pack.action('drag_lift').release_frames[frame]
        wait(100);c.start_drag();assert c.drag_action=='drag_lift' and c.player.start_frame>0
        c.end_drag();wait(2400);assert c.drag_action is None
        c.last_pet_click=-1;QTest.mouseClick(c.pet,Qt.MouseButton.LeftButton,pos=QPoint(50,50))
        assert c.active_interaction and c.active_interaction.action.startswith('click_')
    finally:c.shutdown()


def test_drag_cancel_and_other_character_fallback(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(character='builtin-dragon-maid',notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop();c.sessions={}
    try:
        c.start_drag();assert c.drag_action=='drag_lift'
        c.collapse_avatar();assert c.drag_action is None
        c.restore_avatar();c.start_drag();c.activate_character('builtin-blue-fish')
        assert c.drag_action is None and not c.pet.authored_drag
        c.start_drag();assert c.drag_action is None
    finally:c.shutdown()


def test_drag_pair_rejects_missing_action_and_invalid_mapping(monkeypatch):
    import json,copy,pytest
    from workbuddy_pet import materials
    pack=builtin_pack('builtin-dragon-maid');original=json.loads((pack.root/'manifest.json').read_text(encoding='utf-8'))
    for broken in ('pair','mapping'):
        data=copy.deepcopy(original)
        if broken=='pair':del data['actions']['drag_drop']
        else:data['actions']['drag_lift']['release_frames']=[-1]*30
        with monkeypatch.context() as patch:
            patch.setattr(materials.json,'loads',lambda _:data)
            with pytest.raises(materials.MaterialError,match='成对|release_frames'):materials.validate_pack(pack.root,decode=False)


def test_important_task_interrupts_authored_drag(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.events import Event
    save_settings(tmp_path,Settings(character='builtin-dragon-maid',notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop();c.sessions={}
    try:
        c.start_drag();c.consume([Event('review-test',time.time(),'synthetic','PermissionRequest')])
        assert c.drag_action is None and c.visual_action=='review'
        c.end_drag();assert c.drag_action is None and c.visual_action=='review'
    finally:c.shutdown()


def test_menu_cancellation_immediately_leaves_drag_stream(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(character='builtin-dragon-maid',notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop();c.sessions={}
    try:
        c.start_drag();wait(80);assert not c.player.ended
        c.pet.drag_cancelled.emit();c.pet.manual_activity.emit()
        assert c.drag_action is None and c.player.identity[1]=='actions/idle.gif' and c.player.pending is None
    finally:c.shutdown()
