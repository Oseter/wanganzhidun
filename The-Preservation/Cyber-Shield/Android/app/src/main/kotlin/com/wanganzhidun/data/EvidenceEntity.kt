package com.wanganzhidun.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * 取证记录 / 标准弹药入库实体。
 * 标准弹药格式：目标账号|时间|违规内容|对应条款|证据附件
 */
@Entity(tableName = "evidence")
data class EvidenceEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val target: String,        // 目标账号
    val time: String,          // 取证时间（ISO）
    val content: String,       // 违规内容摘要
    val clause: String,        // 对应条款（命途论 / 关键词论）
    val attachments: String,   // 证据附件路径，多个以 ; 分隔
    val createdAt: Long = System.currentTimeMillis()
)
