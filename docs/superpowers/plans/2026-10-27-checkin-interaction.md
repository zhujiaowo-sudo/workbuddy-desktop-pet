# 签到与人物交互 Implementation Plan

> 用户指定本会话直接开发，按现有方式执行，不启动子代理。

**Goal:** 更清楚的签到胶囊、全部上方停靠、左击互动与右键模块。

**Architecture:** 固定目的WBIPC转发独立为模块；签到解析为纯函数，Controller独立调度查询/点击领取。CardWindow负责提示，PetWindow负责点击与轻摆，真实任务状态机不改。

**Tech Stack:** Python3.12、PySide6、Pillow、pytest、PyInstaller。

**Spec:** docs/plans/2026-10-27-checkin-interaction-design.md。

## Global Constraints

- 保持size=224、高清人物、固定应用图标和既有设置。
- 本机连接票据原授权仅余额；新增签到独立授权，不提取登录凭据。
- 不自动领取、超时不重试领取、不虚构积分到账。
- 胶囊342×36，上方居中间隔8px；仅卡片位置独立。

## Review Focus

- 重复点击、已签到、失败和未知结果不产生重复领取：Task 1。
- 授权关闭、启动、刷新和跨日都不能领取：Task 1/3。
- 不同显示器与小屏高度下三种视图在人物上方：Task 2。
- 互动期间收到真实工作/完成事件，动画结束后恢复且不伪造任务状态：Task 3。
- 左键拖动不能触发互动，右键菜单不能立即展开：Task 3。

### Task 1: 固定目的转发及签到

Files: workbuddy_relay.py, balance.py, checkin.py, settings.py, ui/settings.py, tests/test_balance.py, tests/test_checkin.py。

- [x] 保留余额协议与双向校验，提取共享转发；目的仅balance/checkin_status/checkin_claim，各自固定POST及空对象。
- [x] 合成传输测试三种目的、未知目的在读取票据前拒绝、协议身份失败及不泄露票据。
- [x] 严格解析状态和领取结果，处理1001/1002/1003、缺奖励、失败及超时；perform_checkin先查询，已签不POST。
- [x] 增加独立checkin_enabled，测试关闭/定时/跨日不领取、点击才领取和刷新余额。

### Task 2: 胶囊及上方面板

Files: ui/card.py, ui/icons.py, placement.py, app.py, tests/test_card.py, tests/test_placement.py。

- [x] 三段胶囊、12px会话、11px粗积分和圆形签到，真实状态提示与点击信号。
- [x] 所有模式居中停靠可见人物顶部8px，结合屏幕高度限制详细区，保留仅卡片位置。
- [x] 测试三段透明间隙、字号/粗细、三模式中心/间距、边缘和高度收缩。

### Task 3: 左击人物互动

Files: interaction.py, ui/pet.py, ui/card.py, app.py, tests/test_interaction.py。

- [x] 左击发出互动，拖动仍移动、右键选择模块；增加小卡菜单入口。
- [x] 实现短句轮换、超时清理、原动画临时覆盖与轻摆，不写入任务事件或改变提醒。
- [x] 测试互动后恢复、工作状态变化、连续点击和模块选择，卡片刷新不抢掉短句。

### Task 4: 验证与交付

- [ ] 取得本机签到额外授权后只读查询真实状态；领取仅用户点击触发。
- [x] 全套测试、合成和原素材预览、冻结程序验证；更新本机保留设置。
- [x] 更新中文说明，推送、CI通过和发布v0.4.0，核验公开附件。

交付：代码9401cef；[Windows检查及全部步骤成功](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/actions/runs/40522473180/job/122252969681)；[v0.4.0公开下载](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/tag/v0.4.0)。95项测试及冻结程序验证通过，公开附件摘要与匿名校验文件下载已核对。本机界面和互动已更新，保留224大小、高清人物与余额查询。

待用户确认：此前本机票据只授权余额，新增签到用途的异步授权问题尚未答复；交付时checkin_enabled=false、状态disabled。没有查询本机签到状态或领取积分，没有真实到账实测结论。用户明确扩展授权后，再启用并仅做状态查询；领取仍由用户点击。
