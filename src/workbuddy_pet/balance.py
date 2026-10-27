"""Read personal remaining credits using only the fixed balance request purpose."""
from dataclasses import dataclass
from decimal import Decimal,InvalidOperation
from pathlib import Path
import time
from .workbuddy_relay import RelayError as BalanceError,PIPE_PREFIX,_NamedPipe,_proof,request_json

SUMMARY_PATH='/billing/meter/get-user-resource-summary'

@dataclass(frozen=True)
class BalanceSnapshot:
    remaining: float | None = None
    at: float | None = None
    message: str = '等待 WorkBuddy 余额连接'


def _summary(home: Path,transport_factory=_NamedPipe):
    return request_json(home,'balance',transport_factory)


def parse_summary(response,at=None):
    if not isinstance(response,dict) or type(response.get('code')) is not int or response.get('code')!=0:raise BalanceError('账户余额摘要查询失败')
    data=response.get('data')
    packages=data.get('Packages') if isinstance(data,dict) else None
    if not isinstance(packages,list) or len(packages)>500:raise BalanceError('余额摘要不完整')
    total=Decimal(0)
    for package in packages:
        if not isinstance(package,dict):raise BalanceError('余额明细无效')
        value=package.get('CycleRemainCapacity')
        if type(value) not in (int,float,str):raise BalanceError('余额明细缺少可用积分')
        try:amount=Decimal(str(value))
        except InvalidOperation:raise BalanceError('余额数值无效') from None
        if not amount.is_finite() or amount<0:raise BalanceError('余额数值无效')
        total+=amount
    # Matches the desktop client's sumSummaryCapacity; no unit conversion or local debit inference.
    return BalanceSnapshot(float(total),time.time() if at is None else at,'WorkBuddy 个人账户余额')


def read_balance(home: Path):
    try:return parse_summary(_summary(home))
    except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):
        return BalanceSnapshot(message='余额暂不可读，请确认 WorkBuddy 已运行并登录')
