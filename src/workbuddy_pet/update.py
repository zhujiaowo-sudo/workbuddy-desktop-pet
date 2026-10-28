"""Public release discovery and verified staging. No account credentials involved."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit

from .storage import atomic_json,plain

REPOSITORY='zhujiaowo-sudo/workbuddy-desktop-pet'
RELEASES=f'https://github.com/{REPOSITORY}/releases'
LATEST=f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
EXE='WorkBuddyDesktopPet.exe'
MAX_ZIP=160*1024*1024


class UpdateError(ValueError):pass
class Cancelled(UpdateError):pass


@dataclass(frozen=True)
class Release:
    version:str
    notes:str
    url:str
    name:str
    size:int
    sha256:str


def version_tuple(version):
    if not isinstance(version,str) or not re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)',version):
        raise UpdateError('更新版本号无效')
    return tuple(map(int,version.lstrip('v').split('.')))


def _request(url):
    return urlopen(Request(url,headers={'User-Agent':'WorkBuddyDesktopPet-Updater','Accept':'application/vnd.github+json' if url==LATEST else 'application/octet-stream'}),timeout=20)


def _read(url,limit,opener):
    with opener(url) as response:
        content=response.read(limit+1)
    if len(content)>limit:raise UpdateError('更新服务响应过大')
    return content


def check_latest(current,opener=_request):
    try:
        value=json.loads(_read(LATEST,1024*1024,opener))
        tag=value['tag_name'];version=version_tuple(tag)
        if value.get('draft') or value.get('prerelease'):return None
        if version<=version_tuple(current):return None
        if tag!='v'+'.'.join(map(str,version)):raise UpdateError('更新标签无效')
        prefix=RELEASES+'/download/'+tag+'/'
        name='workbuddy-desktop-pet-'+tag[1:]+'-windows-x64.zip'
        assets=value['assets']
        matches=[a for a in assets if a.get('name')==name]
        sums=[a for a in assets if a.get('name')=='SHA256SUMS.txt']
        if len(matches)!=1 or len(sums)!=1:raise UpdateError('新版本安装附件尚未就绪，请稍后重试')
        package=matches[0];checksum=sums[0]
        if package['browser_download_url']!=prefix+name or checksum['browser_download_url']!=prefix+'SHA256SUMS.txt':
            raise UpdateError('更新附件来源不匹配')
        if type(package['size']) is not int or not 0<package['size']<=MAX_ZIP:raise UpdateError('更新包大小无效')
        lines=_read(checksum['browser_download_url'],65536,opener).decode('utf-8-sig').splitlines()
        hashes=[m[1] for line in lines if (m:=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)) and m[2]==name]
        if len(hashes)!=1:raise UpdateError('缺少唯一的安装包 SHA-256')
        digest=package.get('digest')
        if digest and digest!='sha256:'+hashes[0]:raise UpdateError('服务器校验信息不一致')
        notes=value.get('body') or '此版本未提供更新说明。'
        return Release(tag[1:],str(notes)[:18000],prefix+name,name,package['size'],hashes[0])
    except (OSError,URLError,KeyError,TypeError,json.JSONDecodeError,UnicodeError):
        raise UpdateError('检查更新失败，请检查网络后重试') from None


def download_release(release,directory,cancel=lambda:False,progress=lambda done,total,attempt:None,opener=_request,wait=None):
    version_tuple(release.version)
    expected=f'workbuddy-desktop-pet-{release.version}-windows-x64.zip'
    if (release.name!=expected or release.url!=RELEASES+'/download/v'+release.version+'/'+expected
        or type(release.size) is not int or not 0<release.size<=MAX_ZIP or not re.fullmatch('[0-9a-f]{64}',release.sha256)):
        raise UpdateError('更新包来源或大小无效')
    directory=plain(directory);directory.mkdir(parents=True,exist_ok=True)
    target=plain(directory/release.name);partial=plain(directory/(release.name+'.part'))
    # Each retry starts clean, so no unverified partial bytes can enter the package.
    if wait is None:
        def wait(seconds):
            for _ in range(seconds*10):
                if cancel():raise Cancelled('已取消下载')
                time.sleep(.1)
    try:
        for attempt in range(1,4):
            if cancel():raise Cancelled('已取消下载')
            digest=hashlib.sha256();size=0;progress(0,release.size,attempt)
            try:
                with opener(release.url) as response,partial.open('wb') as output:
                    while block:=response.read(128*1024):
                        if cancel():raise Cancelled('已取消下载')
                        size+=len(block)
                        if size>release.size:raise UpdateError('更新包大小超出清单')
                        output.write(block);digest.update(block);progress(size,release.size,attempt)
                if size!=release.size or digest.hexdigest()!=release.sha256:raise UpdateError('更新包不完整或 SHA-256 校验失败')
                if cancel():raise Cancelled('已取消下载')
                partial.replace(target);return target
            except Cancelled:raise
            except (OSError,URLError,UpdateError):
                partial.unlink(missing_ok=True)
                if attempt==3:raise UpdateError('下载失败（已尝试 3 次），可点击重试') from None
                wait(attempt)
    finally:partial.unlink(missing_ok=True)


def stage_package(archive,install_dir,cancel=lambda:False):
    """Extract beside installation for same-volume swaps; never touch running files."""
    import zipfile
    install_dir=plain(install_dir)
    if not (install_dir/EXE).is_file():raise UpdateError('当前安装目录无效')
    work=Path(tempfile.mkdtemp(prefix='.workbuddy-update-',dir=install_dir.parent))
    stage=work/'payload';stage.mkdir()
    try:
        with zipfile.ZipFile(archive) as package:
            entries=package.infolist();seen=set();total=0
            if not 1<=len(entries)<=5000:raise UpdateError('更新包文件数量无效')
            for entry in entries:
                if cancel():raise Cancelled('已取消准备更新')
                name=entry.orig_filename;parts=PurePosixPath(name).parts
                if ('\\' in name or not parts or parts[0]!='WorkBuddyDesktopPet' or name.startswith('/')
                    or any(p in ('.','..') or ':' in p or p.endswith((' ','.')) or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',p,re.I) for p in name.rstrip('/').split('/'))
                    or '//' in name or '\x00' in name or entry.flag_bits&1 or stat.S_IFMT(entry.external_attr>>16) not in (0,stat.S_IFDIR,stat.S_IFREG)):
                    raise UpdateError('更新包包含不安全路径')
                key='/'.join(parts).casefold()
                if key in seen:raise UpdateError('更新包存在重复路径')
                seen.add(key);total+=entry.file_size
                if total>600*1024*1024:raise UpdateError('更新包解压大小超限')
                if len(parts)==1:
                    if not entry.is_dir():raise UpdateError('更新目录结构无效')
                    continue
                target=stage.joinpath(*parts[1:])
                if entry.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with package.open(entry) as source,target.open('xb') as output:
                    shutil.copyfileobj(source,output,128*1024)
        exe=stage/EXE
        if not exe.is_file() or not (stage/'_internal/python312.dll').is_file():
            raise UpdateError('更新包缺少 Windows 程序或运行库')
        with exe.open('rb') as stream:
            if stream.read(2)!=b'MZ':raise UpdateError('更新包程序格式无效')
        return stage
    except Exception:
        shutil.rmtree(work)
        raise


def prepare_install(stage,install_dir,root,*,pid=None,version='0.0.0'):
    """Create a reviewable immutable plan; subprocess starts only on restart click."""
    stage,install_dir,root=plain(stage),plain(install_dir),plain(root)
    work=stage.parent
    if work.parent!=install_dir.parent or not re.fullmatch(r'\.workbuddy-update-[\w-]+',work.name) or stage.name!='payload':
        raise UpdateError('更新暂存位置无效')
    if root==install_dir or root.is_relative_to(install_dir):raise UpdateError('用户数据位于程序目录内，请先手动更新并保留数据')
    files={}
    for path in stage.rglob('*'):
        plain(path)
        if path.is_file():
            with path.open('rb') as stream:files[path.relative_to(stage).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
    version_tuple(version)
    plan={'schema':1,'pid':pid or os.getpid(),'version':version,'target':str(install_dir),'stage':str(stage),
          'backup':str(install_dir.with_name(install_dir.name+'.previous-'+work.name.rsplit('-',1)[-1])),
          'root':str(root),'arguments':subprocess.list2cmdline(['--root',str(root)]),'files':files}
    atomic_json(work/'plan.json',plan)
    shutil.copyfile(Path(__file__).with_name('update_install.ps1'),work/'install.ps1')
    return work/'plan.json'


def launch_install(plan):
    plan=plain(plan)
    if os.name!='nt':raise UpdateError('自动安装仅支持 Windows')
    return subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass',
        '-File',str(plan.with_name('install.ps1')),'-PlanPath',str(plan)],cwd=str(plan.parent),
        creationflags=subprocess.CREATE_NO_WINDOW,close_fds=True)
