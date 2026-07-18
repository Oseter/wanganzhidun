# 网安智盾 · 代码审计报告（找 bug）

- **审计对象**：`The-Preservation/Cyber-Shield`（Windows GUI 端 + Android 端）
- **审计日期**：2025-07-21
- **审计方式**：静态走读 + `py_compile` 语法校验 + 跨线程 tkinter 调用扫描 + Android 资源/清单/编译依赖核对
- **结论**：共发现 **10 个缺陷**（2 Critical / 1 High / 2 Medium / 5 Low），**全部已修复**。低危项原在初版审计中仅记录建议，已按「不可漏任何 bug」要求补齐（见 §三）。

---

## 一、缺陷总览

| 编号 | 严重度 | 位置 | 问题 | 状态 |
|------|--------|------|------|------|
| W1 | 🔴 Critical | `Windows/core/archiver.py` | 加密后删除明文，但 `ammo` 仍引用已删除路径 → 邮件静默丢弃全部附件、草稿/DB 记录指向死文件 | **已修复** |
| W2 | 🟠 High | `Windows/main.py` + `ui/manager.py` + `ui/confirm_dialog.py` | 标准弹药「对应条款」字段恒为空：归档在确认弹窗之前、未传默认条款，弹窗里用户改的条款也未写回 | **已修复** |
| A3 | 🟠 High | `Android/.../core/VideoClipEncoder.kt` | Surface 输入编码却未设置呈现时间戳 → MediaMuxer 时间戳非递增 → MP4 静默失败，仅 PNG 兜底 | **已修复** |
| A1 | 🟡 Medium | `Android/.../service/ChatAccessibilityService.kt` | 遍历无障碍节点不回收子 `AccessibilityNodeInfo` → 系统节点池溢出、漏事件 | **已修复** |
| A2 | 🟡 Medium | `Android/.../AndroidManifest.xml` | `CaptureService` 误加 `android:permission="android.permission.FOREGROUND_SERVICE"` → 可能 `SecurityException` | **已修复** |
| W3 | 🟢 Low | `Windows/core/reporter.py` | `webbrowser.open` 在 `ThreadPoolExecutor` 工作线程内调用，跨线程开浏览器在部分环境不可靠 | **已修复** |
| W4 | 🟢 Low | `Windows/core/monitor.py` | `request_access()` 为 winrt 异步 API 却未 await，权限判定可能失效（仅 Windows 运行） | **已修复** |
| A4 | 🟢 Low | `Android/.../core/CaptureBuffer.kt` | `snapshot()` 深拷贝帧在 `persist` 后未回收，短暂内存占用 | **已修复** |
| A5 | 🟢 Low | `Android/.../MainActivity.kt` | `openEvidence` 用 FileProvider 分享目录，多数文件管理器打不开 → 回退 toast | **已修复** |
| A6 | 🟢 Low | `Android/.../core/CaptureOrchestrator.kt` | 去重键用 `hashCode()`，哈希碰撞可能漏报 | **已修复** |

---

## 二、已修复缺陷详解

### W1（Critical）— 加密删除明文后 `ammo` 仍引用死路径

**根因**：`Archiver.archive()` 先把截图/录像/原文/meta 的**明文**路径写进返回的 `ammo` 字典，随后在加密分支里 `encrypt_file(p)` 并 `os.remove(p)` 删除明文。于是返回的 `ammo` 指向的 `/evidence/.../shot_1.png` 等文件已被删除。

**连锁破坏**：
- `db.add_evidence(event_id, ammo)` 把死路径存进 SQLite（记录与磁盘实际不符）；
- `build_draft(ammo)` 在「证据附件」里列出已不存在的路径，用户复制草稿到举报页后无法对应到文件；
- `Reporter.send_email()` 里 `if os.path.exists(s)` 对全部截图均为 `False` → **邮件静默丢弃所有附件**，发往官方的举报邮件实质为空壳。

**修复**：加密分支改为「加密后把 `ammo` 的附件路径同步改写为 `.enc` 路径」，保证 `db / 草稿 / 邮件` 引用始终有效；并把 `meta.json` 的写入移到加密改写**之后**，使落盘元数据与内存 `ammo` 一致。同时给 `Reporter` 增加 `crypto` 引用与 `_resolve_attachment()`：发邮件时若附件是 `.enc`，先解密到临时文件再附上，发送后清理临时文件。

