"""Exercise frozen stdin collection, safe shell arguments, and GUI startup."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument('--interactive-pack',type=Path,help='额外验证完整15动作素材的冻结导入和播放')
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project / "src"))
    from workbuddy_pet.integration import powershell_command
    exe = project / "dist/WorkBuddyDesktopPet/WorkBuddyDesktopPet.exe"
    root = args.scratch.absolute() / ("verify-" + uuid.uuid4().hex)
    payload = json.dumps({"session_id": "synthetic-packaged-test", "prompt": "NEVER-WRITE-THIS"}).encode()
    result = subprocess.run([str(exe), "--root", str(root), "--hook", "UserPromptSubmit"],
                            input=payload, capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stdout, "Frozen collector failed"
    files = list((root / "events").glob("*.jsonl"))
    assert len(files) == 1 and b"NEVER-WRITE-THIS" not in files[0].read_bytes()
    # Real PowerShell stdin forwarding, including apostrophes and spaces in paths.
    shell_root = root / "spaces and ' quote"
    command = powershell_command([str(exe), "--root", str(shell_root), "--hook", "Stop"])
    result = subprocess.run(command.split(), input=payload, capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stdout
    assert list((shell_root / "events").glob("*.jsonl")), "PowerShell lost stdin or literal arguments"
    result=subprocess.run([str(exe),'--root',str(root/'materials'),'--import-pet',str(project/'examples/starter-pet')],capture_output=True,timeout=20)
    assert result.returncode==0 and list((root/'materials/characters').glob('*/manifest.json')), 'Frozen material decoder/import failed'
    if args.interactive_pack:
        full_root=root/'interactive'
        result=subprocess.run([str(exe),'--root',str(full_root),'--import-pet',str(args.interactive_pack.absolute())],capture_output=True,timeout=45)
        assert result.returncode==0,'Frozen complete pack import failed'
        pack_root=next((full_root/'characters').glob('*/manifest.json')).parent
        from workbuddy_pet.settings import Settings,save_settings
        save_settings(full_root,Settings(character=pack_root.name,size=224,compact=True,notifications=False))
        result=subprocess.run([str(exe),'--root',str(full_root),'--demo','--smoke-seconds','2',
            '--workbuddy-home',str(root/'absent-workbuddy'),'--capture-page','interaction',
            '--capture',str(root/'preview-interactive.png')],env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),capture_output=True,timeout=25)
        assert result.returncode==0,'Frozen complete animation startup failed'
        runtime=json.loads((full_root/'runtime.json').read_text(encoding='utf-8'))
        assert runtime['animation_loaded'] and runtime['visual_action']=='click_wave' and runtime['capsule_gap']==8
        assert runtime['checkin_state']=='disabled'
    assert (exe.parent/'_internal/workbuddy_pet/catalog.json').is_file(),'Optional material catalog missing'
    assert (exe.parent/'_internal/workbuddy_pet/assets/mint-orbit-idle.png').is_file(),'Default portrait missing'
    assert (exe.parent/'_internal/workbuddy_pet/update_install.ps1').is_file(),'Update installer missing'
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    from workbuddy_pet import __version__
    for page,mode,card_only in (('summary','summary',True),('capsule','capsule',True),('data','expanded',True),
                               ('capsule','capsule',False),('interaction','capsule',False)):
        suffix=page+('-card' if card_only else '-pet')
        gui_root=root/('gui-'+suffix)
        result = subprocess.run([str(exe), "--root", str(gui_root), "--demo", "--smoke-seconds", "2",
                                 '--workbuddy-home',str(root/'absent-workbuddy'),*(['--card-only'] if card_only else []),
                                 '--capture-page',page,'--capture',str(root/('preview-'+suffix+'.png'))],
                                env=env,capture_output=True,timeout=20)
        assert result.returncode == 0, f"Frozen GUI failed: exit={result.returncode}, stderr={result.stderr[-2000:]!r}"
        runtime = json.loads((gui_root / "runtime.json").read_text(encoding="utf-8"))
        assert runtime["demo"] is True and runtime["version"] == __version__
        assert runtime['card_only']==card_only and runtime['visible'] is True and runtime['view_mode']==mode
        if not card_only:assert runtime['panel_gap']==8,'Frozen panel does not follow the visible portrait'
        if page=='interaction':assert runtime['interacting'] is True,'Frozen interaction was not activated'
        assert runtime['checkin_state']=='disabled','Packaged demo must never query or claim check-in'
        assert runtime['chat_behavior']=='open-workbuddy','Chat must only open WorkBuddy'
        assert (root/('preview-'+suffix+'.png')).is_file()
    print(json.dumps({"frozen_collector": True, "powershell_stdin": True, "frozen_gui": True,'frozen_material_import':True,'card_only':True,
                      'three_views':True,'visible_docking':True,'interaction':True,'checkin_disabled_by_default':True,"captures": str(root)}, indent=2))


if __name__ == "__main__":
    main()
