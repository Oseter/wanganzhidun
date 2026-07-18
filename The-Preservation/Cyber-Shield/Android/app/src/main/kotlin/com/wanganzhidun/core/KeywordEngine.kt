package com.wanganzhidun.core

import com.wanganzhidun.Constants
import kotlinx.serialization.json.Json
import java.io.File

/**
 * 关键词论引擎：从 keywords.json 加载用户词表，对文本做包含匹配。
 * 仅对用户配置的关键词触发，默认词为占位示例（红线：不对非恶俗目标使用）。
 */
object KeywordEngine {

    private val _keywords = mutableSetOf<String>()
    val keywords: Set<String> get() = _keywords.toSet()

    fun load(file: File) {
        if (!file.exists()) seed(file)
        try {
            val list = Json.decodeFromString<List<String>>(file.readText())
            _keywords.clear()
            _keywords.addAll(list.map { it.trim() }.filter { it.isNotBlank() })
        } catch (_: Exception) {
            if (_keywords.isEmpty()) _keywords.addAll(Constants.DEFAULT_KEYWORDS)
        }
    }

    /** 重新载入（配置热更新） */
    fun reload(file: File) = load(file)

    fun save(file: File, list: List<String>) {
        file.writeText(Json.encodeToString(list))
        load(file)
    }

    /** 返回命中的关键词 */
    fun match(text: String): List<String> =
        _keywords.filter { text.contains(it, ignoreCase = true) }

    fun hasMatch(text: String): Boolean = match(text).isNotEmpty()

    private fun seed(file: File) {
        file.writeText(Json.encodeToString(Constants.DEFAULT_KEYWORDS))
        _keywords.addAll(Constants.DEFAULT_KEYWORDS)
    }
}
