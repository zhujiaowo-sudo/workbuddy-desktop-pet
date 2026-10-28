# 聊天跳转与动画修正 Implementation Plan

> 用户已选择聊天跳转WorkBuddy，直接在本会话实施。

**Goal:** 移除内置聊天，统一外部会话跳转；工作时坐下正向使用电脑，互动平滑无叠加弹跳。
**Architecture:** CardWindow只发跳转信号，Controller复用会话深链；AnimationPlayer管理混帧与过渡，素材生成器负责坐姿与脚底注册。
**Tech Stack:** Python3.12、PySide6、Pillow、内置imagegen、pytest、PyInstaller。
**Spec:** docs/plans/2026-10-28-chat-seated-motion-design.md。

## Global Constraints

- 无桌宠内聊天输入、模型配置或模型调用，旧配置不读取。
- 余额/签到权限与现有设置保持；不自动签到。
- 原素材保留，署名及AI派生改动明确，用户大小/图标/自启保留。

## Review Focus

- 所有聊天入口有会话跳对话、无会话开主程序：Task 1。
- 聊天点击不能展开面板，移除页后设置和签到索引不能错：Task 1。
- 隐藏和连续点击、跨动作过渡不抖动：Task 2。
- 坐姿帧桌椅不动、透明公共区域不能淡成半透明：Task 2。

### Task 1：聊天跳转

- [x] 删除内置聊天后端/UI及未支持的实验转发，保留原三用途本机积分接口。
- [x] 顶栏、右键、兼容open_page入口及--chat统一外部跳转，不创建新消息。
- [x] 验证无输入框、四页面索引、全部入口和无会话回退。

### Task 2：动画

- [x] 保存坐姿源图/提示词和署名，提取固定家具与轮廓的8帧，构建两档1.1.1素材及2.0.1模板。
- [x] 去除上下弹跳与叠加窗口运动，脚底注册，30fps混帧与180ms过渡。
- [x] 验证家具/轮廓固定、alpha、隐藏停止、源图完整及电脑方向。

### Task 3：交付

- [x] 完整回归、原生预览、冻结验证和本机更新，保留原设置与快捷方式。
- [x] 推送与Windows CI成功，发布v0.5.1并核验公开附件。

交付（2026-10-28）：代码d3717e6，原生118项回归与冻结程序验证通过；[Windows CI成功](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/actions/runs/40625627058/job/122609714031)。[v0.5.1公开发布](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/tag/v0.5.1)，6个附件的大小/SHA-256核对，匿名下载校验文件及默认轻量包成功并确认15动作。本机启用坐姿高清包并以chat_behavior=open-workbuddy运行，--chat跳转命令已发送，未发送消息；保留当前大小、关闭自启和原桌面快捷方式。
