package com.wanganzhidun.service

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.wanganzhidun.core.CaptureOrchestrator

/**
 * 聊天无障碍服务（关键词论）：读取对话界面文本，喂给取证编排中枢。
 * 启用入口：系统「设置 → 无障碍 → 已下载的应用」。
 * 红线：仅读取、仅做本地关键词匹配，不做任何上传或自动反伤。
 */
class ChatAccessibilityService : AccessibilityService() {

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return
        val root = rootInActiveWindow ?: return
        try {
            val sb = StringBuilder()
            traverse(root, sb)
            val text = sb.toString().trim()
            if (text.isNotBlank()) {
                CaptureOrchestrator.onText("chat:${event.packageName}", text)
            }
        } finally {
            root.recycle()
        }
    }

    private fun traverse(node: AccessibilityNodeInfo?, sb: StringBuilder) {
        node ?: return
        node.text?.let { sb.append(it).append(' ') }
        val count = node.childCount
        for (i in 0 until count) {
            traverse(node.getChild(i), sb)
        }
    }

    override fun onInterrupt() {
        // 服务被系统中断，无需处理
    }
}
