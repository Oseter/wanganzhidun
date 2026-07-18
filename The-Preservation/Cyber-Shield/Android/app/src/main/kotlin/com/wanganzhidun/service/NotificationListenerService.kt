package com.wanganzhidun.service

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.wanganzhidun.core.CaptureOrchestrator

/**
 * 通知监听（命途·存护 侦察）：捕获目标账号的推送正文，喂给取证编排中枢。
 * 启用入口：系统「设置 → 通知使用权」。
 */
class NotificationListenerService : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        val pkg = sbn.packageName ?: return
        val extras = sbn.notification.extras ?: return

        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString().orEmpty()
        val big = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString().orEmpty()
        val combined = "$title $text $big".trim()

        if (combined.isNotBlank()) CaptureOrchestrator.onText(pkg, combined)
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // 无需处理
    }
}
