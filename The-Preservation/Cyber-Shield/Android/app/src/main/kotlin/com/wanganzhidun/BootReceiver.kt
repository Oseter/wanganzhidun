package com.wanganzhidun

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * 开机重建监听（可选）。
 * 注意：MediaProjection 需要每次手动授权，无法在开机时自动重启录屏；
 * 此处保留扩展点，目前不做自动操作，避免越权。
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        if (intent?.action == Intent.ACTION_BOOT_COMPLETED) {
            // 扩展点：可在此弹出「重新授权录屏」提醒。
        }
    }
}
