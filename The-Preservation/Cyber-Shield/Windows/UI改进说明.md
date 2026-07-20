# 网安智盾 · exe UI 改进说明（v2）

> 存护命途 · 防打号 / 防点号 / 反伤
> 本次仅改 **UI 层**（`ui/` 与 `main.py` 接线），不碰 `core/`、`db/` 取证/归档/举报逻辑。
> 红线守稳：不伪造证据、不自动举报、仅对恶俗攻击反制。

---

## 一、关于 apk

仓库里 **已有 Android 端**：`The-Preservation/Cyber-Shield/Android`
（Kotlin，AGP 8.5 + Kotlin 1.9 + KSP + Room + MediaProjection +
`NotificationListenerService` + `ChatAccessibilityService`，架构完成）。

- 编译产物 `WangAnZhiDun.apk` 由 `.github/workflows/android.yml` 自动构建，
  在对应 Actions 运行的 **Artifacts** / Releases 中下载，源码已入库。
- 即：**apk 有（源码 + CI 产物），不是只有 exe**。

---

## 二、改进清单（按文件）

### 1. `ui/main_window.py` — 主仪表盘
- 视觉升级：统一圆角卡片 + 细描边 + 盾蓝主色，品牌头更精致；
- 顶部大状态条「运行中 / 已暂停」+ 三细分状态药丸（监听 / 录屏 / 加密）；
- 统计卡带副标题（取证 / 证据 / 反伤）；
- **事件列表按类型着色**：取证=蓝、反伤=绿、测试=灰，含空状态提示；
- 快捷操作分组：主操作与「退出」危险操作分离，新增可选「证据库 / 关于」入口；
- 新增 `set_uptime()` 显示本次运行时长；
- 向后兼容：旧 `add_event(time, src, kw)` 调用方式仍可用。

### 2. `ui/confirm_dialog.py` — 反伤确认弹窗
- **标准弹药完整预览**：目标账号 / 时间 / 违规内容 / 对应条款 / 证据附件 一览；
- **证据缩略图**：截图/录像文件名 + 图片缩略图（最多 4 张）；
- 倒计时改 **进度条** + 剩余秒数；
- **键盘快捷键**：`Enter`=确认反伤，`Esc`=放弃；
- `ask_confirm` 新增可选参数 `evidence_files / target_account / event_time`（缺省不影响旧调用）。

### 3. `ui/tray.py` — 系统托盘
- 菜单增强：新增「立即测试取证 / 关于 / 重载配置」（回调缺失自动隐藏，向后兼容）；
- **暂停态图标变灰**：`set_running(False)` 切换为灰色盾牌，状态一眼可见。

### 4. `ui/icons.py` — 图标
- 盾牌增加顶部高光 + 内描边，更立体；
- 提供 `active / inactive` 两态（供托盘暂停灰态使用）。

### 5. `ui/config_window.py` — 配置窗
- 每个页签增加**说明横幅**；
- 字段用 `LabelFrame` **分组**，结构更清晰；
- 监测页新增「**载入推荐关键词**」按钮（本地合规词库，追加不覆盖）；
- 底部新增「恢复默认(录屏)」推荐参数；
- **保存逻辑与配置字段完全保持兼容**，热更新照旧。

### 6. `ui/manager.py` — UI 管理器
- `add_event` 增加 `kind` 参数（支持事件着色）；
- `ask_confirm` 增加可选 `evidence_files / target_account / event_time`，启用弹窗预览；
- 线程安全队列泵模型不变。

### 7. `main.py` — 入口接线（仅增强）
- `start()` 的 callbacks 增加 `on_view_db / on_about`；托盘 `TrayApp` 增加 `on_test / on_about / on_reload`；
- `_on_trigger` 中 `ask_confirm` 传入 `evidence_files / target_account / event_time`，启用标准弹药预览；反伤确认后插入一条 `kind="anti"` 着色事件；
- 新增 `_show_about / _reload_config / _view_reports / 运行时长刷新`；
- 代码中以 `# [UI改进]` 标记所有改动点，便于审阅。

---

## 三、如何合并到你的仓库

改进文件已放在本目录（与仓库相对路径一致），直接覆盖即可：

```
The-Preservation/Cyber-Shield/Windows/
├── main.py                  ← 覆盖（含 [UI改进] 标记）
└── ui/
    ├── main_window.py       ← 覆盖
    ├── confirm_dialog.py    ← 覆盖
    ├── tray.py              ← 覆盖
    ├── icons.py             ← 覆盖
    ├── config_window.py     ← 覆盖
    └── manager.py           ← 覆盖
```

方式 A（直接覆盖）：把上述 7 个文件复制进你的本地仓库对应位置，`git commit` 即可。
方式 B（PR）：在此 fork 上提交，向 `Oseter/wanganzhidun` 发 PR。

> 其余文件（`core/`、`db/`、`config.ini`、`build.spec`、`build.bat`、`installer.iss` 等）**未改动**，无需替换。

---

## 四、验证建议（Windows）

```bat
pip install -r requirements.txt
python main.py            # 开发模式，观察仪表盘/托盘/反伤弹窗
```

重点验证：
1. 托盘右键菜单出现「立即测试取证 / 关于 / 重载配置」；
2. 点「测试取证」→ 仪表盘出现灰色「测试」事件，证据目录生成截图；
3. 命中攻击关键词 → 反伤弹窗显示**标准弹药预览 + 证据缩略图 + 进度条**，Enter/Esc 可用；
4. 暂停监听 → 托盘图标变灰、状态条显示「已暂停」；
5. 设置页每页有说明横幅，监测页「载入推荐关键词」可追加。

打包仍用 `build.bat` → Inno Setup 编译 `installer.iss`（行为与旧版一致）。

---

## 五、红线自检

- 不改包 / 不爆破 / 不逆向：仅 UI 层调整，未触及任何第三方软件；
- 不伪造证据：缩略图/预览均来自真实取证文件；
- 不自动举报：反伤仍需用户在确认弹窗手动确认；
- 仅用于反制恶俗攻击：推荐关键词为防御性监测词，目标由用户在官方通道填写。
