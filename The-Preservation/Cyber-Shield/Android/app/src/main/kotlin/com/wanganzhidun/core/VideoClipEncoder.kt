package com.wanganzhidun.core

import android.graphics.Bitmap
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import com.wanganzhidun.Constants
import java.io.File

/**
 * 把回捞到的帧编码成一段 MP4 短视频（取证补充证据）。
 *
 * 采用「缓冲区输入 + 显式 PTS」方式：把每帧 Bitmap 转 NV21 后喂入编码器，
 * 并写入单调递增的 presentationTimeUs。这样 MediaMuxer 才能正常封装出合法 MP4。
 *
 * 历史实现用 Surface 输入却未设置呈现时间戳，导致 MediaMuxer 报时间戳非递增而
 * 静默失败（只能回退到 PNG 帧）。本实现修正该问题。
 *
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

            val format = MediaFormat.createVideoFormat(
                MediaFormat.MIMETYPE_VIDEO_AVC, w, h
            ).apply {
                setInteger(MediaFormat.KEY_BIT_RATE, 2_000_000)
                setInteger(MediaFormat.KEY_FRAME_RATE, fps)
                setInteger(
                    MediaFormat.KEY_COLOR_FORMAT,
                    MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible
                )
                setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
            }

            val encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
            encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            encoder.start()

            val muxer = MediaMuxer(out.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            var trackIndex = -1
            var muxerStarted = false

            val frameDurationUs = 1_000_000L / fps
            val info = MediaCodec.BufferInfo()

            // 排空输出队列：处理 format 变更与编码帧；muxer 必须在收到首帧前 start
            fun drain(): Boolean {
                var outBuf = encoder.dequeueOutputBuffer(info, TIMEOUT_US)
                while (outBuf != MediaCodec.INFO_TRY_AGAIN_LATER) {
                    when {
                        outBuf == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                            trackIndex = muxer.addTrack(encoder.outputFormat)
                            muxer.start()
                            muxerStarted = true
                        }
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
                            if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) {
                                return true
                            }
                        }
                    }
                    outBuf = encoder.dequeueOutputBuffer(info, TIMEOUT_US)
                }
                return false
            }

            frames.forEachIndexed { idx, frame ->
                val nv21 = bitmapToNV21(frame.bitmap, w, h)
                val inBufId = encoder.dequeueInputBuffer(TIMEOUT_US)
                if (inBufId >= 0) {
                    val inBuf = encoder.getInputBuffer(inBufId)!!
                    inBuf.clear()
                    inBuf.put(nv21)
                    val pts = idx * frameDurationUs
                    val flags = if (idx == frames.lastIndex) {
                        MediaCodec.BUFFER_FLAG_END_OF_STREAM
                    } else 0
                    encoder.queueInputBuffer(inBufId, 0, nv21.size, pts, flags)
                }
                drain()
            }

            // 兜底：若最后一帧未触发 EOS 输出，再排空一次确保 muxer 收尾
            if (!muxerStarted) drain()

            if (muxerStarted) muxer.stop()
            muxer.release()
            encoder.stop()
            encoder.release()
            out.exists() && out.length() > 0
        } catch (_: Throwable) {
            false
        }
    }

    /** Bitmap(ARGB) -> NV21(YUV420SP)，便于 H.264 编码器消费。 */
    private fun bitmapToNV21(bitmap: Bitmap, w: Int, h: Int): ByteArray {
        val argb = IntArray(w * h)
        bitmap.getPixels(argb, 0, w, 0, 0, w, h)
        val yuv = ByteArray(w * h + 2 * (w * h) / 4)
        var yIndex = 0
        var uvIndex = w * h
        for (i in 0 until h) {
            for (j in 0 until w) {
                val px = argb[i * w + j]
                val r = (px shr 16) and 0xFF
                val g = (px shr 8) and 0xFF
                val b = px and 0xFF
                var y = ((66 * r + 129 * g + 25 * b + 128) shr 8) + 16
                y = if (y < 0) 0 else if (y > 255) 255 else y
                yuv[yIndex++] = y.toByte()
                if (i % 2 == 0 && j % 2 == 0) {
                    var u = ((-38 * r - 74 * g + 112 * b + 128) shr 8) + 128
                    var v = ((112 * r - 94 * g - 18 * b + 128) shr 8) + 128
                    u = if (u < 0) 0 else if (u > 255) 255 else u
                    v = if (v < 0) 0 else if (v > 255) 255 else v
                    yuv[uvIndex++] = u.toByte()
                    yuv[uvIndex++] = v.toByte()
                }
            }
        }
        return yuv
    }
}
