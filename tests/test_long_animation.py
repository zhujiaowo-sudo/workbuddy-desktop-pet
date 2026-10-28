import json
import time
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from workbuddy_pet.materials import ALL_ACTIONS, LOOP_ACTIONS, MaterialError, validate_pack
from workbuddy_pet.ui.animation import AnimationPlayer
from workbuddy_pet.ui.frame_stream import FrameStream


def animation(path, count=20, size=512, duration=42):
    frames=[]
    for i in range(count):
        image=Image.new('RGBA',(size,size))
        ImageDraw.Draw(image).rectangle((size//3+i,size//3,size//3+i+20,size-10),fill=(20,200,120,255))
        frames.append(image)
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=duration,loop=0,disposal=0,blend=0)


def pack(root):
    (root/'actions').mkdir()
    animation(root/'sample.png')
    for action in ALL_ACTIONS:(root/'actions'/f'{action}.png').write_bytes((root/'sample.png').read_bytes())
    data=dict(schema=3,id='synthetic',name='Synthetic',author='Test',version='1.0',license='CC0',quality='light',anchor=[0,0,512,512],
              actions={a:dict(file=f'actions/{a}.png',loop=a in LOOP_ACTIONS) for a in ALL_ACTIONS})
    (root/'manifest.json').write_text(json.dumps(data))
    return data


def wait_until(qt_app, predicate, timeout=3):
    end=time.perf_counter()+timeout
    while time.perf_counter()<end:
        qt_app.processEvents()
        if predicate():return
        time.sleep(.002)
    assert predicate()


def test_long_format_and_old_limit_are_separate(tmp_path):
    data=pack(tmp_path)
    assert validate_pack(tmp_path).schema==3
    data['schema']=2
    (tmp_path/'manifest.json').write_text(json.dumps(data))
    with pytest.raises(MaterialError):validate_pack(tmp_path)


@pytest.mark.parametrize('change',['anchor','size','duration','frames','length'])
def test_long_format_rejects_invalid_input(tmp_path,change):
    data=pack(tmp_path)
    if change=='anchor':data.pop('anchor')
    else:
        animation(tmp_path/'actions/idle.png',count=241 if change=='frames' else 80 if change=='length' else 20,
                  size=256 if change=='size' else 512,duration=10 if change=='duration' else 200 if change=='length' else 42)
    (tmp_path/'manifest.json').write_text(json.dumps(data))
    with pytest.raises(MaterialError):validate_pack(tmp_path)


def test_worker_is_bounded_and_cancel_does_not_wait(tmp_path):
    path=tmp_path/'loop.png';animation(path)
    stream=FrameStream(path,True)
    end=time.perf_counter()+3
    while stream.frames.qsize()<6 and time.perf_counter()<end:time.sleep(.01)
    assert stream.frames.qsize()==6
    started=time.perf_counter();stream.close()
    assert time.perf_counter()-started<.1
    assert stream.done.wait(2)


def test_stream_three_loops_switch_hide_and_resume(tmp_path,qt_app):
    data=pack(tmp_path);character=validate_pack(tmp_path)
    player=AnimationPlayer();seen=[]
    player.changed.connect(lambda:seen.append(player.pixmap.toImage().pixelColor(171,171).alpha()) if player.pixmap else None)
    player.load(character,'idle')
    wait_until(qt_app,lambda:len(seen)>=60,timeout=5)
    assert len(player.frames)==1 and player.stream.frames.qsize()<=6
    old=player.stream;player.load(character,'done')
    assert old.stop.is_set() and player.stream is not old
    wait_until(qt_app,lambda:bool(player.frames))
    player.set_visible(False)
    assert not player.timer.isActive() and player.stream is None
    player.set_visible(True)
    wait_until(qt_app,lambda:player.deadline>0)
    player.clear();assert not player.frames and player.stream is None


def test_late_callbacks_follow_accumulated_source_clock(qt_app,monkeypatch):
    clock=[0.0];monkeypatch.setattr('workbuddy_pet.ui.animation.time.perf_counter',lambda:clock[0])
    image=QPixmap(8,8);image.fill(Qt.GlobalColor.red)
    player=AnimationPlayer();player.frames=tuple((image,d) for d in (41,42,42));player.deadline=.041
    clock[0]=.300;player._timeout()
    assert player.index==1 and player.deadline==pytest.approx(.333)
    clock[0]=.999;player._timeout()
    assert player.index==2 and player.deadline==pytest.approx(1.0)
    player.loop=False;clock[0]=2;player._timeout()
    assert player.index==2 and not player.timer.isActive()
    player.clear()


def test_long_click_waits_for_authored_end_and_keeps_urgent_interrupts(tmp_path,qt_app):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.materials import MaterialLibrary
    from workbuddy_pet.settings import Settings,save_settings
    from workbuddy_pet.events import Event
    source=tmp_path/'source';source.mkdir();pack(source)
    character=MaterialLibrary(tmp_path/'characters').import_pack(source)
    save_settings(tmp_path,Settings(character=character.key,notifications=False))
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    controller.demo_timer.stop();controller.timer.stop();base=controller.visual_action;controller.interact()
    assert controller.interaction_deadline-time.monotonic()>12
    wait_until(qt_app,lambda:controller.active_interaction is None)
    assert controller.visual_action==base
    controller.last_pet_click=-1;controller.interact()
    now=time.time();controller.consume([Event('start',now,'s','UserPromptSubmit'),Event('wait',now+.01,'s','PermissionRequest')])
    assert controller.active_interaction is None
    controller.shutdown()


def test_segment_worker_enters_once_loops_forward_and_exits_tail(tmp_path,monkeypatch):
    from workbuddy_pet.materials import Frame
    monkeypatch.setattr('workbuddy_pet.ui.frame_stream.iter_animation',lambda *a,**k:iter(Frame((1,1),bytes((i,0,0,255)),42) for i in range(8)))
    stream=FrameStream(tmp_path/'unused',True,(2,6));seen=[]
    for _ in range(14):seen.append(stream.frames.get(timeout=2).rgba[0])
    assert seen[:6]==list(range(6))
    assert all(x in (2,3,4,5) for x in seen[6:])
    stream.exit.set()
    while not stream.done.is_set() or not stream.frames.empty():
        try:seen.append(stream.frames.get(timeout=.1).rgba[0])
        except __import__('queue').Empty:pass
    assert stream.tail_started.is_set() and seen[-2:]==[6,7]
    assert 0 not in seen[6:]


def test_deferred_switch_finishes_tail_and_latest_request_wins(tmp_path,qt_app):
    data=pack(tmp_path);data['actions']['idle']['loop_range']=[4,12]
    (tmp_path/'manifest.json').write_text(json.dumps(data));character=validate_pack(tmp_path)
    player=AnimationPlayer();player.load(character,'idle')
    wait_until(qt_app,lambda:bool(player.frames))
    player.load(character,'thinking',defer=True);old=player.stream
    player.load(character,'working',defer=True)
    assert player.identity[1]=='actions/idle.png'
    wait_until(qt_app,lambda:player.identity[1]=='actions/working.png')
    assert old.tail_started.is_set() and old.done.is_set()
    player.clear()


def test_loop_range_must_leave_real_entry_and_exit(tmp_path):
    data=pack(tmp_path);data['actions']['idle']['loop_range']=[0,20]
    (tmp_path/'manifest.json').write_text(json.dumps(data))
    with pytest.raises(MaterialError):validate_pack(tmp_path)
