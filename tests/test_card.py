from dataclasses import replace
import time
import pytest

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


@pytest.mark.parametrize('size',[100,224,240])
def test_collapse_reanchors_above_pet_without_moving_it(tmp_path,qt_app,monkeypatch,size):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.settings import Rect
    save_settings(tmp_path,Settings(size=size,notifications=False))
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    monkeypatch.setattr(controller,'screens',lambda:[Rect(0,0,1920,1040)])
    controller.demo_timer.stop()
    controller.pet.move(900,650);controller.position_bubble()
    position=controller.pet.pos()
    for _ in range(4):
        controller.bubble.set_compact(True);qt_app.processEvents()
        assert controller.pet.pos()==position
        visible=controller.pet.content_rect()
        assert abs(controller.bubble.x()+controller.bubble.width()/2-(controller.pet.x()+visible.x()+visible.width()/2))<=1
        assert controller.bubble.y()+controller.bubble.height()==controller.pet.y()+visible.y()-8
        assert controller.pet.width()==size+24
        controller.bubble.set_compact(False);qt_app.processEvents()
        assert controller.pet.pos()==position
        assert controller.bubble.mode=='summary'
        assert controller.bubble.width()==320 and controller.bubble.height()==202
    controller.shutdown()


def test_context_menu_selects_page_before_expansion(tmp_path,qt_app,monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent
    from workbuddy_pet.app import Controller
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    chat_calls=[];monkeypatch.setattr(controller,'open_current_conversation',lambda:chat_calls.append('open'))
    controller.demo_timer.stop();controller.bubble.set_compact(True)
    event=QContextMenuEvent(QContextMenuEvent.Reason.Mouse,QPoint(20,20),controller.pet.mapToGlobal(QPoint(20,20)))
    qt_app.sendEvent(controller.pet,event)
    assert controller.bubble.compact
    for action in controller.pet.context_menu.actions():
        if not action.data():continue
        previous=(controller.bubble.mode,controller.bubble.tabs.currentIndex())
        action.trigger();qt_app.processEvents()
        key=action.data()
        if key=='capsule':assert controller.bubble.compact
        elif key=='summary':assert controller.bubble.mode=='summary'
        elif key=='chat':
            assert chat_calls==['open'] and (controller.bubble.mode,controller.bubble.tabs.currentIndex())==previous
        else:
            assert not controller.bubble.compact
            assert controller.bubble.tabs.currentIndex()==('details','data','materials','settings').index(key)
    controller.pet.context_menu.hide();controller.shutdown()


def test_navigation_never_overlaps_divider_and_content(qt_app):
    from PySide6.QtWidgets import QLabel
    from PySide6.QtCore import QPoint
    card=CardWindow()
    for name in ('聊天','素材','设置'):card.add_page(QLabel(name),name)
    card.open_page('details');card.show()
    for _ in range(3):
        for index in range(card.tabs.count()):
            card.tabs.setCurrentIndex(index);qt_app.processEvents()
            divider_bottom=card.divider.mapTo(card,QPoint(0,card.divider.height())).y()
            tab_top=card.tabs.bar.mapTo(card,QPoint()).y()
            content_top=card.tabs.pages.mapTo(card,QPoint()).y()
            assert tab_top>=divider_bottom+5
            assert content_top>=tab_top+card.tabs.bar.height()+5
            assert card.collapse_button.mapTo(card.summary,QPoint()).y()<35
            assert card.collapse_button.mapTo(card,QPoint()).x()>card.width()/2
            image=card.grab().toImage()
            assert image.pixelColor(2,card.height()//2).alpha()==255
    card.close()


def test_balance_unknown_is_not_zero_or_consumed_credit(qt_app):
    from workbuddy_pet.local_data import UsageSnapshot
    card=CardWindow();card.set_compact(True)
    card.set_snapshot(UsageSnapshot(True,total_credit=9999))
    assert card.balance is None and card.balance_badge.text()=='积分待同步'
    card.set_balance(0,'synthetic source')
    assert card.balance==0 and '0.0' in card.balance_badge.text()
    for invalid in (-1,float('nan'),True,None):
        card.set_balance(invalid);assert card.balance is None
    card.close()


def test_card_only_position_is_independent_of_pet(tmp_path,qt_app):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.settings import load_settings
    save_settings(tmp_path,Settings(card_only=True,notifications=False,card_position=(180,170)))
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    controller.demo_timer.stop()
    pet_position=controller.pet.pos()
    controller.bubble.move(210,190);controller.card_moved(210,190);controller.save_position()
    assert load_settings(tmp_path).card_position==(210,190)
    controller.bubble.set_compact(True);qt_app.processEvents()
    assert controller.bubble.pos().toTuple()==(210,190)
    assert controller.pet.pos()==pet_position
    controller.shutdown()


def test_three_levels_and_numeric_credit_without_capsule_frame(tmp_path,qt_app):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.local_data import UsageSnapshot,SessionInfo
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    controller.demo_timer.stop();QTest.qWait(60);card=controller.bubble
    card.set_snapshot(UsageSnapshot(True,sessions=(SessionInfo('s','测试会话','model'),),
                                    today_credit=3.5,today_requests=2,today_date='2026-10-27'))
    card.set_display(DisplayState('working','connected','s'))
    card.set_balance(123.45,'synthetic')
    card.set_compact(True);qt_app.processEvents()
    assert card.mode=='capsule' and card.size().toTuple()==(342,36)
    assert card.balance_badge.text()=='123.45'
    image=card.grab().toImage()
    ratio=image.devicePixelRatio()
    # Transparent rounded corners and the gap between the only two modules.
    assert image.pixelColor(0,0).alpha()==0
    assert image.pixelColor(round((card.signin_button.geometry().right()+3)*ratio),round(18*ratio)).alpha()==0
    assert card.capsule.font().pixelSize()==12 and card.balance_badge.font().pixelSize()==11
    assert card.balance_badge.font().bold() and card.signin_button.size().toTuple()==(36,36)
    gap=card.capsule.geometry().right()+3
    assert image.pixelColor(round(gap*ratio),round(16*ratio)).alpha()==0
    QTest.mouseClick(card.capsule,Qt.MouseButton.LeftButton);qt_app.processEvents()
    assert card.mode=='summary' and not card.expanded.isVisible()
    assert card.remaining_value.text()=='123.45' and card.today_value.text()=='3.500'
    assert card.session_link.isVisible() and card.session_link.toolTip()=='测试会话'
    QTest.mouseClick(card.data_button,Qt.MouseButton.LeftButton);qt_app.processEvents()
    assert card.mode=='expanded' and card.tabs.currentIndex()==1
    assert card.summary.isVisible() and card.expanded.isVisible()
    QTest.mouseClick(card.back_button,Qt.MouseButton.LeftButton);qt_app.processEvents()
    assert card.mode=='summary'
    controller.open_page('settings');qt_app.processEvents()
    assert card.mode=='expanded' and card.tabs.currentIndex()==3
    controller.open_card();qt_app.processEvents()
    assert card.mode=='summary'
    QTest.mouseClick(card.collapse_button,Qt.MouseButton.LeftButton);qt_app.processEvents()
    assert card.mode=='capsule'
    controller.shutdown()


def test_unindexed_current_session_does_not_show_another_session(qt_app):
    from workbuddy_pet.local_data import UsageSnapshot,SessionInfo
    card=CardWindow()
    card.set_snapshot(UsageSnapshot(True,sessions=(SessionInfo('old','旧会话','m'),)))
    card.set_display(DisplayState('working','connected','new'))
    assert card.current_session=='new' and '旧会话' not in card.session_link.text()
    card.close()


def test_all_views_are_centered_above_and_dashboard_fits_small_screen(tmp_path,qt_app,monkeypatch):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.settings import Rect
    save_settings(tmp_path,Settings(size=224,notifications=False))
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    controller.demo_timer.stop();controller.timer.stop()
    screen=Rect(0,0,1280,690);monkeypatch.setattr(controller,'screens',lambda:[screen])
    controller.pet.move(500,100)
    for mode in ('capsule','summary','expanded','capsule'):
        controller.bubble.set_mode(mode);qt_app.processEvents();controller.position_bubble()
        visible=controller.pet.content_rect();card=controller.bubble
        assert abs(card.x()+card.width()/2-(controller.pet.x()+visible.x()+visible.width()/2))<=1
        assert card.y()+card.height()==controller.pet.y()+visible.y()-8
        assert card.y()>=0 and controller.pet.y()+controller.pet.height()<=690
        if mode=='expanded':assert 320<=card.height()<540
    controller.shutdown()


def test_dragging_capsule_module_moves_without_expanding(qt_app):
    from PySide6.QtCore import QPointF,QEvent
    from PySide6.QtGui import QMouseEvent
    card=CardWindow();card.set_compact(True);card.move(200,200);card.show();qt_app.processEvents()
    button=card.capsule
    origin=button.mapToGlobal(button.rect().center())
    moves=[];card.moved.connect(lambda x,y:moves.append((x,y)))
    for kind,delta,pressed,buttons in (
        (QEvent.Type.MouseButtonPress,0,Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseMove,30,Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseButtonRelease,30,Qt.MouseButton.LeftButton,Qt.MouseButton.NoButton)):
        point=QPointF(origin.x()+delta,origin.y()+delta)
        event=QMouseEvent(kind,QPointF(10,10),point,pressed,buttons,Qt.KeyboardModifier.NoModifier)
        qt_app.sendEvent(button,event)
    assert moves and moves[-1]==(230,230) and card.compact
    assert not button.isDown()
    card.close()
