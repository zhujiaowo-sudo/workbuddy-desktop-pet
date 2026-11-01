import json,sqlite3,time
from dataclasses import replace
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from workbuddy_pet.settings import Settings,load_settings,save_settings


def test_appearance_settings_persist_and_invalid_values_fall_back(tmp_path):
    value=replace(Settings(),theme='red',capsule_transparent=True,window_mode=True)
    save_settings(tmp_path,value);assert load_settings(tmp_path)==value
    (tmp_path/'settings.json').write_text(json.dumps({'theme':'bad','window_mode':'true','capsule_transparent':1}))
    loaded=load_settings(tmp_path)
    assert loaded.theme=='gray' and not loaded.window_mode and not loaded.capsule_transparent


def test_daily_credits_use_calendar_days_not_selected_report_range(tmp_path):
    from test_local_data import fixture_home
    from workbuddy_pet.local_data import LocalDataReader
    log=fixture_home(tmp_path);now=datetime(2026,11,1,12).timestamp()
    credits={'old':9,'first':1.25,'today':2.5,'future':10,'unknown':8}
    with sqlite3.connect(tmp_path/'workbuddy.db') as db:
        db.execute('UPDATE session_usage SET credit_json=? WHERE session_id=?',(json.dumps(credits),'s'))
    rows=[('old',datetime(2026,10,25,23).timestamp()),('first',datetime(2026,10,26).timestamp()),('today',now),('future',now+1)]
    log.write_text('\n'.join(json.dumps({'timestamp':at,'providerData':{'conversationRequestId':rid,'requestModelId':'example'}}) for rid,at in rows))
    reader=LocalDataReader(tmp_path)
    for days in (None,7,30):
        snap=reader.snapshot(days,now)
        assert len(snap.daily_usage)==7
        assert snap.daily_usage[0].day=='2026-10-26' and snap.daily_usage[0].credit==1.25
        assert snap.daily_usage[-1].day=='2026-11-01' and snap.daily_usage[-1].credit==2.5
        assert sum(x.credit for x in snap.daily_usage)==3.75
    log.write_text('');reader=LocalDataReader(tmp_path)
    assert reader.snapshot(now=now).daily_usage==()


def test_window_buttons_return_and_hidden_state_survive_restart(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop()
    try:
        c.open_page('mode:window_only');qt_app.processEvents()
        assert c.bubble.mode=='window' and not c.pet.isVisible()
        assert len(c.bubble.window_panel.header_buttons)==2
        c.bubble.window_panel.expand_button.click();assert c.bubble.mode=='expanded' and not c.pet.isVisible()
        c.bubble.back_button.click();assert c.bubble.mode=='window'
        c.bubble.maybe_collapse(c.settings,time.monotonic()+9999);assert c.bubble.mode=='window'
        c.bubble.window_panel.capsule_button.click();assert c.bubble.mode=='capsule' and not c.pet.isVisible()
        assert not load_settings(tmp_path).window_mode
        c.open_page('mode:window_only')
    finally:c.shutdown()
    other=Controller(qt_app,tmp_path,True,tmp_path/'absent');other.timer.stop();other.demo_timer.stop()
    try:assert other.bubble.mode=='window' and not other.pet.isVisible()
    finally:other.shutdown()


def test_theme_transparency_and_bold_digits_keep_window_size(qt_app):
    from workbuddy_pet.ui.card import CardWindow
    card=CardWindow();card.show()
    try:
        for name in ('gray','blue','red'):
            card.apply_appearance(name,True);card.set_compact(True)
            assert card.theme_key==name and card.capsule_transparent
            qt_app.processEvents()
            image=card.grab().toImage();ratio=image.devicePixelRatio()
            assert image.pixelColor(round((card.capsule.x()+25)*ratio),round(7*ratio)).alpha()<8
            card.set_balance(1234567.8)
            assert card.balance_badge.font().bold() and card.balance_badge.font().pixelSize()>=13
            assert card.balance_badge.text()=='1,234,567'
            card.window_mode=True;card.set_compact(True);size=card.size()
            card.set_balance(98765);assert card.size()==size and card.mode=='window'
            assert card.window_panel.remaining.font().bold()
            card.window_mode=False
    finally:card.close()


def test_persistent_window_allows_idle_actions(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(character='builtin-dragon-maid',window_mode=True,compact=True,notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop()
    try:
        c.sessions={};c.idle_director.next_due=0;c.refresh()
        assert c.bubble.mode=='window' and c.idle_director.active is not None
    finally:c.shutdown()


def test_settings_and_shortcut_themes_preserve_mode_and_character(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(character='builtin-blue-fish',notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop()
    try:
        c.open_page('mode:window_only');c.open_page('theme:blue');c.open_page('transparent:1')
        c.open_page('settings');c.dialog.path.setText('')
        c.dialog.theme_combo.setCurrentIndex(c.dialog.theme_combo.findData('red'));c.bubble.settings_save.click()
        assert c.settings.window_mode and c.settings.card_only and c.settings.theme=='red'
        assert c.settings.capsule_transparent and c.settings.character=='builtin-blue-fish'
        c.bubble.back_button.click();assert c.bubble.mode=='window' and not c.pet.isVisible()
        c.populate_menu(c.bubble.context_menu)
        assert c.bubble.context_menu.mode_actions['window_only'].isChecked()
        assert c.bubble.context_menu.theme_actions['red'].isChecked() and c.bubble.context_menu.transparent_action.isChecked()
        c.open_page('settings');c.dialog.display_mode.setCurrentIndex(c.dialog.display_mode.findData('window'))
        c.bubble.settings_save.click();c.bubble.back_button.click()
        assert c.pet.isVisible() and c.bubble.mode=='window' and c.active_pack.key=='builtin-blue-fish'
    finally:c.shutdown()
