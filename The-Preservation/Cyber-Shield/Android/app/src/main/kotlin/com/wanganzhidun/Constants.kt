package com.wanganzhidun

/**
 * 全局常量与配置键。
 * 红线约束：所有取证仅用于恶俗目标；反伤必须手动确认；不伪造证据。
 */
object Constants {

    // 录屏循环缓冲参数（可按设备性能在配置中覆写）
    const val CAPTURE_FPS = 10
    const val RING_CAPACITY = 45          // 环形缓冲帧数 ≈ 4.5s @10fps
    const val SNAPSHOT_FRAMES = 24        // 取证触发时回捞的帧数 ≈ 2.4s
    const val FRAME_MAX_DIM = 540         // 单帧最长边缩放上限，控制内存

    // 文件与目录
    const val KEYWORDS_FILE = "keywords.json"
    const val CONFIG_FILE = "config.json"
    const val EVIDENCE_DIR = "evidence"

    // 举报通道（官方合规通道，红线要求）
    const val URL_12377 = "https://www.12377.cn/"
    const val URL_TENCENT_GUARD = "https://110.qq.com/"

    // 通知渠道
    const val CHANNEL_FORENSICS = "forensics"
    const val CHANNEL_CAPTURE = "capture"

    // 反伤确认：必须用户手动点击才算数（红线）
    const val ACTION_REPORT = "com.wanganzhidun.action.REPORT"
    const val EXTRA_EVIDENCE_ID = "evidence_id"
    const val EXTRA_TARGET = "target"

    // 标准弹药默认关键词（占位示例，用户应改为自己的关键词论词表）
    val DEFAULT_KEYWORDS: List<String> = listOf(
        "加微信", "免费领取", "私聊返利", "转账返现"
    )
}
