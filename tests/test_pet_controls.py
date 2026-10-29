from dataclasses import replace
from workbuddy_pet.state import SessionState,derive_display
from workbuddy_pet.settings import Settings,save_settings,load_settings

def test_stale_busy_yields_without_fabricated_completion():
    old=SessionState('old',state='working',at=100)
    d=derive_display({'old':old},220)
    assert (d.state,d.connection,d.reminders)==('idle','stale',())
    fresh=SessionState('fresh',state='thinking',at=219)
    assert derive_display({'old':old,'fresh':fresh},220).session_id=='fresh'
    assert derive_display({'old':replace(old,at=221)},221).state=='working'
    assert derive_display({'old':replace(old,state='review')},9999).state=='review'


def test_stale_allows_leisure_without_resolving_task_and_keeps_visible_warning(qt_app):
    from workbuddy_pet.interaction import idle_allowed
    from workbuddy_pet.ui.card import CardWindow
    old = SessionState('old', state='working', at=100)
    sessions = {'old': old}
    display = derive_display(sessions, 220)
    assert idle_allowed(sessions, display, 220)
    assert sessions['old'].state == 'working' and not sessions['old'].terminal
    card = CardWindow()
    try:
        card.set_display(display)
        assert '状态待确认' in card.capsule.text()
        assert not card.subtitle.isHidden() and '确认' in card.subtitle.text()
        for state in ('review', 'waiting', 'failed', 'thinking'):
            peers = {**sessions, 'fresh': SessionState('fresh', state=state, at=219)}
            assert not idle_allowed(peers, derive_display(peers, 220), 220)
        card.set_display(derive_display({'fresh': SessionState('fresh', state='thinking', at=219)}, 220))
        assert card.subtitle.isHidden() and '状态待确认' not in card.capsule.text()
    finally:
        card.close()

def test_modes_menus_and_persistence(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop()
    try:
        c.set_display_mode(True);qt_app.processEvents()
        c.bubble.set_balance(1234.9,'test');qt_app.processEvents()
        assert c.bubble.size().toTuple()==(48,48)
        assert c.bubble.balance_badge.text()=='1234'
        assert not c.bubble.capsule.isVisible() and c.pet.isVisible()
        c.open_page('details');c.bubble.set_compact(True);assert c.bubble.width()==48
        c.populate_menu(c.pet.context_menu)
        actions=c.pet.context_menu.character_menu.actions()
        assert [a.data() for a in actions[:2]]==['builtin','builtin-blue-fish']
        actions[1].trigger();assert c.settings.character=='builtin-blue-fish'
        assert load_settings(tmp_path).minimal
        c.collapse_avatar();assert c.bubble.width()>48 and not c.pet.isVisible()
        c.show_avatar();assert c.bubble.width()==48
        c.set_display_mode(False);assert c.bubble.width()>48 and c.bubble.capsule.isVisible()
    finally:c.shutdown()

def test_drag_releases_without_click_and_hide_clears(qt_app):
    from workbuddy_pet.ui.pet import PetWindow
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt,QPoint
    p=PetWindow();p.show();hits=[];p.interact_requested.connect(lambda:hits.append(True))
    try:
        QTest.mousePress(p,Qt.LeftButton,pos=QPoint(70,90))
        QTest.mouseMove(p,QPoint(100,100),delay=30);QTest.qWait(220)
        assert p.dragging and p.lift>.9
        QTest.mouseRelease(p,Qt.LeftButton,pos=QPoint(100,100));QTest.qWait(450)
        assert not hits and p.lift==0 and not p.dragging
        QTest.mouseClick(p,Qt.LeftButton,pos=QPoint(70,90));assert hits==[True]
        p.animate_lift(True);QTest.qWait(200);p.hide();assert p.lift==0
    finally:p.close()
