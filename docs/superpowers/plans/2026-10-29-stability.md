# 稳定性与后台性能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 修复已确认的更新、状态和性能问题并补齐可执行验收。

**Architecture:** 保留纯状态、应用协调、界面及本地存储边界。新增独立后台状态写入器和日志增量游标；素材缓存集中在校验层。

**Tech Stack:** Python3.12、PySide6、Pillow、pytest、PyInstaller。

**Spec:** docs/plans/2026-10-29-stability-design.md

## Global Constraints

- Windows x64、仅WorkBuddy；原始GIF、现有授权与审批规则保持。
- 过期阈值120秒；后台心跳15秒；日志每次64MiB/每行2MiB上限。
- 所有测试使用合成数据；真实事件证据不得由合成测试替代。

## Review Focus

- 下载完成后已有回调与“稍后”竞争，必须暂停自动安装。
- 过期会话与真实等待/失败并存，仍优先提醒。
- 工具并行及新轮次复用标识，不能误抹活跃工具。
- 文件大小不变的重写或路径替换，缓存必须失效。
- 更新器启动握手需要及时runtime.json，后台限频不可延误。

### Task 1: 更新与状态一致性

**Files:** ui/updates.py、state.py、interaction.py、ui/card.py及对应tests。
**Interfaces:** effective_state(session, now)供显示及休闲统一调用；更新器暂停标记供自动回调读取。
- [x] 添加更新ready/等待编辑后取消、手动恢复及未取消自动安装测试；补过期提示、休闲和工具乱序/并行/新轮次测试。
- [x] 运行对应测试确认原问题失败。
- [x] 实施定向修复并运行相关回归。
- [x] 提交更新与状态修复。

### Task 2: 素材缓存和后台runtime

**Files:** materials.py、builtin.py、app.py、新runtime.py、tests/test_materials.py、tests/test_runtime.py。
**Interfaces:** validate_pack缓存仅适用于decode=False且支持强制重验；RuntimeWriter.submit(dict)、close()。
- [x] 添加重复加载不重复哈希、文件变更/强制启用重验测试；后台合并、心跳、失败重试及关闭测试。
- [x] 确认原行为不能满足性能断言。
- [x] 实现缓存、单写入线程与最新值合并；控制器启动/退出接线。
- [x] 运行相关回归并提交。

### Task 3: 增量统计

**Files:** local_data.py、tests/test_local_data.py。
**Interfaces:** LocalDataReader.snapshot保持返回协议；内部游标仅缓存结构化元数据与读取边界指纹。
- [x] 添加追加读取量、半行、截断、替换、同尺寸修改、预算续读和删除测试。
- [x] 实现有界增量索引，保留未换行完整JSON兼容性。
- [x] 运行统计回归并提交。

### Task 4: 验收与文档

**Files:** README.md、docs/project-context.md、docs/compatibility.md、docs/qa/、tools/真实事件汇总工具及tests。
**Interfaces:** 真实事件报告仅输出事件类型计数及覆盖状态，不含会话标识/正文/本机路径。
- [x] 同步当前基线，提供真实事件的可执行验收步骤和脱敏汇总。
- [x] 完整pytest、冻结包验证、变更界面检查与最终diff复核。
- [x] 记录实际结果及未验证真实事件，提交交付。

## 实际交付边界

197项回归、最终冻结包和两档缩放变动场景通过，独立代码审查问题已修复。真实审批与正常生命周期有新证据；等待输入、失败和子任务仍未收到对应证据，已如实记录。GitHub推送因本机凭据服务不可用未完成；交付本地分支、测试包、完整源码及补丁，不冒称已经发布或安装。
