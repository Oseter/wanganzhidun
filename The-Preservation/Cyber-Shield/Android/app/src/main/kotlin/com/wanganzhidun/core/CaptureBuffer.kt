package com.wanganzhidun.core

import android.graphics.Bitmap
import com.wanganzhidun.Constants
import java.util.ArrayDeque

/**
 * 循环缓冲录屏的帧环：录屏服务持续写入，取证触发时回捞最近 N 帧。
 * 内置 ImageReader 的 Bitmap 会被复用，故写入前必须拷贝。
 */
data class Frame(val bitmap: Bitmap, val ts: Long)

object CaptureBuffer {

    private val lock = Any()
    private val deque = ArrayDeque<Frame>()
    private val capacity = Constants.RING_CAPACITY

    fun push(src: Bitmap, ts: Long) {
        val copy = scaleAndCopy(src)
        synchronized(lock) {
            deque.addLast(Frame(copy, ts))
            while (deque.size > capacity) {
                deque.removeFirst().bitmap.recycle()
            }
        }
    }

    /** 取证触发时回捞最近 count 帧（深拷贝，避免被回收） */
    fun snapshot(count: Int = Constants.SNAPSHOT_FRAMES): List<Frame> {
        synchronized(lock) {
            val list = deque.toList()
            val take = list.takeLast(count.coerceAtMost(deque.size))
            return take.map { f ->
                Frame(f.bitmap.copy(f.bitmap.config ?: Bitmap.Config.ARGB_8888, false), f.ts)
            }
        }
    }

    fun size(): Int = synchronized(lock) { deque.size }

    fun clear() {
        synchronized(lock) {
            while (deque.isNotEmpty()) deque.removeFirst().bitmap.recycle()
        }
    }

    private fun scaleAndCopy(src: Bitmap): Bitmap {
        val max = Constants.FRAME_MAX_DIM
        val w = src.width
        val h = src.height
        if (w <= max && h <= max) return Bitmap.createBitmap(src)
        val ratio = max.toFloat() / maxOf(w, h)
        return Bitmap.createScaledBitmap(src, (w * ratio).toInt(), (h * ratio).toInt(), true)
    }
}
