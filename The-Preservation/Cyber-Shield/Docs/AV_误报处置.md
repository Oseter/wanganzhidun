# 网安智盾 Windows 版 · 杀软误报（去威胁）处置说明

> 适用：WangAnZhiDun.exe 被 Windows Defender / SmartScreen / Microsoft Edge 报为「恶意软件」。
> 结论先行：**没有一行代码能让未签名的 PyInstaller 程序被系统/Edge 完全信任**。
> 能做的工程降级见下表；唯一能消除 SmartScreen/Edge 红框的手段是**代码签名**。

---

## 一、为什么会被误报

网安智盾的合法功能，恰好与间谍/远控木马的行为特征高度重合，触发 AV 启发式：

| 程序行为 | 在 AV 眼里像 |
|----------|--------------|
| 常驻系统托盘、无控制台后台运行 | 木马常驻 |
| 监听 QQ/微信 通知栏（NotificationListener） | 信息窃取 |
| 截图 + 循环录屏 | 键盘/屏幕记录器 |
| SMTP 自动发邮件 | 外发泄密 |
| PyInstaller 单文件 temp 解包 | 下载器/释放器 |

叠加「**未签名**」这一条，Defender/SmartScreen/Edge 会直接给红框。这是系统信任模型决定的，不是代码 bug。

---

## 二、本轮已落地的工程降级（不靠签名也能降一大截）

已修改 `Windows/build.spec`、`installer.iss`、CI `build.yml`，并新增资源文件：

| 措施 | 改动 | 效果 |
|------|------|------|
| **关掉 UPX** | `build.spec`: `upx=False` | UPX 压缩包被大量 AV 直接判恶意，关掉砍掉大部分启发式命中 |
| **嵌入 asInvoker 清单** | `resources/manifest.xml` | 不请求管理员权限，避免「提权 = 可疑」 |
| **填版本信息** | `resources/version_info.txt` | 匿名 exe 比带完整公司/版本/版权的更易被拦 |
| **改用 onedir** | `build.spec` 改 `COLLECT` + `installer.iss` 取 `dist\WangAnZhiDun\*` | 单文件要在 temp 解包，是经典触发点；目录版运行期不再解包 |
| **接好签名位** | `sign_windows.ps1` + CI 签名步骤（按 secret 开关） | 拿到证书一行命令/一次推送即可签 |

> 这些只能**降低误报概率**，不能消除对「未签名程序」的 SmartScreen/Edge 信任警告。

---

## 三、唯一可靠的「去威胁」手段：代码签名（Authenticode）

### 1. 买证书
- **EV 代码签名证书**：自带即时 SmartScreen 信誉，装好就能让红框消失（最省心，价格高）。
- **普通 DV/OV 代码签名证书**：需积累下载量/信誉后 SmartScreen 才不弹（前期仍可能提示「未知发布者」）。
- 签发机构：DigiCert、Sectigo、GlobalSign 等。拿到 `.pfx`（含私钥 + 密码）。

### 2. 本地签名
```powershell
cd The-Preservation/Cyber-Shield/Windows
$env:PFX_PATH = "D:\cert.pfx"
$env:PFX_PWD  = "证书密码"
.\sign_windows.ps1
```
脚本会定位 `signtool`、用 SHA256 + RFC3161 时间戳（证书过期后签名仍有效）签名
`dist\WangAnZhiDun\WangAnZhiDun.exe`。

### 3. CI 自动签名（推荐）
在仓库 **Settings → Secrets** 增加两项：
- `WIN_CERT_PFX`：pfx 的 **base64**（`[Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.pfx"))`）
- `WIN_CERT_PWD`：证书密码

下次推送即自动解码并签名；缺这俩 secret 时签名步骤自动跳过，**不影响普通构建**。

---

## 四、仍被拦时的补充手段

- **向 Microsoft 提交误报申诉**：
  https://www.microsoft.com/en-us/wdsi/filesubmission 选「误报」，上传 exe，建立文件信誉。
- **Edge / 浏览器下载警告**：签好名 + 一定下载量后自动消失；也可在 Edge 里「… → 保持」放行单次下载。
- **本机临时排除（仅调试用，非分发方案）**：Windows 安全中心 → 病毒和威胁防护 →
  「管理设置」→「排除项」→ 添加网安智盾目录。仅自己机器有效，不能发给别人。

---

## 五、顺带修复：「exe 窗口没弹出来」

现象：双击 exe 后进程在跑（托盘可能也在），但**主窗口不显示**。根因是 UI 线程
启动期任意异常（多为 PyInstaller 漏打包隐性依赖）被 `console=False` 静默吞掉，
`_ready` 事件永不触发。

修复（`Windows/ui/manager.py` + `main.py`）：
- UI 线程 `_run` 整体包 try/except，异常写 `wangzhidun_crash.log`（exe 同目录）；
- `start()` 检测到启动异常即抛出，`main()` 用 messagebox 把错误**显示给用户**后退出，
  不再「无界面假死」；
- 正常启动时强制 `deiconify()/lift()` 把窗口顶到前台，避免躲在背后。

> 重新打包后若仍无窗口，看 exe 同目录的 `wangzhidun_crash.log`，里面就是真实原因
> （通常是某个 `ModuleNotFoundError`），据此补 `build.spec` 的 hiddenimports 即可。
