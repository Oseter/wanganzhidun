package com.wanganzhidun.core

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import com.wanganzhidun.Constants
import java.io.File

/**
 * 把回捞到的帧编码成一段 MP4 短视频（取证补充证据）。
 * 纯尽力而为：任何异常都返回 false，调用方已有 PNG 帧兜底，绝不影响取证闭环。
 */
object VideoClipEncoder {

    private const val TIMEOUT_US = 10_000L

    fun encode(frames: List<Frame>, out: File, fps: Int = Constants.CAPTURE_FPS): Boolean {
        if (frames.isEmpty()) return false
        return try {
            val first = frames.first().bitmap
            val w = first.width
            val h = first.height

            val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, w, h).apply {
                setInteger(MediaFormat.KEY_BIT_RATE, 2_000_000)
                setInteger(MediaFormat.KEY_FRAME_RATE, fps)
                setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
                setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
            }

            val encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
            encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            val surface = encoder.createInputSurface()
            encoder.start()

            val muxer = MediaMuxer(out.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            var trackIndex = -1
            var muxerStarted = false

            val drainer = Thread {
                val info = MediaCodec.BufferInfo()
                while (!Thread.interrupted()) {
                    val outBuf = encoder.dequeueOutputBuffer(info, TIMEOUT_US)
                    when {
                        outBuf == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                            trackIndex = muxer.addTrack(encoder.outputFormat)
                            muxer.start()
                            muxerStarted = true
                        }
                        outBuf == MediaCodec.INFO_TRY_AGAIN -> {}
                        outBuf >= 0 -> {
                            val encoded = encoder.getOutputBuffer(outBuf)!!
                            if (info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) {
                                info.size = 0
                            }
                            if (info.size > 0 && muxerStarted) {
                                encoded.position(info.offset)
                                encoded.limit(info.offset + info.size)
                                muxer.writeSampleData(trackIndex, encoded, info)
                            }
                            encoder.releaseOutputBuffer(outBuf, false)
                            if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) break
                        }
                    }
                }
            }
            drainer.start()

            val frameDurationUs = 1_000_000L / fps
            for (frame in frames) {
                val canvas = surface.lockCanvas(null)
                canvas.drawBitmap(frame.bitmap, 0f, 0f, null)
                surface.unlockCanvasAndPost(canvas)
                Thread.sleep(frameDurationUs / 1000)
            }

            encoder.signalEndOfInputStream()
            drainer.join(5000)
            if (muxerStarted) muxer.stop()
            muxer.release()
            encoder.stop()
            encoder.release()
            out.exists() && out.length() > 0
        } catch (_: Throwable) {
            false
        }
    }
}
