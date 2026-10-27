# 薄荷星伴默认形象 Implementation Plan

> 用户已指定直接开发与上传，沿用本会话执行方式，不启动子代理。

**Goal:** 上传两档默认动画包，本机启用高清，新安装显示薄荷星伴。

**Architecture:** 内置静态PNG和可选动画分离；沿用MaterialLibrary及现有设置，下载清单固定大小和SHA-256。

**Tech Stack:** Python3.12、PySide6、Pillow、PyInstaller。

**Spec:** docs/plans/2026-10-27-mint-default-design.md。

## Global Constraints

- 用户ZIP不改写；作者Buddy娘、许可CC-BY-4.0保持。
- 仅卡片不加载人物动画，不修改WorkBuddy、余额授权和其他角色。
- 只更新本项目GitHub Release，不上传对话、设置、密钥或制作工程文件。

## Review Focus

- 首次离线运行和缺少资源的回退：Task 1。
- 创作模板继续为原CC0机器人，不错误许可新图：Task 1。
- 下载地址不能跳到其他仓库，字节及摘要不匹配拒绝导入：Task 2。
- 原用户选择和仅卡片设置保留：Task 3。
- 公开附件摘要与原包一致：Task 3。

### Task 1: 默认静态形象

Files: ui/pet.py, ui/materials.py, templates.py, assets/mint-orbit-idle.png, NOTICE.md, licenses/mint-orbit/NOTICE.txt。

- [x] 提取高清idle首帧，保留透明；默认PetWindow及素材预览显示新图，缺文件回退旧矢量。
- [x] 模板显式关闭新静态图，保留原CC0内容；测试两种分支及静态图不空。
- [x] 将静态资源纳入wheel及冻结程序，验证仅卡片不加载动画。

### Task 2: 默认下载目录

Files: catalog.json, material_download.py, tests/test_material_download.py, docs/materials.md。

- [x] 清单改为v0.3.1发布下的两个原ZIP，大小及SHA与原包一致。
- [x] 下载路径限制本仓库语义版本Release；测试成功、其他仓库及摘要/大小错误。
- [x] 更新署名、默认素材说明和版本0.3.1。

### Task 3: 本机与公开发布

- [x] 本机导入高清包并保存为当前默认角色；仅更改character和必要的显示开关。
- [x] 全套测试、合成界面及冻结程序验证，构建后重启本机，确认新动画已加载。
- [x] 推送代码，CI通过后公开核心和原素材ZIP，核验匿名下载及摘要。

交付：代码1150bfc；[Windows CI通过](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/actions/runs/40508229515)；[v0.3.1公开发布](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/tag/v0.3.1)。两档素材均已通过程序的真实匿名下载、SHA-256校验和7状态导入；高清内容标识与本机启用角色一致。75项测试及冻结程序验证通过，本机非演示模式动画已加载，其他设置保留。
