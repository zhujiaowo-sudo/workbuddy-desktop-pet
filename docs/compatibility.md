# WorkBuddy 桌面版兼容性记录

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
