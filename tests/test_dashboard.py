import hashlib,json
from pathlib import Path
from PySide6.QtCore import Qt,QAbstractAnimation
from PySide6.QtTest import QTest
from workbuddy_pet.settings import Settings,save_settings,load_settings


def test_dragon_pack_all_frames_hashes_and_user_approved_mapping():
    from workbuddy_pet.builtin import builtin_pack
    from workbuddy_pet.materials import validate_pack
    from PIL import Image
    pack=builtin_pack('builtin-dragon-maid');validate_pack(pack.root)
    audit=json.loads((Path(__file__).resolve().parents[1]/'art/dragon-maid/user-gifs-v1.0.0.json').read_text())
    assert len(audit)==len(pack.actions)==18
    for entry in audit:
        source=pack.root/pack.actions[entry['action']].file
        assert hashlib.sha256(source.read_bytes()).hexdigest()==entry['sha256']
        with Image.open(source) as im:
            assert im.n_frames==30 and im.size==(720,720)
            duration=0
            for i in range(30):im.seek(i);duration+=im.info['duration']
            assert duration==entry['duration_ms']
    assert (pack.root/'actions/working.gif').read_bytes()==(pack.root/'actions/thinking.gif').read_bytes()


def test_dashboard_modes_persist_and_navigation_does_not_restore_avatar(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(character='builtin-dragon-maid',compact=True,notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop()
    try:
        c.open_page('mode:detached');c.bubble.open_page('data');qt_app.processEvents()
        assert not c.pet.isVisible() and not c.player.visible
        assert load_settings(tmp_path).avatar_collapsed
        c.populate_menu(c.bubble.context_menu)
        assert [k for k,a in c.bubble.context_menu.mode_actions.items() if a.isChecked()]==['detached']
        c.open_page('mode:minimal');assert c.pet.isVisible() and c.bubble.width()==48
        c.open_page('mode:standard');assert c.pet.isVisible() and c.bubble.width()>48
        assert load_settings(tmp_path).character=='builtin-dragon-maid'
    finally:c.shutdown()


def test_keyboard_open_and_escape_skip_motion(qt_app,monkeypatch):
    from workbuddy_pet.ui.card import CardWindow
    monkeypatch.setattr('workbuddy_pet.windows.ui_animations_enabled',lambda:True)
    card=CardWindow();card.set_compact(True);card.show();card.capsule.setFocus()
    try:
        QTest.keyClick(card.capsule,Qt.Key.Key_Space);qt_app.processEvents()
        assert card.mode=='expanded' and card.tabs.currentIndex()==0
        assert card.panel_fade.state()==QAbstractAnimation.State.Stopped and card.windowOpacity()==1
        QTest.keyClick(card,Qt.Key.Key_Escape)
        assert card.compact and card.windowOpacity()==1
    finally:card.close()


def test_reduced_motion_and_rapid_close(qt_app,monkeypatch):
    from workbuddy_pet.ui.card import CardWindow
    card=CardWindow();card.set_compact(True);card.show()
    try:
        monkeypatch.setattr('workbuddy_pet.windows.ui_animations_enabled',lambda:False)
        QTest.mouseClick(card.capsule,Qt.MouseButton.LeftButton)
        assert card.windowOpacity()==1 and card.panel_fade.state()==QAbstractAnimation.State.Stopped
        card.set_compact(True)
        monkeypatch.setattr('workbuddy_pet.windows.ui_animations_enabled',lambda:True)
        QTest.mouseClick(card.capsule,Qt.MouseButton.LeftButton)
        card.set_compact(True)
        assert card.windowOpacity()==1 and card.panel_fade.state()==QAbstractAnimation.State.Stopped
    finally:card.close()


def test_usage_tab_refresh_and_busy_feedback(qt_app):
    from workbuddy_pet.ui.card import CardWindow
    from workbuddy_pet.local_data import UsageSnapshot
    card=CardWindow();requests=[];card.data_requested.connect(requests.append)
    try:
        card.open_page('data');assert requests==[None]
        card.set_data_busy(True);assert not card.data_refresh.isEnabled() and not card.table.isEnabled()
        card.set_snapshot(UsageSnapshot(available=False,message='数据库暂被占用'))
        assert card.data_refresh.isEnabled() and card.table.isEnabled()
        assert card.today_value.text()=='待同步' and '失败' in card.data_status.text()
    finally:card.close()


def test_published_schema_matches_new_optional_actions():
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/pet-pack.schema.json').read_text())
    branches={x['properties']['schema']['const']:x['properties']['actions'] for x in schema['oneOf']}
    assert {'idle_scratch','idle_sleep','idle_bow'}<=branches[3]['properties'].keys()
    assert not {'idle_sleep','idle_bow'}&branches[2]['properties'].keys()


def test_settings_save_remains_reachable_and_reports_result(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop()
    try:
        c.open_page('settings');c.dialog.path.setText('');c.dialog.size.setValue(180)
        scroll=c.bubble.tabs.pages.widget(3);scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        assert c.bubble.settings_save.isVisible()
        c.bubble.settings_save.click()
        assert load_settings(tmp_path).size==180 and c.bubble.settings_save.text()=='已保存'
        c.dialog.size.setValue(190);assert c.bubble.settings_save.text()=='保存'
    finally:c.shutdown()
