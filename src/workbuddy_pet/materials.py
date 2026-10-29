"""Local, data-only character packs; no scripts or third-party assets."""
from dataclasses import dataclass, replace
from collections import OrderedDict
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import threading
import warnings
import zipfile

from PIL import Image, UnidentifiedImageError

STATES = ('idle', 'thinking', 'working', 'waiting', 'review', 'done', 'failed')
TASK_ACTIONS = STATES
CLICK_ACTIONS = ('click_wave', 'click_heart', 'click_shy', 'click_surprised')
LEISURE_ACTIONS = ('leisure_snack', 'leisure_phone', 'leisure_stretch', 'leisure_music')
ALL_ACTIONS = STATES + CLICK_ACTIONS + LEISURE_ACTIONS
OPTIONAL_IDLE_ACTIONS = ('idle_scratch',)
LOOP_ACTIONS = frozenset(STATES[:5] + LEISURE_ACTIONS)
FALLBACKS = dict(zip(CLICK_ACTIONS + LEISURE_ACTIONS,
                     ('done', 'waiting', 'waiting', 'review', 'idle', 'thinking', 'done', 'idle')))
MAX_BYTES = 128 * 1024 * 1024
MAX_PIXELS = 64_000_000
MAX_HD_PACK_PIXELS = 72_000_000
MAX_LONG_BYTES = 512 * 1024 * 1024
MAX_LONG_PIXELS = 2_000_000_000
_VISIBLE_ALPHA = [0]*17+[255]*239


def alpha_bounds(image):
    """Ignore hidden RGB and nearly invisible edge noise; right/bottom are exclusive."""
    return image.getchannel('A').point(_VISIBLE_ALPHA).getbbox()


class MaterialError(ValueError):
    pass


def safe_name(name):
    if not isinstance(name, str) or not name or len(name) > 240 or any(c in name for c in '\\:<>"|?*'):
        raise MaterialError('素材路径无效')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('', '.', '..') or p.endswith((' ', '.')) or
        re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', p.split('.')[0], re.I) or
        any(ord(c) < 32 for c in p) for p in name.split('/')):
        raise MaterialError('素材路径无效')
    if path.suffix.lower() not in ('.json', '.png', '.gif', '.webp'):
        raise MaterialError('角色包仅支持 JSON、PNG、GIF 和 WebP')
    return path


def checked(root: Path, name: str):
    path = root.joinpath(*safe_name(name).parts)
    for ancestor in (path, *path.parents):
        if ancestor == root.parent:
            break
        if ancestor.is_symlink() or ancestor.is_junction():
            raise MaterialError('素材路径不能包含链接或目录联接')
    if not path.resolve().is_relative_to(root.resolve()):
        raise MaterialError('素材路径超出角色目录')
    return path


@dataclass(frozen=True)
class Frame:
    size: tuple[int, int]
    rgba: bytes
    duration: int
    bounds: tuple[int,int,int,int] | None = None


