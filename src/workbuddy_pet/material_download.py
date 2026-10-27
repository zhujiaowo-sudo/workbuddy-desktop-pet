"""Only download project-owned, digest-pinned optional example packs."""
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from .materials import MaterialError


def download_default(quality, library, cancel=lambda:False):
    catalog=json.loads(Path(__file__).with_name('catalog.json').read_text(encoding='utf-8'))
    spec=catalog['packs'][quality]
    prefix='https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/download/v0.2.0/'
    if not spec['url']==prefix+spec['name'] or not 0<spec['bytes']<128*1024*1024:
        raise MaterialError('默认素材下载清单无效')
    with tempfile.TemporaryDirectory(prefix='download-',dir=library._root()) as temporary:
        target=Path(temporary)/'pack.zip';digest=hashlib.sha256();size=0
        try:
            with urlopen(spec['url'],timeout=25) as response,target.open('wb') as output:
                while block:=response.read(128*1024):
                    if cancel():raise MaterialError('已取消下载')
                    size+=len(block)
                    if size>spec['bytes']:raise MaterialError('下载大小超出清单')
                    digest.update(block);output.write(block)
        except HTTPError as error:
            raise MaterialError('这套默认素材尚未发布，请先导入本地包或使用内置角色' if error.code==404 else '素材下载服务暂不可用') from None
        except (OSError,URLError):
            raise MaterialError('素材下载连接失败，请稍后重试') from None
        if size!=spec['bytes'] or digest.hexdigest()!=spec['sha256']:
            raise MaterialError('下载不完整或 SHA-256 不匹配')
        if cancel():raise MaterialError('已取消下载')
        return library.import_pack(target)
