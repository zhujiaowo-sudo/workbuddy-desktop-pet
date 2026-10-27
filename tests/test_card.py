from dataclasses import replace
import time

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from workbuddy_pet.settings import Settings,save_settings
from workbuddy_pet.state import DisplayState,Reminder
from workbuddy_pet.ui.card import CardWindow


def test_auto_capsule_respects_activity_work_and_unread(qt_app,monkeypatch):
    card=CardWindow()
    monkeypatch.setattr(card,'underMouse',lambda:False)
    settings=Settings(collapse_seconds=10)
    card.set_display(DisplayState('working','connected'))
    card.last_interaction=0;card.maybe_collapse(settings,100)
    assert not card.compact
    card.set_display(DisplayState('idle','connected',reminders=(Reminder('r','s','done'),)))
    card.maybe_collapse(settings,100)
    assert not card.compact
    card.set_display(DisplayState('idle','connected'));card.maybe_collapse(settings,100)
    assert card.compact
    card.set_compact(False);card.last_interaction=0
    card.maybe_collapse(replace(settings,auto_collapse=False),100)
    assert not card.compact
    card.close()


def test_only_card_and_embedded_settings_survive_toggle(tmp_path,qt_app):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(card_only=True,notifications=False))
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent-workbuddy')
    controller.demo_timer.stop()
    assert controller.bubble.isVisible() and not controller.pet.isVisible()
    assert not controller.pet.timer.isActive() and not controller.player.frames
    controller.open_settings()
    assert controller.dialog.window() is controller.bubble
    assert controller.bubble.tabs.tabText(controller.bubble.tabs.currentIndex())=='设置'
    controller.apply_settings(replace(controller.settings,card_only=False))
    assert controller.pet.isVisible()
    controller.toggle_visible();assert not controller.bubble.isVisible()
    controller.toggle_visible();assert controller.bubble.isVisible()
    controller.shutdown()


def test_material_player_pause_and_state_fallback(tmp_path,qt_app):
    from PIL import Image
    import json
    from workbuddy_pet.materials import MaterialLibrary
    from workbuddy_pet.ui.animation import AnimationPlayer
    source=tmp_path/'source';source.mkdir()
    frames=[Image.new('RGBA',(16,16),color) for color in ('blue','green')]
    frames[0].save(source/'idle.gif',save_all=True,append_images=frames[1:],duration=[80,120],loop=0)
    (source/'manifest.json').write_text(json.dumps({'schema':1,'id':'s','name':'s','author':'s','version':'1','license':'CC0',
        'actions':{'idle':{'file':'idle.gif'}}}))
    pack=MaterialLibrary(tmp_path/'library').import_pack(source)
    player=AnimationPlayer();player.load(pack,'working')
    assert player.timer.isActive()
    player.set_visible(False);assert not player.timer.isActive()
    player.set_visible(True);assert player.timer.isActive()
    player.advance();assert player.index==1
    player.clear();assert not player.frames and not player.timer.isActive()
