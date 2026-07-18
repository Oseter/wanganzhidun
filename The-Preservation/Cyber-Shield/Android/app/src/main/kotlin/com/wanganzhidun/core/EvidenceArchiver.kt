package com.wanganzhidun.core

import android.content.Context
import android.graphics.Bitmap
import com.wanganzhidun.Constants
import com.wanganzhidun.data.AppDatabase
import com.wanganzhidun.data.EvidenceEntity
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 证据归档：把一段取证落盘为「标准弹药」。
 * 标准弹药格式：目标账号|时间|违规内容|对应条款|证据附件
 * 附件包含帧截图（PNG）与可选的短视频（MP4，尽力而为）。
 */
object EvidenceArchiver {

    private val stampFmt = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
    private val isoFmt = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)

    suspend fun persist(
        context: Context,
        target: String,
        content: String,
        clause: String,
        frames: List<Frame>
    ): EvidenceEntity {
        val root = File(context.filesDir, Constants.EVIDENCE_DIR)
        val dir = File(root, "${stampFmt.format(Date())}_${(Math.random() * 1000).toInt()}")
        dir.mkdirs()

        val attaches = mutableListOf<String>()
        frames.forEachIndexed { i, frame ->
            val p = File(dir, "frame_%04d.png".format(i))
            p.outputStream().use { frame.bitmap.compress(Bitmap.CompressFormat.PNG, 90, it) }
            attaches.add(p.absolutePath)
        }

        // 尽力生成短视频
        val clip = File(dir, "clip.mp4")
        if (VideoClipEncoder.encode(frames, clip)) attaches.add(clip.absolutePath)

        // A4 修复：frames 来自 CaptureBuffer.snapshot() 的 24 帧深拷贝，PNG/MP4
        // 编码均已完成，此处回收副本 Bitmap 释放显存（VideoClipEncoder 内部转
        // NV21 不回收输入，回收安全）。
        frames.forEach { it.bitmap.recycle() }

        val time = isoFmt.format(Date())
        val ammo = "$target|$time|$content|$clause|${attaches.joinToString(";")}"
        File(dir, "ammo.txt").writeText(ammo)

        val entity = EvidenceEntity(
            target = target,
            time = time,
            content = content,
            clause = clause,
            attachments = attaches.joinToString(";")
        )
        val id = AppDatabase.getInstance(context).evidenceDao().insert(entity)
        return entity.copy(id = id)
    }
}
