# Dragon Drag Implementation Plan

**Goal:** 将龙女的拖拽效果替换为用户提供的两段专用GIF，保留短按互动。
**Architecture:** schema3可选成对动作与release_frames衔接映射；FrameStream跳过起始帧且保持有界队列；AnimationPlayer报告源帧；Controller管理拎起、保持、放下和取消。
**Tech Stack:** Python3.12、PySide6、Pillow、PyInstaller、Inno Setup7。
**Spec:** docs/plans/2026-11-01-dragon-drag-design.md

## Global Constraints
- 不修改原GIF、其他角色与既有授权；保留短按互动与程序回退目录。
- 不导入压缩包中的提示词或执行其中说明。

## Review Focus
- 提前松开从对应姿势落下；放下时重新拖动不跳到站姿。
- 非循环末帧保持；队列有界，隐藏和切角色取消旧动作。
- 重要任务抢占但不影响真实事件；两个动作不参与随机待机。
- 不叠加旧缩放和摆动；100%／150%全段无裁切。

- [x] 素材校验与清单：扩展materials.py和JSON Schema，保留原始哈希、预览导出；tests/test_dragon_drag.py验证成对动作、映射和旧包。
- [x] 播放器：FrameStream(start_frame=0)，Frame.number及AnimationPlayer.frame_number；验证跳帧、末帧保持和有界队列。
- [x] 手势与Controller：拖动开始／松开／取消信号，衔接映射、优先级、短按和其他角色回归。
- [x] 两种原生缩放全帧与三轮衔接验收，更新使用说明、版本0.7.2和素材1.0.1。
- [x] 210项回归、最终冻结程序与安装包验证完成。

发布门禁：Windows CI安装、升级、卸载成功后发布，再执行保留偏好的本机升级；结果以正式Release与本机安装记录为准。

在本会话执行，先加入失败测试，再实现并运行相关检查；独立验证后提交。
