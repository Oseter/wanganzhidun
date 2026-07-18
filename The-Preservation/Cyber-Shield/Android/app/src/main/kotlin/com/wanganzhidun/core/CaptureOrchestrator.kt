package com.wanganzhidun.core

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.wanganzhidun.Constants
import com.wanganzhidun.MainActivity
import com.wanganzhidun.ReportDispatchActivity
import com.wanganzhidun.data.EvidenceEntity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.io.File

/**
 * 取证反伤编排中枢：各监听服务把文本喂进来，命中关键词后
 * 1) 回捞循环缓冲帧  2) 归档为标准弹药  3) 弹出需手动确认的反伤通知（红线）。
 */
object CaptureOrchestrator {

    private lateinit var app: Context
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val seen = mutableMapOf<String, Long>()

    fun init(context: Context) {
        app = context.applicationContext
        KeywordEngine.load(File(app.filesDir, Constants.KEYWORDS_FILE))
    }

    /** 通知监听 / 无障碍服务统一入口 */
    fun onText(source: String, text: String) {
        if (text.isBlank()) return
        val hits = KeywordEngine.match(text)
        if (hits.isEmpty()) return

        val key = (source + text).hashCode().toString()
        val now = System.currentTimeMillis()
        val last = seen[key] ?: 0
        if (now - last < 30_000) return // 30s 内同内容去重
        seen[key] = now

        scope.launch { process(source, text, hits) }
    }

    /** 测试取证：注入一条合成命中，验证闭环（不针对任何真实目标） */
    fun testForensics() {
        onText("测试源@self", "【网安智盾自检】${Constants.DEFAULT_KEYWORDS.first()} 命中")
    }

    private suspend fun process(source: String, text: String, hits: List<String>) {
        val frames = CaptureBuffer.snapshot()
        val clause = "关键词论：${hits.joinToString("/")}"
        val entity = EvidenceArchiver.persist(
            app,
            target = source,
            content = text.take(200),
            clause = clause,
            frames = frames
        )
        postConfirmNotification(entity)
    }

    /** 反伤必须手动确认：通知仅提供「确认举报」动作，点击才跳转官方通道 */
    private fun postConfirmNotification(entity: EvidenceEntity) {
        val confirmIntent = Intent(app, ReportDispatchActivity::class.java).apply {
            action = Constants.ACTION_REPORT
            putExtra(Constants.EXTRA_EVIDENCE_ID, entity.id)
            putExtra(Constants.EXTRA_TARGET, entity.target)
        }
        val confirmPi = PendingIntent.getActivity(
            app,
            entity.id.toInt(),
            confirmIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val openIntent = Intent(app, MainActivity::class.java)
        val openPi = PendingIntent.getActivity(
            app,
            0,
            openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(app, Constants.CHANNEL_FORENSICS)
            .setSmallIcon(com.wanganzhidun.R.drawable.ic_notification)
            .setContentTitle(app.getString(com.wanganzhidun.R.string.forensics_title))
            .setContentText("${entity.target}：${entity.content.take(40)}")
            .setStyle(NotificationCompat.BigTextStyle().bigText(entity.content))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(openPi)
            .setAutoCancel(true)
            .addAction(
                com.wanganzhidun.R.drawable.ic_notification,
                app.getString(com.wanganzhidun.R.string.action_confirm_report),
                confirmPi
            )

        NotificationManagerCompat.from(app).notify(entity.id.toInt(), builder.build())
    }
}