def iter_animation(path: Path, *, long=False):
    pixels = 0
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if image.format not in ('PNG', 'GIF', 'WEBP') or max(image.size) > 1024 or image.n_frames > 300:
                    raise MaterialError('素材上限为 1024px、300 帧')
                for index in range(image.n_frames):
                    image.seek(index)
                    pixels += image.width * image.height
                    if pixels > (125_000_000 if long else MAX_PIXELS):
                        raise MaterialError('单段动画解码体积过大，请减少帧数或尺寸')
                    rgba = image.convert('RGBA')
                    delay = image.info.get('duration', 100)
                    if long and (type(delay) not in (int, float) or not math.isfinite(delay) or not 20 <= delay <= 500):
                        raise MaterialError('长动画每帧时长须为20–500ms')
                    if not isinstance(delay, (int, float)):
                        delay = 100
                    yield Frame(rgba.size, rgba.tobytes(), max(20, min(10000, int(delay))),alpha_bounds(rgba))
    except (OSError, ValueError, EOFError, Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        if isinstance(error, MaterialError):
            raise
        raise MaterialError('素材不能完整解码：' + path.name) from None
def decode_animation(path: Path) -> tuple[Frame, ...]:
    return tuple(iter_animation(path))


@dataclass(frozen=True)
class Action:
    file: str
    loop: bool = True
    loop_range: tuple[int, int] | None = None


@dataclass(frozen=True)
class CharacterPack:
    key: str
    root: Path
    name: str
    author: str
    quality: str
    license: str
    actions: dict[str, Action]
    schema: int = 1
    anchor: tuple[int, int, int, int] | None = None

    def action(self, state: str) -> Action:
        return self.actions.get(state, self.actions.get(FALLBACKS.get(state, ''), self.actions['idle']))


_PACK_CACHE = OrderedDict()
_CACHE_LOCK = threading.Lock()


def _pack_signature(root):
    manifest = checked(root, 'manifest.json')
    if manifest.stat().st_size > 65536:
        raise MaterialError('角色清单超过 64 KiB')
    data = json.loads(manifest.read_text(encoding='utf-8-sig'))
    names = {'manifest.json'}
    names.update(item['file'] for item in data['actions'].values())
    result = []
    for name in sorted(names):
        path = checked(root, name)
        stat = path.stat()
        result.append((name, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))
    return tuple(result)


def validate_pack(root: Path, *, decode=True, key='', force=False) -> CharacterPack:
    """Cache successful metadata/hash validation; never cache full import decoding."""
    root = Path(root).absolute()
    if decode:
        with _CACHE_LOCK:
            _PACK_CACHE.pop(root, None)
        return _validate_pack(root, decode=True, key=key)
    try:
        signature = _pack_signature(root)
        with _CACHE_LOCK:
            cached = _PACK_CACHE.get(root)
            if not force and cached and cached[0] == signature:
                _PACK_CACHE.move_to_end(root)
                return replace(cached[1], key=key, actions=dict(cached[1].actions))
        pack = _validate_pack(root, decode=False, key=key)
        if _pack_signature(root) != signature:
            raise MaterialError('校验时素材发生变化，请重试')
        with _CACHE_LOCK:
            _PACK_CACHE[root] = (signature, pack)
            _PACK_CACHE.move_to_end(root)
            while len(_PACK_CACHE) > 64:
                _PACK_CACHE.popitem(last=False)
        return replace(pack, actions=dict(pack.actions))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        with _CACHE_LOCK:
            _PACK_CACHE.pop(root, None)
        raise MaterialError('角色清单损坏、素材缺失或校验失败') from None


def _validate_pack(root: Path, *, decode=True, key='') -> CharacterPack:
    manifest_path = checked(root, 'manifest.json')
    try:
        if manifest_path.stat().st_size > 65536:
            raise MaterialError('角色清单超过 64 KiB')
        data = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or type(data.get('schema')) is not int or data.get('schema') not in (1, 2, 3):
            raise MaterialError('不支持的素材包版本，需要 schema=1、2 或 3')
        schema = data['schema']
        if schema >= 2 and 'quality' not in data:
            raise MaterialError('完整互动包须明确指定 quality=light 或 hd')
        for field in ('id', 'name', 'author', 'version', 'license'):
            if not isinstance(data.get(field), str) or not 1 <= len(data[field]) <= 200:
                raise MaterialError('角色清单缺少有效字段：' + field)
        quality = data.get('quality', 'light')
        actions = data.get('actions')
        if quality not in ('light', 'hd') or not isinstance(actions, dict) or 'idle' not in actions:
            raise MaterialError('角色包需要 idle 待机动作，以及 light/hd 画质')
        if schema >= 2 and (not set(ALL_ACTIONS)<=set(actions) or not set(actions)<=set(ALL_ACTIONS+OPTIONAL_IDLE_ACTIONS)):
            raise MaterialError('完整互动包需要15个规定动作，只可额外提供可选idle_scratch')
        anchor = data.get('anchor') if schema >= 2 else None
        if schema == 3 and anchor is None:
            raise MaterialError('长动画包需要统一可见包络 anchor')
        if anchor is not None:
            resolution = (512 if quality == 'light' else 720) if schema == 3 else (256 if quality == 'light' else 512)
            if (not isinstance(anchor, list) or len(anchor) != 4 or any(type(n) is not int for n in anchor)
                or not 0 <= anchor[0] < anchor[2] <= resolution or not 0 <= anchor[1] < anchor[3] <= resolution):
                raise MaterialError('统一可见包络 anchor 无效')
            anchor = tuple(anchor)
        hashes = data.get('files', {})
        if not isinstance(hashes, dict):
            raise MaterialError('文件校验清单无效')
        parsed, seen, pixel_count = {}, set(), 0
        for state, item in actions.items():
            if state not in (ALL_ACTIONS+OPTIONAL_IDLE_ACTIONS if schema >= 2 else STATES) or not isinstance(item, dict) or type(item.get('loop', True)) is not bool:
                raise MaterialError('动作名称或循环设置无效')
            name = item.get('file')
            path = checked(root, name)
            if path.suffix.lower() not in ('.png', '.gif', '.webp'):
                raise MaterialError('动作需要 PNG、GIF 或 WebP')
            if schema >= 2:
                if name not in tuple(f'actions/{state}{ext}' for ext in ('.webp', '.png', '.gif')):
                    raise MaterialError('完整互动包文件须命名为 actions/<动作标识>.webp、.png 或 .gif')
                if item.get('loop') is not (state in LOOP_ACTIONS):
                    raise MaterialError('完整互动包循环设置不符合动作规范：' + state)
            if name in hashes:
                with path.open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != hashes[name]:
                        raise MaterialError('素材 SHA-256 校验失败')
            loop_range = item.get('loop_range')
            if loop_range is not None:
                if (schema != 3 or not item.get('loop') or not isinstance(loop_range,list) or len(loop_range)!=2
                    or any(type(n) is not int for n in loop_range) or not 0 < loop_range[0] < loop_range[1] < 240):
                    raise MaterialError('loop_range须为schema3循环动作的有效中段[起始帧,结束帧)，且保留进入及退出段')
                loop_range=tuple(loop_range)
            if schema == 3 and path.stat().st_size > 64 * 1024 * 1024:
                raise MaterialError('长动画单文件不得超过64MiB')
            if decode and name not in seen:
                count = elapsed = 0
                for frame in iter_animation(path, long=schema == 3):
                    count += 1
                    elapsed += frame.duration
                    if schema >= 2:
                        resolution = (512 if quality == 'light' else 720) if schema == 3 else (256 if quality == 'light' else 512)
                        if frame.size != (resolution, resolution):
                            raise MaterialError(f'完整互动包所有帧须为{resolution}×{resolution}：' + state)
                        if not (20 if schema == 3 else 40) <= frame.duration <= (500 if schema == 3 else 200):
                            raise MaterialError('完整互动包每帧时长超出规范：' + state)
                        if frame.bounds is None or min(frame.rgba[3::4]) == 255:
                            raise MaterialError('完整互动包每帧须有可见角色及透明背景：' + state)
                        if anchor and (frame.bounds[0] < anchor[0] or frame.bounds[1] < anchor[1] or
                                       frame.bounds[2] > anchor[2] or frame.bounds[3] > anchor[3]):
                            raise MaterialError('统一可见包络 anchor 未包含全部动作：' + state)
                    pixel_count += frame.size[0] * frame.size[1]
                    limit = MAX_LONG_PIXELS if schema == 3 else (MAX_HD_PACK_PIXELS if schema == 2 and quality == 'hd' else MAX_PIXELS)
                    if pixel_count > limit:
                        raise MaterialError('整套角色的解码体积超过上限，请拆分画质或减少帧数')
                if schema >= 2 and not 8 <= count <= (240 if schema == 3 else 16):
                    raise MaterialError('完整互动包每段需要8–240帧' if schema == 3 else '完整互动包每段需要8–16帧')
                if loop_range and loop_range[1]>=count:
                    raise MaterialError('loop_range必须在末尾保留退出帧')
                if schema == 3 and elapsed > 12000:
                    raise MaterialError('长动画每段不得超过12秒')
                seen.add(name)
            parsed[state] = Action(name, item.get('loop', True),loop_range)
        return CharacterPack(key, root, data['name'], data['author'], quality, data['license'], parsed, schema, anchor)
    except (OSError, ValueError, TypeError, KeyError) as error:
        if isinstance(error, MaterialError):
            raise
        raise MaterialError('角色清单损坏或缺少素材') from None


class MaterialLibrary:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()

    def _root(self):
        if any(p.is_symlink() or p.is_junction() for p in (self.root, *self.root.parents)):
            raise MaterialError('角色库不能使用链接目录')
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root.resolve()

    def load(self, key: str, *, force=False):
        if not isinstance(key, str) or not re.fullmatch('[0-9a-f]{32}', key):
            raise MaterialError('角色库标识无效')
        root = self._root()
        target = root / key
        if target.is_symlink() or target.is_junction():
            raise MaterialError('角色库目录无效')
        return validate_pack(target, decode=False, key=key, force=force)

    def list_packs(self):
        result = []
        for path in self._root().iterdir():
            if path.is_dir() and re.fullmatch('[0-9a-f]{32}', path.name):
                try:
                    result.append(self.load(path.name))
                except MaterialError:
                    continue
        return sorted(result, key=lambda p: (p.name, p.quality))

    def import_pack(self, source: Path):
        root = self._root()
        source = Path(source)
        with tempfile.TemporaryDirectory(prefix='stage-', dir=root) as temporary:
            stage = Path(temporary)
            names, total = set(), 0

            def write(name, size, stream):
                nonlocal total
                path = checked(stage, name)
                folded = name.casefold()
                total += size
                if folded in names or len(names) >= 64 or size < 0 or total > MAX_LONG_BYTES:
                    raise MaterialError('角色包重复文件、数量过多或超过 512 MiB')
                names.add(folded)
                path.parent.mkdir(parents=True, exist_ok=True)
                count = 0
                with path.open('wb') as output:
                    while block := stream.read(128 * 1024):
                        count += len(block)
                        if count > size:
                            raise MaterialError('素材实际体积超出清单')
                        output.write(block)
                if count != size:
                    raise MaterialError('素材文件不完整')

            try:
                if source.is_dir():
                    for path in source.rglob('*'):
                        if path.is_symlink() or path.is_junction():
                            raise MaterialError('角色包不能包含链接')
                        if path.is_file():
                            with path.open('rb') as stream:
                                write(path.relative_to(source).as_posix(), path.stat().st_size, stream)
                else:
                    if source.stat().st_size > MAX_LONG_BYTES:
                        raise MaterialError('ZIP 超过 512 MiB')
                    with zipfile.ZipFile(source) as archive:
                        if len(archive.infolist()) > 128:
                            raise MaterialError('ZIP 条目过多')
                        for info in archive.infolist():
                            if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                                raise MaterialError('ZIP 不能包含链接或加密文件')
                            if info.is_dir():
                                safe_name(info.filename.rstrip('/') + '/placeholder.png')
                                continue
                            with archive.open(info) as stream:
                                write(info.filename, info.file_size, stream)
                staged = validate_pack(stage)
                if staged.schema < 3 and total > MAX_BYTES:
                    raise MaterialError('旧格式角色包超过 128 MiB')
                digest = hashlib.sha256()
                for name in sorted(names):
                    digest.update(name.encode('utf-8'))
                    with checked(stage, name).open('rb') as stream:
                        digest.update(hashlib.file_digest(stream, 'sha256').digest())
                key = digest.hexdigest()[:32]
                target = root / key
                if not target.exists():
                    stage.rename(target)
                    stage.mkdir()  # TemporaryDirectory cleans only its empty staging path.
                return self.load(key)
            except (OSError, zipfile.BadZipFile, RuntimeError) as error:
                raise MaterialError('导入失败：素材文件或 ZIP 无效') from None

    def remove(self, key: str):
        pack = self.load(key)
        root = self._root()
        target = pack.root.resolve()
        if target.parent != root or not re.fullmatch('[0-9a-f]{32}', target.name):
            raise MaterialError('拒绝删除角色库以外的目录')
        # Verify the final absolute target immediately before recursive removal.
        if any(p.is_symlink() or p.is_junction() for p in target.rglob('*')):
            raise MaterialError('角色目录已发生链接变化，未删除')
        shutil.rmtree(target)
