from dataclasses import replace
import json

import pytest

from workbuddy_pet.settings import Settings,save_settings,load_settings
from workbuddy_pet.windows import website_url,path_from_registration


def test_settings_migration_does_not_grant_account_access(tmp_path):
    (tmp_path/'settings.json').write_text('{"size":150,"startup":false}')
    settings=load_settings(tmp_path)
    assert not settings.balance_enabled and not settings.checkin_enabled and not settings.onboarding_done
    assert settings.quick_action=='checkin' and settings.auto_update
    save_settings(tmp_path,replace(settings,quick_action='custom',quick_url='https://example.com',auto_update=False))
    assert load_settings(tmp_path).quick_url=='https://example.com' and not load_settings(tmp_path).auto_update


def test_websites_and_registration_paths():
    for url in ('file:///C:/x','javascript:alert(1)','https://user:pass@example.com','https://example.com/\n','https://example.com:bad'):
        with pytest.raises(ValueError):website_url(url)
    assert website_url('https://example.com/a?q=1')=='https://example.com/a?q=1'
    assert path_from_registration('"D:/Work Buddy/WorkBuddy.exe" "%1"').name=='WorkBuddy.exe'
    assert path_from_registration('D:/Work Buddy/WorkBuddy.exe,0').name=='WorkBuddy.exe'
    assert path_from_registration('other.exe') is None


def test_manual_capsule_hides_and_expansion_restores_avatar(tmp_path,qt_app):
    from workbuddy_pet.app import Controller
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent')
    controller.demo_timer.stop()
    try:
        controller.open_page('capsule')
        assert controller.bubble.compact and not controller.pet.isVisible() and not controller.player.visible
        controller.bubble.open_summary(manual=True)
        assert controller.pet.isVisible() and not controller.settings.card_only
        assert any(a.text()=='退出桌宠' for a in controller.pet.context_menu.actions())
        controller.apply_settings(replace(controller.settings,card_only=True))
        controller.open_page('capsule');controller.open_card()
        assert not controller.pet.isVisible()
    finally:controller.shutdown()


def test_balance_integer_adapts_width_and_quick_action_dispatch(tmp_path,qt_app,monkeypatch):
    from workbuddy_pet.app import Controller
    import workbuddy_pet.windows as windows
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent');controller.demo_timer.stop()
    try:
        card=controller.bubble;card.set_compact(True);card.set_balance(12.999)
        narrow=card.balance_badge.width();assert card.balance_badge.text()=='12' and narrow<94
        card.set_balance(1234567.99)
        assert card.balance_badge.text()=='1,234,567' and card.balance_badge.width()>narrow
        assert card.width()==card.capsule_width() and '.' not in card.remaining_value.text()
        calls=[];monkeypatch.setattr(controller,'checkin_clicked',lambda:calls.append('claim'))
        monkeypatch.setattr(controller,'refresh_data',lambda:calls.append('refresh'))
        monkeypatch.setattr(windows,'open_website',lambda url:calls.append(url))
        for key in ('website','custom','refresh','checkin'):
            controller.apply_settings(replace(controller.settings,quick_action=key,quick_url='https://example.com'))
            card.signin_button.click()
        assert calls==[windows.WORKBUDDY_WEBSITE,'https://example.com','refresh','claim']
    finally:controller.shutdown()


def test_first_binding_waits_for_consent(tmp_path,qt_app,monkeypatch):
    from workbuddy_pet.app import Controller
    import workbuddy_pet.app as app
    calls=[];monkeypatch.setattr(app,'read_balance',lambda *_:calls.append('balance'))
    monkeypatch.setattr(app,'read_checkin',lambda *_:calls.append('status'))
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=tmp_path/'absent');controller.demo_timer.stop()
    try:
        controller.demo=False;controller.first_binding();controller.binding.reject()
        assert not controller.settings.balance_enabled and not controller.settings.checkin_enabled
        assert not calls and not (tmp_path/'integration-receipt.json').exists()
    finally:controller.shutdown()


def test_one_binding_confirmation_preserves_other_plugins(tmp_path,qt_app):
    from workbuddy_pet.app import Controller
    exe=tmp_path/'WorkBuddy.exe';exe.write_bytes(b'MZ-synthetic')
    home=tmp_path/'buddy-home';home.mkdir()
    (home/'settings.json').write_text(json.dumps({'enabledPlugins':{'other':True},'permissions':{'mode':'ask'}}))
    save_settings(tmp_path,Settings(workbuddy_path=str(exe),notifications=False))
    controller=Controller(qt_app,tmp_path,True,workbuddy_home=home);controller.demo_timer.stop()
    try:
        controller.complete_binding(True,False)
        assert controller.settings.balance_enabled and not controller.settings.checkin_enabled and controller.settings.onboarding_done
        assert (tmp_path/'integration-receipt.json').is_file()
        value=json.loads((home/'settings.json').read_text())
        assert value['enabledPlugins']['other'] and value['permissions']=={'mode':'ask'}
    finally:controller.shutdown()
