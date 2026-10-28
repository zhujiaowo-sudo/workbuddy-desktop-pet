import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path

import pytest

from workbuddy_pet.update import (Release,UpdateError,Cancelled,LATEST,RELEASES,EXE,
    version_tuple,check_latest,download_release,stage_package,prepare_install)


def release_fixture():
    name='workbuddy-desktop-pet-0.6.0-windows-x64.zip';url=RELEASES+'/download/v0.6.0/'
    data=b'synthetic package';digest=hashlib.sha256(data).hexdigest()
    value={'tag_name':'v0.6.0','draft':False,'prerelease':False,'body':'更新内容 <script> 不执行',
        'assets':[{'name':name,'browser_download_url':url+name,'size':len(data),'digest':'sha256:'+digest},
                  {'name':'SHA256SUMS.txt','browser_download_url':url+'SHA256SUMS.txt'}]}
    def opener(address):return io.BytesIO(json.dumps(value).encode() if address==LATEST else (digest+'  '+name+'\n').encode())
    return value,opener,Release('0.6.0',value['body'],url+name,name,len(data),digest),data


def test_only_newer_stable_complete_own_release():
    value,opener,expected,_=release_fixture()
    assert check_latest('0.5.1',opener)==expected
    assert check_latest('0.6.0',opener) is None
    assert version_tuple('0.10.0')>version_tuple('0.9.9')
    for key in ('draft','prerelease'):
        value[key]=True;assert check_latest('0.5.1',opener) is None;value[key]=False
    value['assets'][0]['browser_download_url']='https://evil.example/package.zip'
    with pytest.raises(UpdateError):check_latest('0.5.1',opener)
    for invalid in ('v1.0','1.0.1-beta','1.00.0','x1.0.0','1.0.1\n'):
        with pytest.raises(UpdateError):version_tuple(invalid)


def test_download_retry_progress_corruption_and_cancel(tmp_path):
    _,_,release,data=release_fixture();calls=[];progress=[]
    def flaky(url):
        calls.append(url)
        if len(calls)<3:raise OSError('synthetic network error')
        return io.BytesIO(data)
    archive=download_release(release,tmp_path,progress=lambda *v:progress.append(v),opener=flaky,wait=lambda _:None)
    assert archive.read_bytes()==data and len(calls)==3 and progress[-1]==(len(data),len(data),3)
    archive.unlink()
    with pytest.raises(UpdateError,match='3 次'):download_release(release,tmp_path,opener=lambda _:io.BytesIO(b'broken'),wait=lambda _:None)
    assert not archive.exists() and not list(tmp_path.glob('*.part'))
    with pytest.raises(Cancelled):download_release(release,tmp_path,cancel=lambda:True)


def make_archive(path,extra=None):
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('WorkBuddyDesktopPet/'+EXE,b'MZ-synthetic')
        archive.writestr('WorkBuddyDesktopPet/_internal/python312.dll',b'synthetic')
        if extra:
            name,data=extra
            if isinstance(name,str) and '\\' in name:
                entry=zipfile.ZipInfo('placeholder');entry.filename=name;name=entry
            archive.writestr(name,data)


@pytest.mark.parametrize('bad',['../outside','WorkBuddyDesktopPet/../escape','WorkBuddyDesktopPet/./x',
    'WorkBuddyDesktopPet//x','WorkBuddyDesktopPet/CON.txt','WorkBuddyDesktopPet/x:stream',
    'WorkBuddyDesktopPet/x.','WorkBuddyDesktopPet/'+EXE.upper(),'WorkBuddyDesktopPet\\x'])
def test_unsafe_archive_never_changes_installation(tmp_path,bad):
    install=tmp_path/'installed';install.mkdir();(install/EXE).write_bytes(b'MZ-old')
    archive=tmp_path/'pack.zip';make_archive(archive,(bad,b'unsafe'))
    with pytest.raises(UpdateError):stage_package(archive,install)
    assert (install/EXE).read_bytes()==b'MZ-old' and not list(tmp_path.glob('.workbuddy-update-*'))


def test_stage_plan_preserves_root_and_rejects_links(tmp_path):
    install=tmp_path/'installed';install.mkdir();(install/EXE).write_bytes(b'MZ-old')
    root=tmp_path/'profile';root.mkdir();(root/'settings.json').write_text('unchanged')
    archive=tmp_path/'pack.zip';make_archive(archive)
    stage=stage_package(archive,install)
    plan=prepare_install(stage,install,root,pid=999999,version='0.6.0')
    value=json.loads(plan.read_text())
    assert value['target']==str(install) and value['version']=='0.6.0' and len(value['files'])==2
    assert (install/EXE).read_bytes()==b'MZ-old' and (root/'settings.json').read_text()=='unchanged'
    with pytest.raises(UpdateError):prepare_install(stage,install,install/'profile')
    link=zipfile.ZipInfo('WorkBuddyDesktopPet/link');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
    make_archive(archive,(link,b'../outside'))
    with pytest.raises(UpdateError):stage_package(archive,install)
