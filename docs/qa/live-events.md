# 真实WorkBuddy事件验收

自动化测试使用合成数据。以下流程用于真实客户端验收；事件汇总只说明收到事件，界面表现还需逐项观察。不得修改权限策略、代用户批准操作或以脚本注入Hook冒充实测。

1. 记下WorkBuddy版本、桌宠版本及本地开始时间，新建专用测试会话；不使用私人工作内容。
2. 请求一次简单只读操作，核对开始、工具前后、完成事件及桌宠表现。
3. 请求读取一个明确不存在的测试文件，核对是否发出PostToolUseFailure；工具返回错误文本不等于宿主一定发出失败事件。
4. 请求通过提问工具给出两个无敏感信息的选项；停留在输入提示，核对Notification的可识别类型及waiting表现。普通聊天提问不等于该事件。
5. 如出现审批提示，先核对review。审批由用户自行检查并决定，未批准时后续事件尚未出现是正常结果。
6. 请求一项无副作用的子任务（如独立计算），核对有父标识的SubagentStart/Stop配对；父任务不可被子任务停止事件提前结束。
7. 在源码目录运行以下只读汇总（时间替换为本次开始时间）。输出不含会话ID、正文、账户或路径；如需分享只分享汇总。

```powershell
python tools/collect_event_audit.py --since 2026-10-29T17:45:00+08:00
```

`observed`为事件覆盖，`not_observed`不是功能失败结论；`scan_complete=false`表示达到扫描上限。验收记录需同时标明人工操作、实际事件、界面结果以及未完成原因。

2026-10-29本轮：界面识别WorkBuddy5.9.3；用户触发测试并确认停在审批提示。队列观察到Notification(permission_prompt)，现有0.6.6桌宠runtime显示review、connected、demo=false。随后用户完成测试，观察到两组PreToolUse/PostToolUse及Stop，Stop之后出现idle_prompt。用户反馈“成功了”，但队列未观察到PostToolUseFailure或有父标识的子任务配对；也未出现input_required/elicitation_dialog，暂不声称这些场景已通过。

真实顺序还显示SessionStart晚于UserPromptSubmit；0.6.7已补回归并修复晚到的启动事件抹除思考/工作/审批状态的问题。新版本对真实脱敏事件的内存重放属于逻辑复核，不等同新版本端到端联调。
