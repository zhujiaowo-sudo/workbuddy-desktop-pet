"""Explicit text-only chat providers, independent from desktop task conversations."""
from dataclasses import dataclass
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

from .storage import atomic_json


class ChatError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class ChatConfig:
    backend: str = 'workbuddy-cli'
    endpoint: str = ''
    model: str = ''
    key: str = ''


def validate_endpoint(url):
    parts = urlsplit(url)
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ChatError('接口地址不能包含账号、密码、查询参数或片段')
    if not (parts.scheme == 'https' and parts.hostname or parts.scheme == 'http' and parts.hostname in ('127.0.0.1', 'localhost', '::1')):
        raise ChatError('接口需使用 HTTPS，本机服务可以使用 HTTP')
    return url.rstrip('/') + ('/chat/completions' if not parts.path.rstrip('/').endswith('/chat/completions') else '')


def _protect(value: bytes, decrypt=False) -> bytes:
    if os.name != 'nt':
        raise ChatError('保存密钥需要 Windows 用户加密服务')
    import ctypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ChatError(f'Windows 用户加密服务不可用（错误码 {ctypes.get_last_error()}），密钥未保存')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


def save_chat_config(root, config):
    if config.backend == 'api':
        validate_endpoint(config.endpoint)
        if not config.model.strip():
            raise ChatError('请填写模型名称')
    sealed = base64.b64encode(_protect(config.key.encode())).decode() if config.key else ''
    atomic_json(Path(root)/'chat.json', {'backend':config.backend, 'endpoint':config.endpoint,
        'model':config.model, 'key_dpapi':sealed})


def load_chat_config(root):
    try:
        value = json.loads((Path(root)/'chat.json').read_text(encoding='utf-8'))
        key = _protect(base64.b64decode(value['key_dpapi']), True).decode() if value.get('key_dpapi') else ''
        return ChatConfig(value.get('backend','workbuddy-cli'), value.get('endpoint',''), value.get('model',''), key)
    except (OSError, ValueError, KeyError, TypeError):
        return ChatConfig()


def cli_command(workbuddy_path: str):
    script = Path(workbuddy_path).parent/'resources/app.asar.unpacked/cli/dist/codebuddy-lite-wb.mjs'
    if not script.is_file():
        raise ChatError('未找到 WorkBuddy 随附 CLI，请检查程序位置或配置模型接口')
    node = shutil.which('node')
    executable = node or workbuddy_path
    return [executable, str(script), '--print', '--output-format', 'json', '--tools', '',
            '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
            '--settings', '{"disableAllHooks":true}', '--setting-sources', 'user',
            '--no-session-persistence', '--max-turns', '1']


class ChatClient:
    def __init__(self):
        self.cancelled = threading.Event()
        self.process = None

    def cancel(self):
        self.cancelled.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def complete(self, config, messages, *, workbuddy_path='', home=None, cwd=None):
        self.cancelled.clear()
        if not messages or len(messages[-1]['content']) > 8000:
            raise ChatError('消息需要 1 至 8000 个字符')
        messages = [{'role':m['role'], 'content':m['content'][:8000]} for m in messages[-12:]]
        if config.backend == 'workbuddy-cli':
            reply = self._cli(messages, workbuddy_path, home, cwd)
        elif config.backend == 'api':
            reply = self._api(config, messages)
        else:
            raise ChatError('不支持的聊天通道')
        if self.cancelled.is_set():
            raise ChatError('已取消')
        return reply

    def _api(self, config, messages):
        url = validate_endpoint(config.endpoint)
        if not config.model:
            raise ChatError('请先保存聊天模型配置')
        body = json.dumps({'model':config.model, 'messages':messages, 'stream':False}, ensure_ascii=False).encode()
        headers = {'Content-Type':'application/json'}
        if config.key:
            headers['Authorization'] = 'Bearer ' + config.key
        try:
            with build_opener(NoRedirect).open(Request(url, data=body, headers=headers), timeout=25) as response:
                payload = response.read(512*1024+1)
            if len(payload) > 512*1024:
                raise ChatError('回复超过 512 KiB，请缩短对话')
            value = json.loads(payload)
            text = value['choices'][0]['message']['content']
            if not isinstance(text, str) or not text.strip():
                raise ChatError('接口未返回文本回复')
            return text[:32000]
        except HTTPError as error:
            raise ChatError(f'模型接口返回 HTTP {error.code}，请检查地址、模型和授权') from None
        except (URLError, OSError, ValueError, KeyError, IndexError, TypeError) as error:
            if isinstance(error, ChatError):
                raise
            raise ChatError('模型接口不可用、超时或回复格式不兼容') from None

    def _cli(self, messages, executable, home, cwd):
        command = cli_command(executable)
        env = dict(os.environ, WORKBUDDY_CONFIG_DIR=str(home), CODEBUDDY_CONFIG_DIR=str(home),
                   CODEBUDDY_SKIP_GIT_BASH_CHECK='1', CODEBUDDY_DISABLE_IDE='1')
        if command[0] == executable:
            env['ELECTRON_RUN_AS_NODE'] = '1'
        prompt = '\n\n'.join(m['role']+': '+m['content'] for m in messages)
        try:
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=cwd, env=env, creationflags=0x08000000 if os.name == 'nt' else 0)
            stdout, _ = self.process.communicate(prompt.encode('utf-8'), timeout=40)
            if self.cancelled.is_set():
                raise ChatError('已取消')
            if len(stdout) > 512*1024:
                raise ChatError('CLI 回复超过上限')
            try:
                value = json.loads(stdout)
                reply = value.get('result')
                if value.get('is_error') or not isinstance(reply, str) or not reply.strip():
                    raise ValueError()
                return reply[:32000]
            except (ValueError, TypeError, AttributeError):
                raise ChatError('WorkBuddy CLI 未返回可用回复，可能需要单独授权；可配置模型接口，或打开 WorkBuddy 对话') from None
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate()
            raise ChatError('WorkBuddy CLI 请求超时') from None
        except OSError:
            raise ChatError('无法启动 WorkBuddy CLI，请检查安装位置') from None
        finally:
            self.process = None
