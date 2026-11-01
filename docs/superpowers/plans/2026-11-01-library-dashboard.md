# Library and Dashboard Implementation Plan

**Goal:** 完成用户已批准的第三套角色、随机待机和统一看板升级。
**Architecture:** 素材校验扩展schema3动作，纯调度器负责随机策略；控制器保持任务和界面分离，统一主题与导航。
**Tech Stack:** Python3.12、PySide6、Pillow、Inno Setup7。
**Spec:** docs/plans/2026-11-01-library-dashboard-design.md

- [x] assets/dragon_maid、builtin/settings/materials/schema：原样导入、署名、兼容测试。
- [x] interaction/app：有效任务判断、按角色选动作、完整播放、任务抢占与测试。
- [x] ui/theme/card/menu/settings/materials/onboarding/updates：统一看板、三种显示模式、加载与筛选反馈、回归。
- [x] 原生循环和UI截图审查、自动回归与冻结检查。
- 发布顺序：构建当前用户安装包，Windows CI通过后发布全部校验附件，再沿用原配置升级本机。

重点：缺少工作动作的明确映射；非循环动作结束；旧过期会话；旧包缺少新动作；快速筛选返回旧数据；隐藏角色不得恢复解码；新UI不得遮挡角色或溢出屏幕。
