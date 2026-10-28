# 参考项目与素材说明

本仓库的程序、状态处理与基础角色均独立实现，不包含参考项目的程序代码、角色图片、视频或声音。

## 白龙桌宠

参考项目：https://github.com/Wunsch2048/codex-bailong-desktop-pet

研究范围包括 Windows 悬浮桌宠、工作状态展示、完成提醒、状态来源与界面解耦等实现思路。

该项目的来源及授权说明不等同于整套代码和角色素材采用通用开源许可。开发时应逐项核实所引入代码和素材的许可，不将参考项目整体标注为本项目自有内容。

本机已经安装的白龙桌宠及其用户设置不会因为本仓库初始化而被修改；本机素材也不上传至本仓库。

## WorkBuddy Buddy

参考项目：https://github.com/FlashFamily/workbuddy-buddy

参考其 WorkBuddy 事件接入与状态展示思路。其 README 标注代码采用 MIT 许可，角色素材按各素材包声明处理；如果后续实际引入代码，应保留对应版权和许可文件。

## 本项目新增内容

已独立实现 WorkBuddy 适配、Windows 卡片、统计和角色包系统。原“小搭子”机器人为独立程序绘制的原创形象，保留为资源缺失时的回退和创作模板；其导出图像与示例包以 CC0-1.0 提供，许可文本见 https://creativecommons.org/publicdomain/zero/1.0/legalcode 。此声明不覆盖新默认形象、整个程序代码、白龙人物或其他用户素材。

## 默认形象：薄荷星伴

作者：**Buddy娘**。版本：1.0.1。许可：**CC-BY-4.0**，见 https://creativecommons.org/licenses/by/4.0/ 。素材来自用户提供的高清ZIP及配套轻量ZIP，公开原包见[发布页](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/tag/v0.3.1)。

两档动画ZIP保持原始字节及清单不变。内置 `assets/mint-orbit-idle.png` 为高清待机动画首帧的透明PNG格式导出，未改绘角色。署名及来源说明随程序保留在 `licenses/mint-orbit/NOTICE.txt`。该形象不适用旧机器人素材的CC0声明。

v0.5.0另外提供**薄荷星伴互动版1.1.0**，为原1.0.1的派生包，继续采用CC-BY-4.0并署名Buddy娘。改动包括：各段重采样为16帧，叠加本项目原创程序绘制的电脑、零食、手机、爱心、音符及运动关键帧，扩展4种点击反应与4种休闲动作；并非原作者新绘制的15段动画。派生包manifest保留来源、许可链接与改动说明；原始ZIP不变。公开的15动作机器人创作模板使用独立原创角色，采用CC0-1.0。

本项目原创代码的正式开源发行许可尚未指定；当前未对未引入的第三方代码或素材授予任何许可。

v0.5.1的薄荷互动版1.1.1新增坐姿电脑工作姿势，为内置imagegen基于薄荷原形象生成的派生素材；按4×2网格提取8关键帧，去除孤立杂点、固定家具与外轮廓，局部合成眨眼及手部，点击动作去除上下弹跳。继续保留原作者Buddy娘和CC-BY-4.0；源图及完整提示词见[素材生成记录](art/mint-orbit/README.md)。用户坐姿参考图及其中的其他角色不随项目分发。

## 动态运行时依赖

PySide6 Essentials 与 Shiboken 采用其发行包声明的 LGPL/GPL/商业许可选项；本包保留动态库和许可说明，公共许可文本见 `licenses/`，Qt 源码见 https://code.qt.io/ 与 https://download.qt.io/official_releases/QtForPython/ 。正式源代码版本号和依赖锁定见 `requirements-dev.lock`。

Python 采用 PSF 许可；PyInstaller 使用带引导程序例外条款的 GPL 许可。程序包中的 Microsoft C/C++ 运行时源自 Qt 的 Windows 发行包，保留其原有运行时文件，不修改系统版本。

Pillow 按其发行包中的 HPND 及各附属图像库许可分发，打包时保留对应许可文本。
