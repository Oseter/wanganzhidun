package com.wanganzhidun

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.wanganzhidun.core.ReportLauncher

/**
 * 反伤中转：仅当用户点「确认举报」才跳转官方通道（红线：反伤须手动确认）。
 * 透明主题，直接弹选择对话框。
 */
class ReportDispatchActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val target = intent.getStringExtra(Constants.EXTRA_TARGET).orEmpty()

        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.report_choose)
            .setMessage("目标：$target\n${getString(R.string.forensics_tap_confirm)}")
            .setPositiveButton(R.string.report_12377) { _, _ -> launchReport("12377") }
            .setNeutralButton(R.string.report_guard) { _, _ -> launchReport("guard") }
            .setNegativeButton(R.string.action_dismiss) { _, _ -> finish() }
            .setOnCancelListener { finish() }
            .show()
    }

    private fun launchReport(type: String) {
        startActivity(ReportLauncher.intent(this, type))
        finish()
    }
}
