package com.wanganzhidun.service

import android.app.Activity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.util.DisplayMetrics
import androidx.core.app.NotificationCompat
import com.wanganzhidun.Constants
import com.wanganzhidun.MainActivity
import com.wanganzhidun.R
import com.wanganzhidun.core.CaptureBuffer

/**
 * 循环缓冲录屏前台服务：通过 MediaProjection 持续抓取屏幕帧写入 CaptureBuffer。
 * 不依赖 OBS；取证触发时由 CaptureOrchestrator 回捞最近 N 帧归档。
 */
class CaptureService : Service() {

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private val handlerThread = HandlerThread("wazd-capture")
    private lateinit var handler: Handler
    private var running = false

    private val projCallback = object : MediaProjection.Callback() {
        override fun onStop() = stopSelf()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val resultCode = intent?.getIntExtra("resultCode", Activity.RESULT_CANCELED)
            ?: Activity.RESULT_CANCELED
        val data: Intent? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent?.getParcelableExtra("data", Intent::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent?.getParcelableExtra("data")
        }

        startForeground(NOTIFY_ID, buildNotification())

        if (resultCode == Activity.RESULT_OK && data != null) {
            startCapture(resultCode, data)
        } else {
            stopSelf()
        }
        return START_NOT_STICKY
    }

    private fun startCapture(resultCode: Int, data: Intent) {
        val mpm = getSystemService(MediaProjectionManager::class.java)
        mediaProjection = mpm.getMediaProjection(resultCode, data).also {
            it.registerCallback(projCallback, null)
        }

        val metrics = resources.displayMetrics
        val width = metrics.widthPixels
        val height = metrics.heightPixels
        val density = metrics.densityDpi

        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "WangAnZhiDun",
            width, height, density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader?.surface, null, null
        )

        handlerThread.start()
        handler = Handler(handlerThread.looper)
        running = true
        scheduleGrab()
    }

    private fun scheduleGrab() {
        val interval = (1000L / Constants.CAPTURE_FPS)
        handler.postDelayed(object : Runnable {
            override fun run() {
                grabFrame()
                if (running) handler.postDelayed(this, interval)
            }
        }, interval)
    }

    private fun grabFrame() {
        val reader = imageReader ?: return
        val image = reader.acquireLatestImage() ?: return
        try {
            val plane = image.planes[0]
            val buffer = plane.buffer
            val pixelStride = plane.pixelStride
            val rowStride = plane.rowStride
            val rowPadding = rowStride - pixelStride * reader.width

            val raw = Bitmap.createBitmap(
                reader.width + rowPadding / pixelStride,
                reader.height,
                Bitmap.Config.ARGB_8888
            )
            raw.copyPixelsFromBuffer(buffer)

            val clean = if (rowPadding == 0) raw else {
                val cropped = Bitmap.createBitmap(raw, 0, 0, reader.width, reader.height)
                raw.recycle()
                cropped
            }
            CaptureBuffer.push(clean, System.currentTimeMillis())
        } catch (_: Exception) {
            // 单帧失败忽略，继续下一帧
        } finally {
            image.close()
        }
    }

    override fun onDestroy() {
        running = false
        handlerThread.quitSafely()
        virtualDisplay?.release()
        imageReader?.close()
        mediaProjection?.unregisterCallback(projCallback)
        mediaProjection?.stop()
        CaptureBuffer.clear()
        super.onDestroy()
    }

    private fun buildNotification(): Notification {
        val openIntent = Intent(this, MainActivity::class.java)
        val pi = PendingIntent.getActivity(
            this, 0, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, Constants.CHANNEL_CAPTURE)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(getString(R.string.capture_running))
            .setContentIntent(pi)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    companion object {
        const val NOTIFY_ID = 2001
    }
}
