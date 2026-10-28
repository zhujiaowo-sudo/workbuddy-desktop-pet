# 多状态互动 Implementation Plan

> 用户已要求直接开发，本会话按原方式实施，不启动子代理。

**Goal:** 提供可见的电脑任务动画、4点击反应、4随机休闲及公开15动作模板。

**Architecture:** interaction.py维护纯调度；Controller根据真实会话选择动画；ui/animation_art.py负责原创道具与动作关键帧。materials.py校验schema1/2，模板及默认派生包共用动画渲染。

**Tech Stack:** Python3.12、PySide6、Pillow、pytest、PyInstaller。

**Spec:** docs/plans/2026-10-28-rich-animation-design.md。

## Global Constraints

- schema1兼容；schema2准确15动作、256/512方形、8–16帧、40–200ms、总6400万像素。
- 左击约3秒；闲置45–110秒，动作6–10秒；done至少12秒；确认/等待/失败优先。
- 保留真实任务、账户授权、224大小、固定图标与原素材；不自动签到。
- 无网络生成动作，不提交私人数据。

## Review Focus

- 一个会话结束但另一个仍忙：Task 2通过所有会话判定。
- 点击期间出现确认、隐藏、换角色、拖动：Task 2/3取消覆盖并恢复当前状态。
- 静态、别名文件、错误画布或解码超限伪装完整包：Task 1逐项拒绝。
- 素材每段切换导致卡片偏移：Task 3对增强包使用统一包络。
- 模板授权错误覆盖薄荷形象：Task 4继续使用原创机器人CC0，薄荷派生保持BY署名。

### Task 1：规范与校验

Files: materials.py, docs/pet-pack.schema.json, tests/test_materials.py。

- [ ] 定义TASK_ACTIONS、CLICK_ACTIONS、LEISURE_ACTIONS、ALL_ACTIONS和回退表；STATES保留旧7状态接口。
- [ ] 新CharacterPack.schema默认1；validate_pack支持schema2完整规则；动作缺失按专用回退表。
- [ ] 测试兼容、15动作、缺项、静态、尺寸、帧数/时长/透明度/命名/循环/共享文件拒绝。

### Task 2：动作调度

Files: interaction.py, app.py, tests/test_interaction.py。

- [ ] IdleDirector注入random，维护下次与当前动作；45–110秒/6–10秒，不重复，阻塞即清空并重新计时。
- [ ] 4点击动作与短句，任务警示优先；判断所有会话和done12秒；休闲不替换任务文字。
- [ ] 合成时钟测试隐藏、忙碌、事件打断、重复选择、结束恢复与点击拖动。

### Task 3：可见动作与预览

Files: ui/animation_art.py, ui/pet.py, ui/animation.py, ui/materials.py。

- [ ] 原创向量电脑打字、零食、手机滑屏、伸展、音符、爱心等，参数progress；已有完整动作不叠加。
- [ ] 旧包/静态启用低频效果计时，隐藏停止；增强包统一稳定包络；预览下拉展示15动作和完整度。
- [ ] Qt测试不同帧、稳定停靠与隐藏计时。

### Task 4：模板、默认包与交付

Files: templates.py, tools/create_interactive_pack.py, examples/, docs/materials.md, README.md, NOTICE.md, licenses/, catalog.json, versions。

- [ ] CC0原机器人15动作模板与薄荷BY派生轻量/高清包，16帧×80ms，记录改动/来源，验证可导入。
- [ ] 全套测试与可视化检查；构建并验证冻结包，更新本机保留设置、快捷方式有效。
- [ ] 推送、Windows CI、发布v0.5.0，核验附件摘要和公开模板。
