package com.wanganzhidun.core

import android.content.Context
import android.content.Intent
import android.net.Uri
import com.wanganzhidun.Constants

/**
 * 反伤通道：仅跳转到官方合规举报页（12377 / 腾讯卫士）。
 * 红线：必须由用户在 ReportDispatchActivity 中点「确认举报」才执行，不做自动反伤。
 */
object ReportLauncher {

    fun intent(context: Context, type: String): Intent {
        val url = when (type) {
            "guard" -> Constants.URL_TENCENT_GUARD
            else -> Constants.URL_12377
        }
        return Intent(Intent.ACTION_VIEW, Uri.parse(url))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
}
