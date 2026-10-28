# 首次绑定与自动更新 Implementation Plan

> 用户要求直接开发，在当前会话逐项实施。

**Goal:** 完成六项界面/安装/素材改进，并增加可重试、保留数据的应用更新。
**Architecture:** windows 负责发现，Settings 保存偏好，Controller 调度，独立 onboarding/update UI；update 模块处理验证与准备，独立 PowerShell 助手交换安装目录。动画仍采用公开透明源图与局部帧注册。
**Tech Stack:** Python 3.12、PySide6、Pillow、PowerShell、GitHub Releases、imagegen。
**Spec:** docs/plans/2026-10-28-setup-shortcuts-update-design.md。

## Global Constraints

- 不添加桌宠内模型调用；不自动领取签到；既有设置/素材/蓝色图标保留。
- 首次绑定清楚同意后读取本地票据，票据不上传/记录。
- 更新必须用户确认；只接受本仓库正式版本和校验通过的包。

## Review Focus

- 拒绝首次授权后不查询票据，仍能使用卡片。
- 胶囊隐藏与永久仅卡片不能混淆；展开后恢复。
- 自定义 URL 仅 HTTP(S)，签到按钮切换后不可误领取。
- 不完整下载、恶意 ZIP、安装目录无写权限必须保留当前程序。
- 目录交换失败需回退；更新资料只显示纯文本。

### Task 1：绑定与 UI

- [x] 增强发现候选，添加一次绑定引导和重新检测。
- [x] 右键收起人物/展开恢复/退出；快捷按钮设置及积分自适应。
- [x] 合成测试旧设置迁移、拒绝授权、收起恢复、按钮分发。

### Task 2：素材

- [x] imagegen 制作手机与零食坐姿源图，公开提示词及署名。
- [x] 局部帧注册，生成新版两档素材，验证固定身体与动作变化。

### Task 3：更新器

- [x] 实现正式版本发现、来源验证、后台下载/重试/取消、严格解压。
- [x] 更新对话框及自动/手动检查；下载完成重启安装。
- [x] PowerShell 独立事务交换、回退、保留数据，原生合成验证。

### Task 4：交付

- [x] 回归、原生截图、冻结验证、本机升级与设置保留。
- [x] 推送、CI、发布新版，核对公开校验值及匿名下载。

交付：代码提交 `c0e38314a691731ed92364a5a7a1e0746ee9d316`，[Windows CI成功](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/actions/runs/40629236615/job/122621445419)，[v0.6.0正式发布](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/tag/v0.6.0)。6附件大小/摘要与本地一致；匿名下载校验清单、15动作轻量包通过。实际更新器通过 latest 接口识别0.6.0，完整下载50,313,020字节程序包并校验SHA-256与进度100%。真实冻结包交换/重启及坏程序回退另在独立目录验证；本机0.6.0运行并可查询余额，保留大小150、自启关闭及原授权。公开源图及提示词见art/mint-orbit/leisure-v1.2.0.md。
