# WorkBuddy Desktop Pet

面向 **Windows 11 / Windows 10 x64** 的 WorkBuddy 专用桌面宠物。

让桌面角色跟随 WorkBuddy 的工作状态变化，在任务完成或需要你确认时提醒你，并支持点击唤起 WorkBuddy。

> 当前版本：**v0.3.2 Windows 预览版**。修复人物放大后胶囊留白过大，按可见轮廓贴近停靠。默认形象“薄荷星伴”支持轻量/高清独立动画，采用胶囊、数据小卡、展开看板三级布局。[兼容性记录](docs/compatibility.md)区分实测与尚未验证能力。

## 已实现功能

- 状态动画：空闲、思考、执行工具、等待输入、等待审批、完成、失败。
- 多会话状态汇总：优先展示需要用户处理的会话，避免子任务完成导致整项任务被误报完成。
- 提醒：等待确认提示、任务完成通知、点击后确认已读。
- 桌面交互：透明悬浮窗、拖动、位置记忆、系统托盘与点击唤起 WorkBuddy。
- 接入诊断：区分未连接、已收到事件与连接过期，不把没有数据显示为空闲。
- 数据面板：只读本地积分记录，按请求元数据关联模型，支持全部/7天/30天；未知模型、缺时间明确列出。
- 集成卡片：胶囊点击进入紧凑数据模式，再展开详情、数据看板、聊天、素材或设置；闲置可自动缩成胶囊。
- 数据模式：显示会话名称与任务状态、个人账户剩余积分、本机今日消耗；今日按本地零点计算，不受看板日期范围影响。
- 会话跳转：点击会话名称直达对应 WorkBuddy 对话，兼容当前 Windows 协议注册。
- 仅卡片模式：隐藏人物并释放动画，保留状态、统计与设置；程序包不包含外部人物动画。
- 自制素材：ZIP/文件夹导入、预览、启用、删除、模板导出；PNG/GIF/WebP，至少一段待机即可。默认轻量/高清示例包独立下载，详见[素材制作说明](docs/materials.md)。
- 独立闲聊：卡片内配置兼容 Chat Completions 的本机或 HTTPS 模型接口；密钥通过 Windows DPAPI 加密。随附 WorkBuddy CLI 为候选本地通道，本机尚未通过该通道的授权验证，不能宣称可直接接管桌面已有会话。

审批继续在 WorkBuddy 内完成。本机积分统计不代表完整账户账单；上下文 used/size 不累计为 Token 消耗，Auto 缺少实际响应模型时明确标记未知。卡片闲聊不执行工具，也不自动代替用户发送桌面任务消息。

## 设计与实施计划

- [首版设计](docs/plans/2026-10-27-workbuddy-desktop-pet-design.md)
- [实施计划与验收步骤](docs/superpowers/plans/2026-10-27-workbuddy-desktop-pet.md)
- [参考项目与素材说明](NOTICE.md)
- [卡片和素材设计](docs/plans/2026-10-27-card-and-materials-design.md)
- [角色包 JSON Schema](docs/pet-pack.schema.json)

## 启动与连接

下载 Windows 程序包，完整解压后运行 `WorkBuddyDesktopPet/WorkBuddyDesktopPet.exe`。右键角色或点击小卡顶栏的齿轮打开设置，选择 `WorkBuddy.exe` 并保存，然后点击“连接 WorkBuddy”。在 WorkBuddy 新建任务即可验证；若旧会话仍未加载插件，保存工作后重新打开 WorkBuddy。

点击人物或胶囊进入320×202的数据小卡。蓝色顶栏依次提供刷新、详情、统计、聊天、设置和右上角收起；统计等页面展开在小卡上方，点击展开区右上角×返回数据模式。右键人物仍可直达指定页面。胶囊只保留会话与数字积分两个模块，停靠人物正上方；靠屏幕边缘时两者整体让位，拖动胶囊模块也能移动。只用卡片可运行随包的 `仅卡片启动.vbs`，或在“设置”勾选“仅显示卡片”。素材页提供导入、模板导出和可选的默认动画下载；不下载动画也可使用薄荷星伴静态形象。

默认形象“薄荷星伴”由Buddy娘提供，采用[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)；来源和内置首帧导出说明见[NOTICE](NOTICE.md)。旧机器人创作模板保持独立CC0许可。

胶囊按人物可见轮廓上方8个逻辑像素停靠，忽略窗口和素材画布的透明留白。动画以整段帧轮廓并集定位，播放时不会逐帧跳动；放大人物不再同步放大中间空白。

任务栏、托盘、窗口及程序文件图标固定为原始蓝色小搭子，不提供修改入口；导入、切换或删除人物素材均不会改变应用图标。

胶囊旁只显示剩余积分数字，提示中可查看含义和更新时间。在设置中启用“授权本地查询剩余积分”后，通过WorkBuddy本地WBIPC转发读取真实个人积分摘要，每60秒刷新，任务结束后会提前更新。连接票据只用于本机握手，不上传、不写入桌宠日志；登录凭据由WorkBuddy自身持有。查询失败时显示“积分待同步”，不以本机消耗推算余额。点击徽标进入数据模式并刷新；顶栏刷新同时更新余额与本机统计。今日消耗不含缺时间或未来的请求，仅代表可读取的本机记录。

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

自动化测试覆盖统计关联、素材校验、聊天接口、胶囊与仅卡片回归。GitHub Actions 的运行结果以仓库实际检查状态为准。

## 参考资料

- [WorkBuddy 官方插件说明](https://www.codebuddy.cn/docs/workbuddy/Plugins)
- [白龙桌宠参考项目](https://github.com/Wunsch2048/codex-bailong-desktop-pet)
- [WorkBuddy Buddy 参考项目](https://github.com/FlashFamily/workbuddy-buddy)

本项目与腾讯、WorkBuddy 及上述项目作者无隶属或背书关系。
