# 紧凑卡片修复 Implementation Plan

> 用户已指定本会话直接开发；当前未安装executing-plans技能，不启动子代理。

**Goal:** 修正停靠、菜单、穿透、尺寸和收起入口，加入真实余额的明确未知状态。

**Architecture:** 位置计算为独立纯函数；卡片使用独立导航/内容容器和不透明页面，Controller连接页面与位置事件。

**Tech Stack:** Python3.12、PySide6 Essentials、pytest、PyInstaller。

**Spec:** docs/plans/2026-10-27-compact-ui-fixes-design.md

## Global Constraints

- 不改动WorkBuddy登录、审批、用户插件或其他桌宠。
- 无真实剩余积分时显示待同步，不能从消耗记录推算。
- 全部尺寸为Qt逻辑像素，窗口受显示器可用区域约束。

## Review Focus

- 收起/展开不得移动人物；上方空间不足时需确保窗口和人物不相交。
- 菜单出现不得立即跳页；选择后只展开指定页面。
- 切页/刷新不可留下旧页文字或穿透标签底线。
- 仅卡片拖动、重启与缩放仍能恢复到屏幕内。
- 未知、0和负值余额不能混淆。

### Task 1: 位置与卡片布局

Files: src/workbuddy_pet/placement.py, src/workbuddy_pet/ui/card.py, tests/test_card.py。

- [x] 测试胶囊居中上方、侧边展开、不同人物大小及屏幕边界；先复现旧坐标偏移。
- [x] 实现card_position纯函数和紧凑卡片布局，右上角收起、独立分界线、无原生底线、页面不透明；保留tabs接口供Controller使用。
- [x] 对所有页面反复切换、渲染截图，断言导航与内容几何不重叠。

### Task 2: 菜单、余额与控制器

Files: src/workbuddy_pet/ui/pet.py, src/workbuddy_pet/app.py, src/workbuddy_pet/ui/settings.py, tests/test_card.py。

- [x] 测试菜单不立即展开、动作选择打开正确页面；测试反复收放人物不移动。
- [x] 连接右键菜单和页面选择，窗口尺寸改变重新停靠；仅卡片保持独立位置。
- [x] 核查余额接口；真实来源不可用时展示待同步与原因。测试真实0余额与未知的区别。
- [x] 缩小嵌入式设置控件，避免横向溢出。

### Task 3: 验证与交付

Files: pyproject.toml, src/workbuddy_pet/__init__.py, docs/releases/v0.2.1.md。

- [x] 全套测试、正常/胶囊/设置/菜单截图与高DPI验证。
- [x] 构建和验证冻结程序，重启本机桌宠并确认状态；发布v0.2.1和更新GitHub。
