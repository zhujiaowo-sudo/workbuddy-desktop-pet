# WorkBuddy 桌面版兼容性记录

## v0.3.0 三级布局

67项自动化测试通过。胶囊仅保留两个模块且外部透明；点击进入320×202的数据小卡，再展开上方看板。合成数据检查100%与150%缩放，覆盖导航返回、余额数字、胶囊拖动、只读统计和原功能。今日消费按系统本地日历日独立汇总，缺时间和未来请求不计入；新会话未建立索引时不会套用旧会话标题。剩余积分接口与授权范围沿用v0.2.1。

冻结程序已验证Hook输入、PowerShell转发、素材导入、仅卡片及三种视图启动；本机更新后的v0.3.0以非演示模式运行，连接及真实余额查询正常。没有新增任务事件类型的实测结论。

## v0.2.1 界面修正

63项测试通过；合成截图检查100%和150%缩放。覆盖胶囊位于人物正上方、边缘整体让位、右键选择后展开页面、独立导航和不透明内容、仅卡片独立坐标、右上角收起入口以及余额查询。

余额源码核查：WorkBuddy5.9.2的 `auth:getAccountUsage` 依赖授权会话，普通缓存不提供余额。进一步确认了本地WBIPC `wb.request/http.fetch` 转发能力；在用户明确授权读取本机连接票据后，双向HMAC握手和个人积分摘要查询实测成功（HTTP200/code0）。程序只调用固定的 `/billing/meter/get-user-resource-summary` 查询路径，按与客户端相同的 `Packages[].CycleRemainCapacity` 汇总；数值无需单位换算。

余额功能默认关闭，由“授权本地查询剩余积分”启用。本机连接票据只用于本机握手；不读取登录access token，不向网络上传票据，不把票据或余额写入桌宠诊断。只有通过服务端身份校验、完整返回摘要后才显示数字；查询失败清除旧值并显示待同步。当前适配个人账户积分，团队预算接口未在本版验证。

## v0.2.0 新增验证

- 只读访问本机 WorkBuddy5.9.2 SQLite：可读取会话、请求积分，且部分历史请求可关联模型；未读取账户登录凭据。
- `session_usage.credit_json` 是请求ID到积分的映射。used/size是上下文用量与容量，未累计为计费Token。
- Windows注册与客户端源码确认 `workbuddy://chat/<id>`；真实测试已打开先前算术测试会话的主页面。协议调用可能保持最小化，桌宠另按有效程序路径恢复窗口。
- 49项自动化测试覆盖原事件链路、素材导入、路径/坏图拒绝、动画时长、胶囊与仅卡片、集成设置、模型接口及Windows DPAPI保存/读取。受限测试账户无DPAPI用户配置时需要在真实当前用户下执行该加密验证，未使用明文存储作为回退。
- 默认轻量256px、高清512px素材包均经过完整解码验证，均含7个状态；这些是本项目原创形象的导出图像。
- Chat Completions文本接口已通过本机合成HTTP服务验证收发与无工具请求；没有使用用户私有模型密钥做真实模型调用。
- WorkBuddy随附CLI已检查参数并尝试无工具文本请求；单独运行尚未获得有效回复，原生用户测试出现授权相关提示。因此不能宣称桌面登录已自动复用，也不能宣称已在卡片中收发桌面已有任务消息。
- 独立闲聊可显式配置本机或HTTPS模型接口；密钥仅通过Windows用户DPAPI加密保存。未连接宿主内部IPC或导出WorkBuddy登录票据。

验证日期：2026-10-27。环境为 Windows 10 x64 22H2（19045），WorkBuddy 桌面版 5.9.2，随应用提供的 Agent CLI 2.165.0。

## 已验证

- 本机应用中的 `.codebuddy-plugin/plugin.json`、本地目录市场、`extraKnownMarketplaces` 和 `enabledPlugins` 配置结构。
- 使用随 WorkBuddy 提供的插件校验命令验证了生成的插件和市场清单。
- WorkBuddy 已将本插件安装进标准版本化缓存，未手动改写其插件注册表。
- 使用打包程序通过标准输入接收 Hook 数据并写入白名单事件。
- Windows PowerShell 调用链能保留输入，以及参数中的空格和单引号。
- 打包 GUI 启动、独立用户目录、演示截图与正常退出。

## 真实任务观察

由用户在 WorkBuddy 新建任务并要求执行简单本机算术命令。仅检查本插件生成的结构化事件，不保存提示词、工具参数、回复、会话标题或文件路径。

| 事件 | 本机观察 | 结构化字段 |
| --- | --- | --- |
| SessionStart | 已收到 | 会话标识、generation_id |
| UserPromptSubmit | 已收到 | 会话标识、generation_id |
| PreToolUse | 已收到 | generation_id、tool_use_id、命令工具分类 |
| PostToolUse | 已收到 | generation_id、tool_use_id、命令工具分类 |
| Stop | 已收到 | 会话标识、generation_id |
| Notification | 已收到 | generation_id；未出现可识别的 notification_type |
| PostToolUseFailure | 未观察到 | 未验证 |
| PermissionRequest | 未观察到 | 未验证 |
| SessionEnd | 未观察到 | 未验证 |
| SubagentStart / SubagentStop | 未观察到 | 未验证 |

桌宠在真实任务完成后显示 `done`、`connected`、一个未读完成提醒，且 `demo=false`。后续新消息触发 `thinking` 并消除上一阶段提醒。真实队列损坏行计数为零。

等待审批和等待输入状态已实现并有合成测试覆盖，但在此版本桌面端尚未验证其真实触发方式。未通过读取对话内容来推测这些状态；未配置自动审批。

子任务、轮次乱序及重复事件由合成测试覆盖，仍需增加目标桌面版实测。仅在实际提供 generation_id/tool_use_id 时做相应关联，不补造来源标识。

## QtCore 打包问题与修复

初次打包出现 QtCore DLL 加载失败。原因是构建环境的 Git 目录提供了另一个同名 `icuuc.dll`，其带版本后缀的导出接口与 Qt 6.12 要求的 Windows 原生 ICU 接口不一致。

构建脚本现会比较 Qt 所需导出和收集库的导出；出现此冲突时，验证系统原生 ICU 可用并移除错误收集的 ICU，不修改系统 DLL。另修正了构建检查器未关闭 PE 文件映射导致无法替换文件的问题。

修复后重新构建，并通过 `tools/verify_package.py` 的打包采集、PowerShell 转发、GUI 启动和截图检查。Windows 旧版本未逐一验证；当前 Qt 依赖要求系统具有兼容原生 ICU。