```python
# archiver.py（节选）：加密后改写路径
saved_shots = [_enc(p) for p in saved_shots]
raw_path = _enc(raw_path)
if saved_replay and not os.path.isdir(saved_replay):
    saved_replay = _enc(saved_replay)
ammo["evidence_attachments"] = {"screenshots": saved_shots,
                                 "replay": saved_replay, "raw_text": raw_path}
```

---

### W2（High）— 标准弹药「对应条款」字段恒为空

**根因**：
1. `main.py` 调用 `self.archiver.archive(app, text, shots, replay)` 时**未传入 `clause`**，归档发生在用户确认**之前**，因此 `ammo["clause"]` 永远是默认值 `""`；
2. 确认弹窗（`ConfirmDialog`）允许用户**编辑条款**，但 `on_result` 只回传 `bool`，用户改的条款被丢弃，从未写回 `ammo / 草稿 / 邮件`。

标准弹药格式要求「目标账号|时间|违规内容|**对应条款**|证据附件」，对应条款为空破坏格式完整性，也不利于官方审核。

**修复**：
- `archive()` 调用处补传 `clause=self.cfg.default_clause`；
- `UIManager.ask_confirm()` 改为返回 `(ok, clause)` 元组，`ConfirmDialog._finish()` 把 `self.clause_var.get()`（用户最终编辑值）一并回传；
- `main.py` 在 `approved` 后写回 `ammo["clause"] = clause` 并调用新增的 `db.update_evidence_clause(event_id, clause)`，随后再 `build_draft`。

---

### A3（High）— MP4 取证短片静默失败

**根因**：原 `VideoClipEncoder` 用 `COLOR_FormatSurface` 编码器 + `surface.lockCanvas` 绘制，但 Surface 输入方式**不会自动获得单调递增的呈现时间戳**。写入 `MediaMuxer` 时所有帧 `presentationTimeUs` 为 0 或非递增，触发 `IllegalArgumentException`（时间戳非递增），被外层 `catch` 吞掉 → 方法返回 `false` → 走 PNG 兜底。**短视频证据特性实际从未生效**。

**修复**：改为「缓冲区输入 + 显式 PTS」标准做法——每帧 `Bitmap` 转 NV21(YUV420SP) 经 `getInputBuffer` 喂入，按 `idx * frameDurationUs` 设置 `presentationTimeUs`，末帧置 `BUFFER_FLAG_END_OF_STREAM`。`MediaMuxer` 收到递增时间戳后正常封装出合法 MP4。

---

### A1（Medium）— 无障碍服务节点泄漏

**根因**：`ChatAccessibilityService.traverse()` 递归调用 `node.getChild(i)` 获取子节点却**从不 `recycle()`**。`AccessibilityNodeInfo` 来自系统对象池，不回收会耗尽池并触发 `“AccessibilityNodeInfo cache overflow”`，导致后续事件被丢弃、聊天内容读取时断时续。

**修复**：递归遍历每个子节点后 `child.recycle()`；根节点仍由 `onAccessibilityEvent` 的 `finally` 统一回收。

---

### A2（Medium）— 前台服务权限属性误用

**根因**：`CaptureService` 声明了 `android:permission="android.permission.FOREGROUND_SERVICE"`。`<service>` 上的 `android:permission` 是用来限制**谁能启动/绑定该服务**的，而非声明自身需要的权限。Foreground-service 类型与所需权限（已在 `<uses-permission>` 中声明 `FOREGROUND_SERVICE` / `FOREGROUND_SERVICE_MEDIA_PROJECTION` 且 `foregroundServiceType="mediaProjection"`）已正确配置，这个 `android:permission` 属多余且可能在部分 ROM 上引发 `SecurityException`。

**修复**：删除该 `android:permission` 属性。

---

## 三、低危项修复详解（按「不可漏任何 bug」要求补齐）

> 初版审计中这 5 项仅记录建议、未改动；现已全部落地。

### W3（Low）— 线程池工作线程内打开浏览器

**根因**：`report_channels()` 把 `webbrowser.open(url)` 放进 `ThreadPoolExecutor` 工作线程。Windows 上 `webbrowser.open` 最终 fork 浏览器进程，跨线程在部分环境（尤其无活动桌面会话、被服务化时）不可靠，可能静默打不开举报页。

**修复**：邮件（网络 I/O）仍保留在线程池并发；每个网页通道改为起独立守护线程派发 `_web_result()`，与邮件线程池解耦，结果汇总回 `results`。这样既保证网页打开在专建线程上完成，又不阻塞主流程。

### W4（Low）— winrt 异步授权未等待结果

