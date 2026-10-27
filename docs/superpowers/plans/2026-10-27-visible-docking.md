# 可见人物停靠 Implementation Plan

> 沿用用户指定的本会话直接开发方式，不启动子代理。

**Goal:** 两倍人物保持，胶囊贴近可见顶部8逻辑像素。

**Architecture:** 解码记录帧边界，播放器聚合并发出边界变更信号；PetWindow共享绘制/坐标映射，纯位置函数支持可见锚点。

**Tech Stack:** Python3.12、Pillow、PySide6、pytest、PyInstaller。

**Spec:** docs/plans/2026-10-27-visible-docking-design.md。

## Global Constraints

- 不缩小角色、不改素材、不改其他用户设置。
- 胶囊间距8逻辑像素；动作内边界稳定。
- 仅卡片独立位置、侧边展开和固定只读余额接口保持。

## Review Focus

- 透明RGB颜色和轻微透明噪点不应撑大轮廓：Task 1。
- 全透明帧、图片资源缺失仍有有效回退：Task 1。
- 放大、DPI、底部对齐的目标区域与停靠映射一致：Task 2。
- 角色靠近屏幕边缘时完整窗口和胶囊仍在屏内：Task 2。
- 换帧不抖动、换动作正确更新、仅卡片不跟随隐藏人物：Task 2。

### Task 1: 可见边界

Files: materials.py, ui/animation.py, tests/test_materials.py, tests/test_visible_docking.py。

- [x] 先用合成透明边距和动画帧验证边界、并集与全透明回退。
- [x] Frame追加可见边界，加载时聚合；bounds_changed只在动作加载/清空时通知。
- [x] 验证换帧边界和信号不变，原解码限制与播放器回归通过。

### Task 2: 停靠与控制器

Files: ui/pet.py, placement.py, app.py, tests/test_placement.py, tests/test_card.py。

- [x] 测试放大人物的目标矩形、可见锚点8px间距及屏幕边缘约束。
- [x] 共享图片目标矩形，缓存静态边界；纯位置函数接受可选anchor，Controller连接边界变更。
- [x] 更新原收放测试，验证人物大小、缩放比例及位置不变，只有胶囊跳过透明边距。
- [x] 按用户补充固定原蓝色应用/托盘/EXE图标；验证更换人物资源不能影响图标，素材预览仍显示人物。

### Task 3: 交付

- [x] 合成数据及真实素材7状态预览，全部测试、冻结程序验证。
- [x] 更新本机，核对224大小、高清动画及8px间距；提交推送。
- [ ] CI通过后发布v0.3.2核心和校验文件，素材下载保留v0.3.1。
