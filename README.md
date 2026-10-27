# WorkBuddy Desktop Pet

面向 **Windows 11 / Windows 10 x64** 的 WorkBuddy 专用桌面宠物。

让桌面角色跟随 WorkBuddy 的工作状态变化，在任务完成或需要你确认时提醒你，并支持点击唤起 WorkBuddy。

> 当前状态：项目初始化与首版设计已完成，正在等待实施计划确认。此仓库暂不包含可运行的桌宠程序或安装包。以下功能为开发目标，不代表已实测可用。

## 首版目标

- 状态动画：空闲、思考、执行工具、等待输入、等待审批、完成、失败。
- 多会话状态汇总：优先展示需要用户处理的会话，避免子任务完成导致整项任务被误报完成。
- 提醒：等待确认提示、任务完成通知、点击后确认已读。
- 桌面交互：透明悬浮窗、拖动、位置记忆、系统托盘与点击唤起 WorkBuddy。
- 接入诊断：区分未连接、已收到事件与连接过期，不把没有数据显示为空闲。
- 使用基础原创程序绘制角色，后续支持用户选择本地动画资源包。

首版只提供状态和提醒；审批继续在 WorkBuddy 内完成。Token、账户余额、对话直达和聊天功能不纳入首版。

## 设计与实施计划

- [首版设计](docs/plans/2026-10-27-workbuddy-desktop-pet-design.md)
- [实施计划与验收步骤](docs/superpowers/plans/2026-10-27-workbuddy-desktop-pet.md)
- [参考项目与素材说明](NOTICE.md)

## 计划采用的技术

- Python 3.12+：状态转换、事件读取、设置与诊断。
- PySide6：Windows 透明窗、角色绘制、系统托盘和通知。
- WorkBuddy Hook 插件：采集最少的结构化生命周期事件。
- PyInstaller：打包 Windows x64 程序。
- pytest：验证事件处理、多会话状态、断连和配置维护。

## 数据流

```mermaid
flowchart LR
  A[WorkBuddy 生命周期事件] --> B[Hook 适配器]
  B --> C[本地结构化事件队列]
  C --> D[会话状态转换与汇总]
  D --> E[桌宠动画与提醒]
  E -->|用户点击| F[唤起 WorkBuddy]
```

## 接入边界

WorkBuddy 官方文档列有 Hook 插件，但具体事件与负载需要在目标桌面版实测。CodeBuddy CLI 文档中的事件不能直接视为 WorkBuddy 桌面版已支持的能力。

验证通过前，文档和界面将明确标注“演示”或“未验证”；不会将演示事件作为真实任务状态。

Hook 适配器仅记录事件类型、时间、会话标识及必要的工具分类。不收集对话内容、提示词、工具参数、文件正文、登录凭据或 API 密钥。

## 开发进度

- [x] 创建独立仓库并确认 WorkBuddy 专用方向。
- [x] 明确首版范围、技术方案和验证边界。
- [x] 拆分实施任务及验收步骤。
- [ ] 在当前 WorkBuddy 桌面版验证 Hook 兼容性。
- [ ] 实现事件适配与状态转换。
- [ ] 实现 Windows 桌宠与提醒。
- [ ] 完成本机联调和 Windows 打包。

## 参考资料

- [WorkBuddy 官方插件说明](https://www.codebuddy.cn/docs/workbuddy/Plugins)
- [白龙桌宠参考项目](https://github.com/Wunsch2048/codex-bailong-desktop-pet)
- [WorkBuddy Buddy 参考项目](https://github.com/FlashFamily/workbuddy-buddy)

本项目与腾讯、WorkBuddy 及上述项目作者无隶属或背书关系。
