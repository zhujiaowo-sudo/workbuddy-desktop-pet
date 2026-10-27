import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import pytest
from workbuddy_pet.chat import ChatClient, ChatConfig, ChatError, cli_command, validate_endpoint


def test_local_api_text_contract_and_error():
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            body=json.dumps({'choices':[{'message':{'content':'连接成功'}}]}).encode()
            self.send_response(200);self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        client=ChatClient()
        config=ChatConfig('api',f'http://127.0.0.1:{server.server_port}/v1','test')
        assert client.complete(config,[{'role':'user','content':'测试'}])=='连接成功'
        assert 'tools' not in received[0] and received[0]['stream'] is False
    finally:server.shutdown();server.server_close()
    with pytest.raises(ChatError):validate_endpoint('http://remote.example/v1')
    with pytest.raises(ChatError):validate_endpoint('https://user:secret@example.test/v1')


def test_cli_never_bypasses_permissions_or_enables_tools(tmp_path):
    script=tmp_path/'resources/app.asar.unpacked/cli/dist/codebuddy-lite-wb.mjs'
    script.parent.mkdir(parents=True);script.touch()
    command=cli_command(str(tmp_path/'WorkBuddy.exe'))
    assert command[command.index('--tools')+1]==''
    assert '--dangerously-skip-permissions' not in command and '--resume' not in command
    assert 'disableAllHooks' in ' '.join(command)


def test_windows_key_is_encrypted_and_local_no_key_config(tmp_path):
    import os
    from workbuddy_pet.chat import save_chat_config,load_chat_config
    config=ChatConfig('api','http://127.0.0.1:8080/v1','synthetic')
    save_chat_config(tmp_path,config)
    assert load_chat_config(tmp_path)==config
    if os.name=='nt':
        sealed=ChatConfig('api','https://example.invalid/v1','synthetic','synthetic-secret-never-plain')
        save_chat_config(tmp_path,sealed)
        assert 'synthetic-secret-never-plain' not in (tmp_path/'chat.json').read_text()
        assert load_chat_config(tmp_path)==sealed