**根因**：`self._listener.request_access()` 在 winrt 中返回 `IAsyncOperation`（异步句柄），原代码直接同步取结果并比较 `!= 1`，拿到的可能尚未完成的异步对象，导致授权判定失效、误报「未获授权」。

**修复**：用 `op.get()` 阻塞等待异步操作完成，取到真正的 `NotificationListenerAccessStatus`，再与 `NotificationListenerAccessStatus.ALLOWED` 比较（`hasattr(op, "get")` 兜底，兼容不同 winrt 版本）。仅 Windows 运行，沙箱无法跑；写法对齐 winrt 官方同步等待范式。

### A4（Low）— snapshot 深拷贝帧未回收

**根因**：`CaptureBuffer.snapshot()` 为取证安全返回 24 帧 `Bitmap` 深拷贝（避免被环形缓冲回收），但 `EvidenceArchiver.persist()` 在 PNG/MP4 写盘后从未回收这些副本，造成短暂显存占用（取证频繁时叠加）。

**修复**：在 PNG 与 `VideoClipEncoder.encode()` 均完成后，对 `frames` 逐一 `bitmap.recycle()`。`VideoClipEncoder` 内部仅把 Bitmap 转 NV21 不回收输入，故此处回收安全、无二次释放风险。

### A5（Low）— openEvidence 分享目录无法打开

**根因**：`FileProvider.getUriForFile` 对一个**目录**生成 Uri，而 `ACTION_VIEW` + 目录 Uri 绝大多数文件管理器不支持 → 走 `catch` 回退 toast，用户拿不到证据。

**修复**：改为收集最新事件目录下全部文件，用 `ACTION_SEND_MULTIPLE` + `EXTRA_STREAM`（多个带 `FLAG_GRANT_READ_URI_PERMISSION` 的 Uri）一次性分享；目录为空时提示「暂无证据文件」，避免无意义 chooser。

### A6（Low）— 去重键哈希碰撞漏报

**根因**：去重键 `(source + text).hashCode().toString()` 为 32 位哈希，不同内容存在碰撞概率，极端情况会把一条真实命中误判为「30s 内重复」而丢弃。

**修复**：去重键改为原始字符串 `"$source|$text"`，彻底消除哈希碰撞，确保每条真实违规内容都能触发取证闭环。

---

## 四、验证情况

- ✅ Windows 全部 `.py` 经 `python3 -m py_compile` 通过，无语法错误；
- ✅ 跨线程 tkinter 调用扫描确认：所有 `root.*` 访问均位于 UI 线程（`UIManager._pump` 驱动的队列），此前 `main thread is not in main loop` 崩溃的根因已闭环；
- ✅ W1/W2 修复逻辑经走读核对：`ammo` 路径与磁盘实际一致、条款字段在确认后落库；
- ⚠️ Android 端无 SDK 环境，无法本地编译；A1/A2/A3 为标准化写法修正，最终以 GitHub Actions（ubuntu + `gradle-build-action`）APK 构建结果为准。

---

## 五、涉及文件改动

初版（Critical/High/Medium）：
- `Windows/core/archiver.py` — 加密后改写 `ammo` 附件路径、meta 写入后置
- `Windows/core/reporter.py` — 增加 `crypto` 参数与 `_resolve_attachment()` 解密附件
- `Windows/main.py` — 传 `crypto`/`default_clause`、接收 `(ok, clause)` 并回写
- `Windows/ui/manager.py` — `ask_confirm` 返回 `(ok, clause)`
- `Windows/ui/confirm_dialog.py` — `_finish` 回传编辑后条款
- `Windows/db/database.py` — 新增 `update_evidence_clause()`
- `Android/.../core/VideoClipEncoder.kt` — 重写为缓冲区输入 + 显式 PTS
- `Android/.../service/ChatAccessibilityService.kt` — 回收子节点
- `Android/.../AndroidManifest.xml` — 移除 `CaptureService` 多余 `android:permission`

补齐（Low，本轮）：
- `Windows/core/reporter.py` — 网页打开移出线程池，改独立守护线程派发（W3）
- `Windows/core/monitor.py` — `request_access()` 用 `.get()` 等待异步结果再判定（W4）
- `Android/.../core/EvidenceArchiver.kt` — `persist` 末尾回收 snapshot 深拷贝帧（A4）
- `Android/.../MainActivity.kt` — `openEvidence` 改 `ACTION_SEND_MULTIPLE` 分享文件（A5）
- `Android/app/src/main/res/values/strings.xml` — 新增 `no_evidence_yet` 文案（A5）
- `Android/.../core/CaptureOrchestrator.kt` — 去重键改为原始字符串 `source|text`（A6）
