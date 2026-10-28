from dataclasses import replace
import random

import pytest
from PySide6.QtCore import QPoint,Qt
from PySide6.QtGui import QContextMenuEvent

from workbuddy_pet.settings import Settings,Rect,save_settings,load_settings
from workbuddy_pet.placement import pet_below_capsule,card_position
from workbuddy_pet.interaction import AmbientDirector,IdleDirector


@pytest.mark.parametrize('screen',[Rect(0,0,1920,1040),Rect(-1920,0,1920,1040)])
def test_restore_from_bottom_moves_pair_up_with_capsule_above_pet(screen):
    pet=Rect(900,650,264,316);anchor=Rect(940,720,184,215)
    capsule=Rect(screen.x+700,screen.height-36,310,36)
    x,y=pet_below_capsule(pet,anchor,capsule,[screen])
    restored=Rect(x,y,pet.width,pet.height);visible=Rect(x+40,y+70,184,215)
    cx,cy=card_position(restored,(310,36),[screen],compact=True,anchor=visible)
    assert cy<capsule.y and cy+36==visible.y-8
    assert y+pet.height<=screen.height and x>=screen.x and x+pet.width<=screen.x+screen.width
    assert abs(cx+155-(visible.x+visible.width/2))<=1


def controller_for(root,qt_app,settings=None):
    from workbuddy_pet.app import Controller
    if settings:save_settings(root,settings)
    controller=Controller(qt_app,root,True,workbuddy_home=root/'absent')
    controller.demo_timer.stop();controller.timer.stop()
    return controller


def test_detached_capsule_reaches_bottom_keeps_pet_still_and_restores(tmp_path,qt_app,monkeypatch):
    controller=controller_for(tmp_path,qt_app)
    monkeypatch.setattr(controller,'screens',lambda:[Rect(0,0,1920,1040)])
    try:
        controller.open_page('capsule');position=controller.pet.pos()
        controller.bubble.move(1100,1004);controller.card_moved(1100,1004);controller.position_bubble()
        assert controller.bubble.y()+36==1040 and controller.pet.pos()==position and not controller.pet.isVisible()
        controller.bubble.set_balance(1234567.5)
        assert controller.bubble.y()+36==1040 and controller.pet.pos()==position
        controller.save_position();saved=load_settings(tmp_path)
        assert saved.avatar_collapsed and saved.compact and saved.card_position==(controller.bubble.x(),1004)
        card=controller.bubble
        event=QContextMenuEvent(QContextMenuEvent.Reason.Mouse,QPoint(10,10),card.capsule.mapToGlobal(QPoint(10,10)))
        qt_app.sendEvent(card.capsule,event)
        assert card.context_menu.isVisible() and card.show_avatar_action.isVisible()
        card.show_avatar_action.trigger();card.context_menu.hide();qt_app.processEvents()
        assert controller.pet.isVisible() and card.compact and not controller.avatar_collapsed
        assert controller.pet.y()+controller.pet.height()<=1040
        visible=controller.pet.content_rect()
        assert card.y()+36==controller.pet.y()+visible.y()-8
    finally:controller.shutdown()


def test_restart_keeps_detached_capsule_at_bottom_and_card_only_needs_explicit_show(tmp_path,qt_app,monkeypatch):
    controller=controller_for(tmp_path,qt_app,Settings(compact=True,avatar_collapsed=True,card_position=(500,700)))
    monkeypatch.setattr(controller,'screens',lambda:[Rect(0,0,1920,1040)])
    try:
        assert not controller.pet.isVisible() and controller.bubble.compact
        controller.bubble.move(500,1004);controller.card_moved(500,1004);controller.save_position()
    finally:controller.shutdown()
    other=controller_for(tmp_path,qt_app)
    try:
        available=qt_app.primaryScreen().availableGeometry()
        assert not other.pet.isVisible() and other.bubble.compact
        assert other.bubble.y()+other.bubble.height()<=available.bottom()+1
        other.apply_settings(replace(other.settings,card_only=True));other.open_card()
        assert other.settings.card_only and not other.pet.isVisible()
        other.open_page('capsule');assert '仅卡片' in other.bubble.show_avatar_action.text()
        other.show_avatar();assert not other.settings.card_only and other.pet.isVisible()
    finally:other.shutdown()


def test_ambient_timer_does_not_reset_long_leisure_and_busy_cancels():
    short=AmbientDirector(random.Random(3));long=IdleDirector(random.Random(2))
    assert short.step(100,True) is None and 118<=short.next_due<=140
    long.step(100,True);long_due=long.next_due
    action=short.step(short.next_due,True)
    assert action.action=='idle_scratch' and action.seconds==1.8
    long.step(short.next_due,True);assert long.next_due==long_due
    assert short.step(short.until,True) is None
    short.step(short.next_due,True);assert short.active
    assert short.step(short.until-1,False) is None and short.active is None and short.next_due is None


