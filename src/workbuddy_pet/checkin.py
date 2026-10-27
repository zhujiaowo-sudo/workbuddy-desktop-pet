"""Daily check-in through WorkBuddy; only an explicit click may call perform_checkin."""
from dataclasses import dataclass
from decimal import Decimal,InvalidOperation
import time

from .workbuddy_relay import RelayError,request_json


class CheckinError(ValueError):pass


def local_day(now=None):return time.strftime('%Y-%m-%d',time.localtime(time.time() if now is None else now))


@dataclass(frozen=True)
class CheckinSnapshot:
    state: str = 'unknown'
    daily_credit: float | None = None
    awarded: float | None = None
    message: str = '等待 WorkBuddy 签到状态'
    day: str = ''

    @property
    def checked(self):return self.state in ('checked','claimed')

    @property
    def available(self):return self.state in ('available','checked','claimed','inactive')


def _number(value):
    if type(value) not in (int,float,str):return None
    try:amount=Decimal(str(value))
    except InvalidOperation:return None
    if not amount.is_finite() or amount<0:return None
    result=float(amount)
    return result if result<float('inf') else None


def parse_status(response):
    if not isinstance(response,dict) or type(response.get('code')) is not int or response['code']!=0:
        raise CheckinError('签到状态暂不可读')
    data=response.get('data')
    if not isinstance(data,dict):raise CheckinError('签到状态不完整')
    active=data.get('active');checked=data.get('today_checked_in',data.get('todayCheckedIn'))
    if type(active) is not bool or type(checked) is not bool:raise CheckinError('签到状态不完整')
    credit=_number(data.get('daily_credit',data.get('dailyCredit')))
    state='inactive' if not active else 'checked' if checked else 'available'
    message={'inactive':'WorkBuddy 签到活动暂不可用','checked':'今日已签到','available':'点击领取今日签到积分'}[state]
    return CheckinSnapshot(state,credit,message=message,day=local_day())


def parse_claim(response):
    if not isinstance(response,dict) or type(response.get('code')) is not int:
        return CheckinSnapshot('uncertain',message='签到结果待确认，请刷新状态',day=local_day())
    code=response['code'];data=response.get('data')
    if isinstance(data,dict) and type(data.get('code')) is int and data['code']!=0:code=data['code']
    if code==1001:return CheckinSnapshot('checked',message='今日已签到',day=local_day())
    if code in (1002,1003):return CheckinSnapshot('inactive',message='当前账户或活动暂不支持签到',day=local_day())
    if code!=0:return CheckinSnapshot('error',message='签到未完成，请在 WorkBuddy 查看或完成验证',day=local_day())
    awarded=_number(data.get('credit')) if isinstance(data,dict) else _number(response.get('credit'))
    return CheckinSnapshot('claimed',awarded=awarded,message='签到成功',day=local_day())


def read_checkin(home):
    try:return parse_status(request_json(home,'checkin_status'))
    except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):
        return CheckinSnapshot('unknown',message='签到状态暂不可读，请确认 WorkBuddy 已运行并登录',day=local_day())


def perform_checkin(home,cancel=lambda:False):
    """Single click transaction: read first, submit at most once, never retry a claim."""
    if cancel():return CheckinSnapshot(message='签到已取消')
    status=read_checkin(home)
    if status.state!='available' or cancel():return status
    try:return parse_claim(request_json(home,'checkin_claim'))
    except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):
        return CheckinSnapshot('uncertain',message='签到结果待确认，请刷新状态；不会自动重试领取',day=local_day())
