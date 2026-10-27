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

已独立实现 WorkBuddy 适配与 Windows 桌宠界面。首版角色为程序绘制的基础形象；额外人物素材的本地导入为后续扩展方向，不随仓库默认提交。

本项目原创代码的正式开源发行许可尚未指定；当前未对未引入的第三方代码或素材授予任何许可。

## 动态运行时依赖

PySide6 Essentials 与 Shiboken 采用其发行包声明的 LGPL/GPL/商业许可选项；本包保留动态库和许可说明，公共许可文本见 `licenses/`，Qt 源码见 https://code.qt.io/ 与 https://download.qt.io/official_releases/QtForPython/ 。正式源代码版本号和依赖锁定见 `requirements-dev.lock`。

Python 采用 PSF 许可；PyInstaller 使用带引导程序例外条款的 GPL 许可。程序包中的 Microsoft C/C++ 运行时源自 Qt 的 Windows 发行包，保留其原有运行时文件，不修改系统版本。
