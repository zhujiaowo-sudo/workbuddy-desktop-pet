"""Exercise the actual installer with synthetic profiles, without touching a real pet."""
import argparse,json,subprocess,sys,uuid,winreg
from pathlib import Path

KEY=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{0748246D-1B81-4CDB-A9BA-00D241D20B51}_is1'
def registered():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,KEY):return True
    except FileNotFoundError:return False

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--installer',type=Path,required=True)
    parser.add_argument('--scratch',type=Path,required=True)
    args=parser.parse_args()
    if registered():raise SystemExit('Existing per-user installer registration found; refusing to overwrite it')
    base=args.scratch.resolve()/('verify-'+uuid.uuid4().hex);base.mkdir(parents=True)
    target=base/'app';root=base/'profile';home=base/'workbuddy';home.mkdir()
    fake=base/'WorkBuddy.exe';fake.write_bytes(b'MZ-synthetic-fixture-never-executed')
    fixture={'enabledPlugins':{'other@fixture':True},'test_setting':'preserve'}
    (home/'settings.json').write_text(json.dumps(fixture),encoding='utf-8')
    command=[str(args.installer.resolve()),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS',
             '/DIR='+str(target),'/PETROOT='+str(root),'/WORKBUDDYHOME='+str(home),'/WORKBUDDYEXE='+str(fake),
             r'/TASKS=connect,connect\balance']
    uninstall=target/'unins000.exe'
    try:
        subprocess.run([*command,'/LOG='+str(base/'install.log')],check=True,timeout=180)
        assert registered() and uninstall.is_file()
        result=json.loads((root/'setup-result.json').read_text(encoding='utf-8'));assert result['state']=='configured',result
        settings=json.loads((root/'settings.json').read_text(encoding='utf-8'))
        assert settings['balance_enabled'] and not settings['checkin_enabled'] and not settings['startup']
        assert (root/'integration-receipt.json').is_file()
        settings.update(character='builtin-blue-fish',minimal=True,balance_enabled=False,checkin_enabled=True)
        (root/'settings.json').write_text(json.dumps(settings),encoding='utf-8')
        material=root/'characters'/'fixture.txt';material.parent.mkdir();material.write_text('preserve')
        subprocess.run([*command,'/LOG='+str(base/'upgrade.log')],check=True,timeout=180)
        assert json.loads((root/'settings.json').read_text(encoding='utf-8'))==settings
        assert json.loads((root/'setup-result.json').read_text(encoding='utf-8'))['state']=='preserved'
        assert material.read_text()=='preserve'
    finally:
        if uninstall.is_file():
            subprocess.run([str(uninstall),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/LOG='+str(base/'uninstall.log')],check=True,timeout=90)
    assert not registered() and not (target/'WorkBuddyDesktopPet.exe').exists()
    assert material.read_text()=='preserve' and (root/'settings.json').exists()
    assert not (root/'integration-receipt.json').exists()
    assert json.loads((home/'settings.json').read_text(encoding='utf-8'))['enabledPlugins']==fixture['enabledPlugins']
    assert json.loads((root/'setup-result.json').read_text(encoding='utf-8'))['state']=='removed'
    print(json.dumps({'installer_install_upgrade_uninstall':'passed','synthetic_profile':str(base),
                      'consent_preserved':True,'other_plugins_preserved':True,'user_materials_preserved':True}))
if __name__=='__main__':main()