def test_optional_idle_action_preserves_fifteen_action_packs(tmp_path):
    import json,shutil
    from test_full_pack import full_source
    from workbuddy_pet.materials import validate_pack,MaterialError
    manifest=full_source(tmp_path)
    assert len(validate_pack(tmp_path).actions)==15
    shutil.copyfile(tmp_path/'actions/click_wave.webp',tmp_path/'actions/idle_scratch.webp')
    manifest['actions']['idle_scratch']={'file':'actions/idle_scratch.webp','loop':False}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    assert len(validate_pack(tmp_path).actions)==16
    manifest['actions']['idle_scratch']['loop']=True
    (tmp_path/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(MaterialError):validate_pack(tmp_path)


@pytest.mark.parametrize('only_card',[False,True])
def test_explicit_reset_moves_independent_card_to_corner_without_changing_mode(tmp_path,qt_app,only_card):
    controller=controller_for(tmp_path,qt_app,Settings(card_only=only_card,compact=True,avatar_collapsed=not only_card,card_position=(50,50)))
    try:
        mode=controller.bubble.mode;controller.dialog.reset_requested.emit()
        screen=qt_app.primaryScreen().availableGeometry();card=controller.bubble
        assert card.x()+card.width()==screen.right()+1-24
        assert card.y()+card.height()==screen.bottom()+1-24
        assert controller.bubble.mode==mode and controller.settings.card_only==only_card and not controller.pet.isVisible()
        assert load_settings(tmp_path).card_position==card.pos().toTuple()
    finally:controller.shutdown()


def test_optional_scratch_yields_to_existing_leisure_tasks_menu_and_click(tmp_path,qt_app):
    import json,shutil,time
    from test_full_pack import full_source
    from workbuddy_pet.materials import MaterialLibrary
    from workbuddy_pet.events import Event
    source=tmp_path/'source';manifest=full_source(source)
    shutil.copyfile(source/'actions/click_wave.webp',source/'actions/idle_scratch.webp')
    manifest['actions']['idle_scratch']={'file':'actions/idle_scratch.webp','loop':False}
    (source/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    pack=MaterialLibrary(tmp_path/'characters').import_pack(source)
    controller=controller_for(tmp_path,qt_app,Settings(character=pack.key,notifications=False))
    try:
        controller.sessions={};controller.bubble.set_compact(True)
        controller.idle_director.next_due=time.monotonic()+100;controller.ambient_director.next_due=0
        controller.refresh();assert controller.visual_action=='idle_scratch'
        controller.idle_director.next_due=0;controller.refresh()
        assert controller.visual_action.startswith('leisure_') and controller.ambient_director.active is None
        now=time.time();controller.consume([Event('task',now,'s','UserPromptSubmit'),Event('tool',now+.01,'s','PreToolUse')])
        assert controller.visual_action=='working' and controller.ambient_director.active is None
        controller.interact();assert controller.visual_action=='click_wave'
        controller.consume([Event('approval',now+.02,'s','PermissionRequest')])
        assert controller.visual_action=='review' and not controller.active_interaction
        controller.sessions={};controller.idle_director.cancel();controller.ambient_director.next_due=0
        controller.bubble.context_menu.popup(controller.bubble.mapToGlobal(QPoint(10,10)));controller.refresh()
        assert controller.ambient_director.active is None
        controller.bubble.context_menu.hide();controller.open_page('capsule')
        assert not controller.pet.isVisible() and controller.ambient_director.active is None
    finally:controller.shutdown()


def test_hd_sixteen_actions_with_sixteen_frames_are_supported(tmp_path):
    import json,shutil
    from PIL import Image,ImageDraw
    from workbuddy_pet.materials import ALL_ACTIONS,LOOP_ACTIONS,validate_pack
    (tmp_path/'actions').mkdir();frames=[]
    for index in range(16):
        image=Image.new('RGBA',(512,512));ImageDraw.Draw(image).ellipse((100+index,40,320+index,480),fill='#67bbad');frames.append(image)
    first=tmp_path/'actions/idle.webp'
    frames[0].save(first,save_all=True,append_images=frames[1:],duration=100,lossless=True)
    actions=ALL_ACTIONS+('idle_scratch',)
    for action in actions:
        if action!='idle':shutil.copyfile(first,tmp_path/f'actions/{action}.webp')
    manifest={'schema':2,'id':'hd-max','name':'synthetic','author':'test','license':'CC0-1.0','version':'1','quality':'hd',
        'actions':{a:{'file':f'actions/{a}.webp','loop':a in LOOP_ACTIONS} for a in actions}}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    assert len(validate_pack(tmp_path).actions)==16


def test_first_hidden_capsule_without_card_coordinates_anchors_at_saved_pet(tmp_path,qt_app):
    area=qt_app.primaryScreen().availableGeometry()
    position=(area.x()+area.width()//2,area.y()+area.height()//2)
    controller=controller_for(tmp_path,qt_app,Settings(compact=True,avatar_collapsed=True,position=position))
    try:
        pet=controller.pet;visible=pet.content_rect();card=controller.bubble
        assert not pet.isVisible() and card.compact
        assert card.y()+card.height()==pet.y()+visible.y()-8
        # Once detached, the later "积分未启用" width change keeps its own left
        # coordinate; it must stay near the saved pet rather than the origin.
        assert card.x()>=area.x()+area.width()//4
    finally:controller.shutdown()
