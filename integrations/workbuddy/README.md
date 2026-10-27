# WorkBuddy 本地状态插件

桌宠启动后在设置中点击“连接 WorkBuddy”，或从源码执行 `python launch.py --install-integration`。

程序生成一个独立本地插件市场，包含标准 `.codebuddy-plugin/marketplace.json`、插件的 `.codebuddy-plugin/plugin.json` 和 `hooks/hooks.json`，再将本项目条目合并到 WorkBuddy 用户设置的 `extraKnownMarketplaces` 和 `enabledPlugins`。不直接改写 WorkBuddy 的插件安装注册表或其他插件内容。

所有运行时路径由安装时生成，存放在桌宠用户目录中；仓库不提交机器专属路径或用户配置。重复安装复用首次备份，卸载保留安装后用户自行修改的其他配置。

当前 Windows 主机可能使用 PowerShell 而非 Git Bash 来运行 Hook。命令使用固定 PowerShell 编码脚本传递字面参数，兼容这两种调用外壳。Hook 不把原始事件内容拼成命令，不返回工具审批决策。

事件处理程序先执行 64 KiB 输入限制和白名单投影，再写入本地有界队列。Qt 界面模块不会在 Hook 模式加载。每条 Hook 的超时为 5 秒；50 ms 的限制仅针对文件锁等待，不含进程和外壳启动时间。

官方参考：

- https://www.codebuddy.cn/docs/workbuddy/Plugins
- https://www.codebuddy.cn/docs/cli/plugins-reference
- https://www.codebuddy.cn/docs/cli/plugin-marketplaces
- https://www.codebuddy.cn/docs/cli/hooks

桌面版事件实测结果见 `docs/compatibility.md`，不以 CLI 文档替代桌面版验证。
