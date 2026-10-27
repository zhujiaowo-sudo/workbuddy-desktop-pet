# WorkBuddy Desktop Pet

面向 **Windows 11 / Windows 10 x64** 的 WorkBuddy 专用桌面宠物。

让桌面角色跟随 WorkBuddy 的工作状态变化，在任务完成或需要你确认时提醒你，并支持点击唤起 WorkBuddy。

> 当前版本：**v0.1.0 Windows 预览版**。已实现桌宠程序和本地状态插件，并在 WorkBuddy 5.9.2 上验证真实任务事件。部分事件尚未观察到，详见[兼容性记录](docs/compatibility.md)。

## 已实现功能

- 状态动画：空闲、思考、执行工具、等待输入、等待审批、完成、失败。
- 多会话状态汇总：优先展示需要用户处理的会话，避免子任务完成导致整项任务被误报完成。
- 提醒：等待确认提示、任务完成通知、点击后确认已读。
- 桌面交互：透明悬浮窗、拖动、位置记忆、系统托盘与点击唤起 WorkBuddy。
- 接入诊断：区分未连接、已收到事件与连接过期，不把没有数据显示为空闲。
- 使用程序绘制的原创基础角色；本地动画资源包为后续扩展方向，当前未提供导入界面。

首版只提供状态和提醒；审批继续在 WorkBuddy 内完成。Token、账户余额、对话直达和聊天功能不纳入首版。

## 设计与实施计划

- [首版设计](docs/plans/2026-10-27-workbuddy-desktop-pet-design.md)
- [实施计划与验收步骤](docs/superpowers/plans/2026-10-27-workbuddy-desktop-pet.md)
- [参考项目与素材说明](NOTICE.md)

## 启动与连接

下载 Windows 程序包，完整解压后运行 `WorkBuddyDesktopPet/WorkBuddyDesktopPet.exe`。右键角色或点击状态卡的省略号打开设置，选择 `WorkBuddy.exe` 并保存，然后点击“连接 WorkBuddy”。在 WorkBuddy 新建任务即可验证；若旧会话仍未加载插件，保存工作后重新打开 WorkBuddy。

审批继续在 WorkBuddy 内进行；桌宠只负责提醒。首次安装默认不启用登录自启，可在设置中开启。

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.lock
.venv\Scripts\python launch.py --demo
.venv\Scripts\python launch.py
```

源码运行需要 Python 3.12。可执行程序包无需自行安装 Python。构建与移除说明见 [Windows 使用文档](docs/releasing.md)。

## 技术

- Python 3.12+：状态转换、事件读取、设置与诊断。
- PySide6 Essentials：Windows 透明窗、角色绘制、系统托盘和通知。
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

目前已观察到 `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`Stop` 和 `Notification`。此版本中的通知事件尚未提供已识别的通知分类，不能据此宣称等待审批或等待输入已在本机验证。

使用 `--demo` 的界面明确显示“演示”，其事件不写入真实队列。未观察到的事件不当作已验证能力。

Hook 适配器仅记录事件类型、时间、会话标识及必要的工具分类。不收集对话内容、提示词、工具参数、文件正文、登录凭据或 API 密钥。

## 开发进度

- [x] 创建独立仓库并确认 WorkBuddy 专用方向。
- [x] 明确首版范围、技术方案和验证边界。
- [x] 拆分实施任务及验收步骤。
- [x] 在 WorkBuddy 5.9.2 上验证主要任务 Hook。
- [x] 实现事件适配、状态转换和提醒去重。
- [x] 实现 Windows 桌宠、托盘与连接设置。
- [x] 完成打包程序的真实输入、PowerShell 转发及界面启动验证。
- [x] 完成一次真实命令任务的开始、工具执行和完成联调。
- [ ] 补充审批、失败、等待输入和子任务的真实事件验证。

本地自动化测试 36 项通过。GitHub Actions 配置已提供，其运行结果以仓库实际检查状态为准。

## 参考资料

- [WorkBuddy 官方插件说明](https://www.codebuddy.cn/docs/workbuddy/Plugins)
- [白龙桌宠参考项目](https://github.com/Wunsch2048/codex-bailong-desktop-pet)
- [WorkBuddy Buddy 参考项目](https://github.com/FlashFamily/workbuddy-buddy)

本项目与腾讯、WorkBuddy 及上述项目作者无隶属或背书关系。
