"""Mutually authenticated local relay, restricted to three fixed request purposes."""
import base64,hashlib,hmac,json,os,re,secrets,struct,time
from pathlib import Path
from . import __version__

PIPE_PREFIX='\\\\.\\pipe\\wbipc-'
MAX_FRAME=1024*1024
_PURPOSE_PATHS={
    'balance':'/billing/meter/get-user-resource-summary',
    'checkin_status':'/v2/billing/meter/checkin-activity-status',
    'checkin_claim':'/v2/billing/meter/daily-checkin',
}

class RelayError(ValueError):pass

def _proof(ticket,role,endpoint,client_nonce,server_nonce):
    fields=('wbipc-s' if role=='server' else 'wbipc-c','1',endpoint,client_nonce,server_nonce)
    transcript=b''.join(struct.pack('>I',len(raw))+raw for raw in (field.encode() for field in fields))
    return base64.urlsafe_b64encode(hmac.new(ticket.encode(),transcript,hashlib.sha256).digest()).decode().rstrip('=')


class _NamedPipe:
    """Bounded synchronous Windows pipe I/O, used only on a background worker."""
    def __init__(self,endpoint,timeout=15):
        if os.name!='nt':raise RelayError('余额连接需要 Windows')
        import ctypes
        from ctypes import wintypes
        self.ctypes=ctypes;self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        self.kernel.CreateFileW.restype=wintypes.HANDLE
        self.kernel.WaitNamedPipeW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD]
        self.kernel.PeekNamedPipe.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
        self.kernel.ReadFile.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
        self.kernel.WriteFile.argtypes=self.kernel.ReadFile.argtypes
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.deadline=time.monotonic()+timeout;self.buffer=b''
        self.handle=self.kernel.CreateFileW(endpoint,0xC0000000,0,None,3,0,None)
        if self.handle==ctypes.c_void_p(-1).value:
            if ctypes.get_last_error()==231:
                self.kernel.WaitNamedPipeW(endpoint,1000)
                self.handle=self.kernel.CreateFileW(endpoint,0xC0000000,0,None,3,0,None)
            if self.handle==ctypes.c_void_p(-1).value:raise RelayError('WorkBuddy 本地连接未就绪')

    def send(self,value):
        raw=json.dumps(value,separators=(',',':')).encode()+b'\n'
        count=self.ctypes.c_ulong();buffer=self.ctypes.create_string_buffer(raw)
        if not self.kernel.WriteFile(self.handle,buffer,len(raw),self.ctypes.byref(count),None) or count.value!=len(raw):
            raise RelayError('余额连接已中断')

    def receive(self):
        while b'\n' not in self.buffer:
            if time.monotonic()>self.deadline:raise RelayError('余额查询超时')
            available=self.ctypes.c_ulong()
            if not self.kernel.PeekNamedPipe(self.handle,None,0,None,self.ctypes.byref(available),None):raise RelayError('WorkBuddy 余额连接已关闭')
            if available.value:
                size=min(available.value,65536)
                block=self.ctypes.create_string_buffer(size);count=self.ctypes.c_ulong()
                if not self.kernel.ReadFile(self.handle,block,size,self.ctypes.byref(count),None):raise RelayError('余额连接读取失败')
                self.buffer+=block.raw[:count.value]
                if len(self.buffer)>MAX_FRAME:raise RelayError('余额响应超过上限')
            else:time.sleep(.01)
        line,self.buffer=self.buffer.split(b'\n',1)
        try:value=json.loads(line)
        except (ValueError,RecursionError):raise RelayError('余额连接返回无效数据') from None
        if not isinstance(value,dict):raise RelayError('余额响应无效')
        return value

    def close(self):
        self.kernel.CloseHandle(self.handle)
        self.buffer=b''


def request_json(home: Path,purpose: str,transport_factory=_NamedPipe):
    if not isinstance(purpose,str) or purpose not in _PURPOSE_PATHS:
        raise RelayError('Unsupported WorkBuddy request purpose')
    path=_PURPOSE_PATHS[purpose]
    discovery=Path(home)/'wbipc/endpoint.json'
    if discovery.is_symlink() or discovery.stat().st_size>4096:raise RelayError('本地连接配置无效')
    data=json.loads(discovery.read_text(encoding='utf-8'))
    endpoint,ticket=data.get('endpoint'),data.get('ticket')
    if not isinstance(endpoint,str) or not endpoint.startswith(PIPE_PREFIX) or not re.fullmatch('[A-Za-z0-9_-]{8,128}',endpoint[len(PIPE_PREFIX):]):
        raise RelayError('余额仅支持本机 WorkBuddy 管道')
    if not isinstance(ticket,str) or not re.fullmatch('[A-Za-z0-9_-]{16,256}',ticket):raise RelayError('本地连接认证配置无效')
    pipe=transport_factory(endpoint)
    try:
        nonce=secrets.token_urlsafe(16)
        pipe.send({'type':'session_hello','protocol_min':1,'protocol_max':1,'client_nonce':nonce,
            'ticket_id':hashlib.sha256(ticket.encode()).hexdigest()[:16],
            'client':{'kind':'desktop-pet','id':'workbuddy-desktop-pet','version':__version__}})
        challenge=pipe.receive()
        server_nonce=challenge.get('server_nonce','')
        if challenge.get('type')!='session_challenge' or not isinstance(server_nonce,str) or not 16<=len(server_nonce)<=128:
            raise RelayError('WorkBuddy 余额认证未就绪')
        expected=_proof(ticket,'server',endpoint,nonce,server_nonce)
        if not isinstance(challenge.get('server_proof'),str) or not hmac.compare_digest(expected,challenge['server_proof']):
            raise RelayError('余额通道身份校验失败')
        pipe.send({'type':'session_prove','client_proof':_proof(ticket,'client',endpoint,nonce,server_nonce)})
        ack=pipe.receive()
        if ack.get('type')!='session_hello_ack' or 'wb.request' not in ack.get('pipes',[]):raise RelayError('WorkBuddy 余额转发未连接')
        pipe.send({'jsonrpc':'2.0','id':1,'method':'broker/GetPipe','params':{'pipe':'wb.request'}})
        opened=pipe.receive()
        if opened.get('id')!=1 or 'error' in opened:raise RelayError('余额转发接口不可用')
        channel=opened.get('result',{}).get('channel')
        if channel!='c:wb.request' or 'http.fetch' not in opened.get('result',{}).get('methods',[]):raise RelayError('余额通道版本不兼容')
        # Fixed purpose only: no caller-supplied URL, body or authorization header.
        pipe.send({'jsonrpc':'2.0','id':2,'method':channel+'/http.fetch','mode':'call',
            'params':{'method':'POST','path':path,'headers':{'content-type':'application/json','accept':'application/json'},
                      'body_b64':base64.b64encode(b'{}').decode()}})
        reply=pipe.receive()
        if reply.get('id')!=2 or 'error' in reply:raise RelayError('WorkBuddy 暂未返回余额')
        result=reply.get('result',{})
        if result.get('status')!=200:raise RelayError('余额服务暂不可用，请在 WorkBuddy 检查登录')
        raw=base64.b64decode(result.get('body_b64',''),validate=True)
        if len(raw)>655360:raise RelayError('余额摘要超过上限')
        return json.loads(raw)
    finally:
        pipe.close()

