# Window Themes Implementation Plan

**Goal:** 恢复用户确认的常驻窗口与两个右上角按钮，提供三套配色、透明胶囊和加粗积分。
**Architecture:** 新增独立CompactPanel与TrendChart，CardWindow负责展示形态；Settings持久保存外观和窗口偏好，Controller统一切换。LocalDataReader在现有只读遍历内汇总每日积分，窗口复用同一快照。
**Tech Stack:** Python3.12、PySide6、Pillow、Inno Setup7。
**Spec:** docs/plans/2026-11-01-window-themes-design.md

## Global Constraints

- 窗口常驻，右上角只有切回胶囊／打开看板两个按钮；关闭大看板返回所选模式。
- 不变更人物素材和授权；旧设置可读。数据使用合成测试夹具，公开截图不包含真实会话。

## Review Focus

- 仅窗口与仅胶囊转换不恢复人物；从看板退出仍保持窗口偏好。
- 主窗口改变大小不得覆盖用户选择的紧凑窗口尺寸；保持屏幕停靠和独立拖动。
- 按自然日聚合，只使用有效时间；缺失数据不是零。
- 切换主题不重置其他偏好，透明胶囊的按钮和拖动区域仍可用。
- 常驻窗口不会禁用随机闲置；菜单、拖动、真实任务仍保留优先级。

- [x] Settings新增theme/capsule_transparent/window_mode；主题集中生成样式，旧设置兼容测试。
- [x] LocalDataReader增加日粒度积分序列；合成时间、缺失时间和日期筛选独立性测试。
- [x] CompactPanel两个按钮、趋势空态、数字加粗；CardWindow五种形态导航及Controller持久化测试。
- [x] 设置与右键外观入口，主题即时应用；原生截图和100%／150%验证。
- [x] 203项全量测试、冻结验证与安装包准备。

发布门禁：Windows CI安装、升级和卸载成功后公开安装包，再按保留偏好的流程升级本机；交付结果以正式Release与本机安装记录为准。

每项先加入行为测试，验证失败后实现并运行相关检查。使用本会话原生执行，不另行要求用户重复批准已确认的方案。
