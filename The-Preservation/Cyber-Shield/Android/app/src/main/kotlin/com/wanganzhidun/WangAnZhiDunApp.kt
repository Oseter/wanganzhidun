package com.wanganzhidun

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.wanganzhidun.core.CaptureOrchestrator

/**
 * 应用入口：建通知渠道、预热 Room、初始化取证编排中枢。
 */
class WangAnZhiDunApp : Application() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        CaptureOrchestrator.init(this)
        // 提前触发 Room 实例创建（Application 上下文）
        com.wanganzhidun.data.AppDatabase.getInstance(this)
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(
                Constants.CHANNEL_FORENSICS,
                getString(R.string.notify_channel_forensics),
                NotificationManager.IMPORTANCE_HIGH
            ).apply { description = "命中违规内容的取证提示" }
        )
        manager.createNotificationChannel(
            NotificationChannel(
                Constants.CHANNEL_CAPTURE,
                getString(R.string.notify_channel_capture),
                NotificationManager.IMPORTANCE_LOW
            ).apply { description = "循环缓冲录屏状态" }
        )
    }
}
