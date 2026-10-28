"""Exercise the actual PowerShell installer using synthetic tiny applications."""
import json
import os
from pathlib import Path
import subprocess
import time

import pytest

from workbuddy_pet.update import EXE,prepare_install

pytestmark=pytest.mark.skipif(os.name!='nt',reason='Windows transaction helper')


def compile_app(destination,version,tmp_path):
    source=tmp_path/('app-'+version+'.cs')
    source.write_text('''using System; using System.IO; using System.Threading;
class App { static void Main(string[] args) {
    if(args.Length<2) return;
    string value="{\\"version\\":\\"VERSION\\",\\"at\\":"+DateTimeOffset.UtcNow.ToUnixTimeSeconds()+",\\"pid\\":"+System.Diagnostics.Process.GetCurrentProcess().Id+"}";
    File.WriteAllText(Path.Combine(args[1],"runtime.json"),value);
    Thread.Sleep(1200);
} }'''.replace('VERSION',version),encoding='utf-8')
    script=tmp_path/('compile-'+version+'.ps1')
    # Literal paths are parameters, never interpolated into executable shell text.
    script.write_text("param($SourcePath,$OutputPath)\nAdd-Type -Path $SourcePath -OutputAssembly $OutputPath -OutputType WindowsApplication\n",encoding='utf-8')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),str(source),str(destination)],capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr.decode(errors='replace')


@pytest.mark.parametrize('broken',[False,True])
def test_native_directory_swap_and_rollback_preserve_profile(tmp_path,broken):
    install=tmp_path/'installation';install.mkdir()
    root=tmp_path/'profile with spaces';root.mkdir();(root/'settings.json').write_text('synthetic settings')
    (root/'characters').mkdir();(root/'characters/keep.txt').write_text('synthetic asset')
    compile_app(install/EXE,'0.5.1',tmp_path)
    (install/'old-marker.txt').write_text('old')
    work=tmp_path/'.workbuddy-update-synthetic';stage=work/'payload';stage.mkdir(parents=True)
    if broken:(stage/EXE).write_bytes(b'MZ-invalid executable')
    else:compile_app(stage/EXE,'9.9.9',tmp_path)
    (stage/'new-marker.txt').write_text('new')
    plan=prepare_install(stage,install,root,pid=999999,version='9.9.9')
    helper=work/'install.ps1'
    helper.write_text(helper.read_text(encoding='utf-8').replace('} catch {\n    try {','} catch {\n    Write-Output $_.Exception.ToString()\n    try {'),encoding='utf-8')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(work/'install.ps1'),'-PlanPath',str(plan)],capture_output=True,timeout=40)
    state=json.loads((root/'update-result.json').read_text(encoding='utf-8-sig'))['state']
    assert state==('failed' if broken else 'success'),(state,result.stdout.decode(errors='replace'),result.stderr)
    assert result.returncode==(1 if broken else 0)
    assert (install/('old-marker.txt' if broken else 'new-marker.txt')).is_file()
    assert (root/'settings.json').read_text()=='synthetic settings' and (root/'characters/keep.txt').read_text()=='synthetic asset'
    if not broken:assert list(tmp_path.glob('installation.previous-*'))
    time.sleep(1.3)  # Let the synthetic restarted executable release its test directory.
