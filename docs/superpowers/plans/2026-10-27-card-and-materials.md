# 卡片与开放素材包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 当前环境无该技能，沿用用户指定的本会话直接开发方式；不启动子代理。

**Goal:** 交付本地统计、胶囊集成卡片、会话跳转、可选动画与开放素材模板。

**Architecture:** 本地数据适配器和角色包存储独立于事件状态机；Qt主界面消费只读统计快照与受验证素材。卡片为常驻入口，人物是可选展示层。

**Tech Stack:** Python3.12、PySide6 Essentials、SQLite、ZIP、pytest、PyInstaller。

**Spec:** docs/plans/2026-10-27-card-and-materials-design.md

## Global Constraints

- WorkBuddy only；不拷贝白龙代码或人物素材。
- 本机统计不能冒充全账户账单；used/size不能当作累计token。
- 角色包 schema=1，idle必填，7状态缺动作回退idle。
- 不修改WorkBuddy审批决策、不公开登录凭据、不提交真实数据。
- 各项精确大小与计时限制见设计。

## Review Focus

- ZIP路径逃逸、链接、重复名称和超额解码不得改写库外文件。
- 相同请求多条历史只能计一次，未知模型及日期必须明确标记。
- 用户正在输入、工作或有未读提醒时不自动收起卡片。
- 删除当前角色或损坏素材不得影响卡片和设置。
- CLI失败、未登录或取消不得显示虚构回复或执行工具。

### Task 1: 本地统计与会话

Files: src/workbuddy_pet/local_data.py, tests/test_local_data.py, src/workbuddy_pet/windows.py。

- [ ] 合成数据库和JSONL验证credit按请求关联、元数据去重、日期筛选、deleted_at过滤、缺失元数据及只读打开。
- [ ] 实现 LocalDataReader(home).snapshot(days=None)，返回本机会话、请求和模型积分统计；增量元数据缓存仅驻内存。
- [ ] 增加 conversation_url(session_id) 和 open_conversation，测试URL编码和非法输入。
- [ ] 运行相关测试并提交。

### Task 2: 角色包与播放器

Files: src/workbuddy_pet/materials.py, src/workbuddy_pet/ui/animation.py, tools/create_pet_template.py, tests/test_materials.py。

- [ ] 先测试合法ZIP/目录、缺idle、缺动作回退、坏图、越界、重复名称、超限与删除不触碰源文件。
- [ ] 实现 MaterialLibrary 的 import_pack/list_packs/load/remove，SHA256内容版本目录；分步验证后发布。
- [ ] 实现有界帧播放器，停止时释放帧、隐藏时暂停，动作遵循帧间隔。
- [ ] 导出独立原创示例包 light/hd 以及中文创作模板，运行测试并提交。

### Task 3: 卡片与素材管理

Files: src/workbuddy_pet/ui/card.py, src/workbuddy_pet/ui/materials.py, src/workbuddy_pet/ui/settings.py, src/workbuddy_pet/app.py, src/workbuddy_pet/settings.py, tests/test_ui.py。

- [ ] 测试手动/自动胶囊、未读与焦点阻止收起、仅卡片恢复、设置同窗、素材切换及暂停。
- [ ] 单窗口页面集成详情/统计/聊天/素材/设置；会话名可点击跳转。
- [ ] 增加card_only、auto_collapse、collapse_seconds、character设置，保持旧配置可读。
- [ ] 后台统计读取和导入任务不阻塞GUI，关闭时安全结束。
- [ ] 运行Qt和设置回归测试并提交。

### Task 4: 聊天与发布

Files: src/workbuddy_pet/chat.py, src/workbuddy_pet/ui/chat.py, tests/test_chat.py, README.md, docs/materials.md, docs/compatibility.md, tools/build_windows.py。

- [ ] 验证本机随附CLI文本能力；实现可取消、有时限的无工具聊天客户端与独立闲聊界面；不可用时给出准确诊断和WorkBuddy草稿入口。
- [ ] 用合成进程输出测试成功、失败、取消、超限和命令参数不含权限绕过。
- [ ] 本机验证统计、深链、素材和界面截图；更新中文文档及版本。
- [ ] 全套测试、Windows打包与包验证，通过后推送指定仓库，交付新版程序包和模板。
