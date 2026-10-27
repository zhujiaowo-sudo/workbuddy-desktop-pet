# 数据模式与胶囊 Implementation Plan

> 用户已要求本会话直接开发，沿用当前执行方式；不启动子代理。

**Goal:** 交付胶囊→数据小卡→展开看板三级蓝色界面。

**Architecture:** LocalDataReader独立计算日历日用量；CardWindow管理三种视图，Controller只连接刷新、页面与停靠事件。

**Tech Stack:** Python3.12、PySide6 Essentials、SQLite、pytest、PyInstaller。

**Spec:** docs/plans/2026-10-27-summary-card-design.md

## Global Constraints

- 不收集正文，不扩展余额授权范围，不改动WorkBuddy或其他桌宠。
- 无数据不冒充零；今日用量标注本机来源。
- 胶囊272×32，数据小卡320×202，展开360×540，单位为逻辑像素。

## Review Focus

- 午夜、昨天24小时内和未来请求的日期边界：Task 1。
- 缺时间不能混入今日，日期筛选不能改变今日：Task 1。
- 从胶囊及人物点击必须进入数据模式，菜单保持指定页面：Task 2。
- 看板返回、反复切换和透明间隙不残留背景：Task 2。
- 仅卡片、DPI和显示器边界不越界：Task 3。

### Task 1: 本机今日用量

Files: src/workbuddy_pet/local_data.py, tests/test_local_data.py。

- [x] 添加测试：本地零点前后、未知时间、重复请求、未来请求，全部/7/30天快照今日值一致。
- [x] 在UsageSnapshot尾部新增today_credit、today_requests、today_date；同一遍历独立计算今日数值，保留旧接口。
- [x] 运行本地数据测试，确认只读和元数据缓存不回归。

### Task 2: 三级蓝色界面

Files: src/workbuddy_pet/ui/card.py, src/workbuddy_pet/ui/icons.py, src/workbuddy_pet/app.py, src/workbuddy_pet/ui/pet.py, tests/test_card.py。

- [x] 测试胶囊→summary→expanded→summary→capsule和右键页面选择；断言数字余额及透明像素。
- [x] 新增mode、open_summary、set_mode；set_compact(False)兼容为summary。保留tabs接口，展开区域在数据小卡上方；图形快捷键带提示和无障碍名称。
- [x] Controller.open_card进入summary，open_page保留所选页；统一刷新读取统计与余额，点击余额进入summary并刷新。
- [x] 更新截图入口支持summary，运行Qt导航、余额、停靠回归。

### Task 3: 验证与发布

Files: README.md, docs/releases/v0.3.0.md, pyproject.toml, src/workbuddy_pet/__init__.py。

- [x] 合成数据截图核对胶囊/summary/看板/设置及1.5倍DPI；运行全套测试。
- [x] 构建冻结程序并验证，保存用户设置后重启当前桌宠，确认真实余额可用。
- [x] 提交推送，检查CI并发布v0.3.0程序包和校验文件。

交付：代码82d005d；[Windows构建与测试通过](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/actions/runs/40494544400)；[v0.3.0公开下载](https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/tag/v0.3.0)。本机版本、连接与余额可用状态均已核对，未输出个人积分或票据。
