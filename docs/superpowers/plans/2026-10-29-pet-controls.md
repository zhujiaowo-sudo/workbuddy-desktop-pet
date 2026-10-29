# 桌宠交互 Implementation Plan
**Goal:** 完成已批准五项改动。
**Architecture:** state.py负责纯状态推导；menu/card/pet负责界面；Controller负责角色及偏好。沿用schema3与有界播放器。
**Tech Stack:** Python/PySide6/Pillow。
**Spec:** docs/plans/2026-10-29-pet-controls-design.md
## Global Constraints
保留两套角色、授权、回退目录；不把沉默当完成；不拆分角色关节。
## Review Focus
过期会话压过新任务；无积分显示；极简打开详情后返回；拖动释放误触点击；画布边缘裁切。
## Tasks
- [x] state.py：测试过期回退、并发新鲜活动与审批保留，再实现effective_state并回归。
- [x] ui/menu.py + app.py：动态角色子菜单，稳定key与勾选；测试两个内置及切换。
- [x] settings.py + ui/card.py：保存minimal偏好，圆形积分及未知值；测试重启、详情返回、隐藏恢复。
- [x] ui/pet.py：独立拖动动画，越过6px开始，整图抬升及轻摆，释放回弹；测试点击不误发与隐藏清理。
- [x] 替换thinking原GIF并更新审计hash，完整循环、原生帧及动作衔接检查。
- [x] 全量pytest、原生GUI验证、检查diff并提交实现。根据验证结果构建可测试安装包。
