# 动画结构与入口修复 Implementation Plan

**Goal:** 无重影/拼接变形，右键单开关，小卡−仅收卡片。
**Architecture:** AnimationPlayer只显示原帧；固定身体+刚性部件生成默认动作；CardWindow保存视图，Controller独立管理人物可见性，共享菜单仅一个切换项。
**Tech Stack:** PySide6、Pillow、imagegen、pytest、PyInstaller。
**Spec:** docs/plans/2026-10-28-animation-integrity-design.md。

## Global Constraints
- 用户明确的新收起语义优先于旧设计，不改变账户授权/自启/应用图标。
- 15必填+可选挠头及72M高清上限不变；旧素材仍可用。
- 每帧身体/脸型/腿结构稳定，禁止用完整人物图片叠加冒充补帧。

## Review Focus
- 卡片层级变化不能隐式隐藏人物。
- 一个切换项须覆盖永久仅卡片与临时隐藏，贴底恢复仍有效。
- 帧首尾、动作切换和任意采样时间均不能混合两套五官/肢体。
- 连续播放与全部原始帧必须同时检查，固定身体须跨idle/scratch成立。

### Task 1：交互与播放器
- [x] 分离卡片缩小与人物隐藏，右键合并开关并回归。
- [x] 去除图片叠帧，验证中途采样与动作切换只显示原始帧。

### Task 2：素材与动态验收
- [x] 生成分层源素材、刚性手臂动画和固定脸型眨眼。
- [x] 输出全部动作帧表、连续循环和切换预览，检查结构不变形。

### Task 3：交付
- [ ] 回归、冻结包、本机更新、CI和公开发布验证。
