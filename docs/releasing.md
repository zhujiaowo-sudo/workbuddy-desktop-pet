# Windows 构建与使用

## 构建

在 Windows x64 上安装 Python 3.12，使用较短路径创建虚拟环境，避免 Windows 路径长度限制：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.lock
.venv\Scripts\python -m pytest -q
.venv\Scripts\python tools/build_windows.py --work C:/wb-pet-build
```

产物为 `dist/workbuddy-desktop-pet-0.3.2-windows-x64.zip` 和 `dist/SHA256SUMS.txt`。完整解压后运行目录中的 `WorkBuddyDesktopPet.exe`，不可只复制单个 exe。程序使用动态 Qt 库，必须保留 `_internal` 和随包许可文件。

程序包提供薄荷星伴静态形象，不捆绑7状态人物动画。`仅卡片启动.vbs` 使用同一核心程序，仅隐藏人物；之后可在素材页启用角色。默认动画使用作者提供的原ZIP独立上传Release，附件与catalog.json的字节数及SHA-256必须一致。`python tools/create_pet_template.py` 只导出旧CC0机器人示例；其 `--catalog` 参数会显式切回旧示例清单，不用于发布薄荷星伴。

## 首次连接

1. 解压到固定位置。首次构建是未签名预览版，不修改系统安全设置。
2. 启动桌宠，右键角色或点数据小卡顶栏的齿轮打开设置。
3. 选择本机已经安装的 `WorkBuddy.exe`，保存设置。
4. 点击“连接 WorkBuddy”，它只添加本项目拥有的本地插件市场和启用条目，原有设置先备份。
5. 在 WorkBuddy 新建一个任务。如果始终没有收到事件，保存工作后重新打开 WorkBuddy，再发起新任务。
6. 点击角色进入数据模式，查看会话、剩余积分和今日消耗；顶栏统计图标展开详细看板。点击会话名称进入对应任务，“打开 WorkBuddy”唤起主程序。审批操作仍然在 WorkBuddy 内完成。

“演示”模式仅展示合成事件，不表示已连接。用户数据保存在 `%LOCALAPPDATA%/WorkBuddyDesktopPet`；源代码目录不保存 WorkBuddy 对话或登录凭据。

预览版接入使用解压位置生成运行命令，安装后请保持目录位置不变；目录迁移尚未验证。当前构建依赖 Windows 原生 ICU，已在 Windows 10 22H2 上验证。较旧 Windows 10 版本需另行测试。

## 命令行

```powershell
.\WorkBuddyDesktopPet.exe --demo
.\WorkBuddyDesktopPet.exe --settings
.\WorkBuddyDesktopPet.exe --card-only
.\WorkBuddyDesktopPet.exe --install-integration
.\WorkBuddyDesktopPet.exe --uninstall-integration
.\WorkBuddyDesktopPet.exe --quit
```

GUI 程序不一定显示控制台输出；源代码运行时可用 `python launch.py --diagnose` 查看不含对话内容的连接诊断。

## 移除

在桌宠设置中点击“移除接入”，然后退出桌宠。程序按安装记录移除自己的配置项，保留其他插件和安装后新增的设置；有冲突的用户修改不会强行覆盖。手动移除 WorkBuddy 已缓存的禁用插件可通过其插件管理页面进行。

若启用了登录自启，先在桌宠设置中关闭该项。确认程序退出后，可删除解压目录。用户目录中的设置、事件队列和备份可以由用户自行清理。

## 发布检查

- 本地测试通过；Windows CI 的状态单独以实际运行结果为准。
- 使用打包程序完成无 Qt 的 Hook 输入测试和 GUI 启动测试。
- `tools/build_windows.py` 会检查 ICU 接口冲突；发布前执行 `python tools/verify_package.py --scratch C:/wb-pet-smoke`，防止打包工具收集到 Git 的同名不兼容库。
- 在 `docs/compatibility.md` 中记录真实验证版本和事件，不把模拟结果写成实测结果。
- 压缩包仅包含本项目产物、动态依赖和许可文件；无本机设置、会话内容和凭据。
