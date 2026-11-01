# Installer Implementation Plan
**Goal:** 提供用户已批准的当前用户中文EXE安装向导。
**Architecture:** Inno Setup负责文件、快捷方式、卸载；setup.py复用现有接入与设置；旧ZIP更新保留卸载器。
**Tech Stack:** Python/PySide6、Inno Setup7。
**Spec:** docs/plans/2026-11-01-installer-design.md
- [x] 新增setup.py与CLI setup入口，测试首次授权/旧用户保留/失败/卸载所有权。
- [x] update.py暂存复制当前安装卸载文件并纳入哈希计划，测试更新保留。
- [x] installer/workbuddy.iss及tools/build_installer.py，中文向导最低权限任务复选框与失败反馈。
- [x] 新装/升级/卸载隔离演练、全量回归、构建ZIP及EXE，更新README与发行附件。

本地验收：188项回归正常退出、冻结程序检查通过；真实EXE在隔离合成目录完成安装、覆盖升级和卸载，保留授权、角色选择、用户素材及其他插件。修正用户目录常量；测试窗口在Qt应用销毁前释放，避免测试退出时的回调顺序错误。云端结果以对应提交的Windows CI为准。
