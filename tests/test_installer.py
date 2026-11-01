import json
from dataclasses import replace
from pathlib import Path
import pytest
from workbuddy_pet import setup
from workbuddy_pet.settings import Settings,save_settings,load_settings

@pytest.fixture
def bridge(monkeypatch):
    calls=[]
    monkeypatch.setattr(setup,'discover_workbuddy',lambda:Path('WorkBuddy.exe'))
    monkeypatch.setattr(setup,'install_integration',lambda *a:calls.append(('connect',a)))
    monkeypatch.setattr(setup,'configure_startup',lambda *a:calls.append(('startup',a)))
    monkeypatch.setattr(setup,'stop_running',lambda *a:None)
    return calls

def test_new_installer_applies_only_selected_consents(tmp_path,bridge):
    root=tmp_path/'profile'
    result=setup.apply_setup(root,tmp_path/'wb',connect=True,balance=True,checkin=False)
    s=load_settings(root)
    assert result['state']=='configured' and s.onboarding_done
    assert s.balance_enabled and not s.checkin_enabled and not s.startup
    assert [c[0] for c in bridge]==['connect']

def test_existing_user_keeps_all_preferences(tmp_path,bridge):
    s=Settings(character='builtin-blue-fish',balance_enabled=False,checkin_enabled=True,minimal=True,onboarding_done=True)
    save_settings(tmp_path,s)
    setup.apply_setup(tmp_path,tmp_path/'wb',connect=True,balance=True,checkin=False,startup=True)
    assert load_settings(tmp_path)==s and not bridge

def test_existing_binding_migrates_without_changing_consent(tmp_path,bridge):
    save_settings(tmp_path,Settings(onboarding_done=True,balance_enabled=True))
    (tmp_path/'integration-receipt.json').write_text(json.dumps({'home':str(tmp_path/'wb')}))
    setup.apply_setup(tmp_path,tmp_path/'other',connect=False)
    assert bridge[0][0]=='connect' and bridge[0][1][0]==tmp_path/'wb'
    assert load_settings(tmp_path).balance_enabled

def test_missing_workbuddy_does_not_claim_authorization(tmp_path,bridge,monkeypatch):
    monkeypatch.setattr(setup,'discover_workbuddy',lambda:None)
    result=setup.apply_setup(tmp_path,tmp_path/'wb',connect=True,balance=True,checkin=True)
    assert result['state']=='needs_workbuddy' and not load_settings(tmp_path).balance_enabled
    assert not load_settings(tmp_path).onboarding_done and not bridge

def test_connection_failure_does_not_save_new_grants(tmp_path,bridge,monkeypatch):
    def fail(*a):raise ValueError('conflict')
    monkeypatch.setattr(setup,'install_integration',fail)
    with pytest.raises(ValueError):setup.apply_setup(tmp_path,tmp_path/'wb',connect=True,balance=True)
    assert not load_settings(tmp_path).balance_enabled

def test_old_uninstaller_cannot_remove_new_installation(tmp_path,bridge):
    (tmp_path/'installation.json').write_text(json.dumps({'exe':str(tmp_path/'other.exe')}))
    assert setup.remove_setup(tmp_path)['state']=='not_owned'
    assert (tmp_path/'installation.json').exists()

def test_update_preserves_uninstaller_and_hashes(tmp_path):
    from workbuddy_pet.update import stage_package,prepare_install,EXE
    import zipfile,json
    installed=tmp_path/'app';installed.mkdir();(installed/EXE).write_bytes(b'MZ-old')
    (installed/'unins000.exe').write_bytes(b'MZ-uninstaller');(installed/'unins000.dat').write_bytes(b'data')
    archive=tmp_path/'update.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('WorkBuddyDesktopPet/'+EXE,b'MZ-new')
        z.writestr('WorkBuddyDesktopPet/_internal/python312.dll',b'runtime')
    stage=stage_package(archive,installed)
    assert (stage/'unins000.dat').read_bytes()==b'data'
    plan=json.loads(prepare_install(stage,installed,tmp_path/'profile').read_text(encoding='utf-8'))
    assert 'unins000.exe' in plan['files'] and 'unins000.dat' in plan['files']
