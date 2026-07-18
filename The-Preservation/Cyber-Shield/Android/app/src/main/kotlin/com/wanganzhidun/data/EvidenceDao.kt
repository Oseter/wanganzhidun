package com.wanganzhidun.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface EvidenceDao {

    @Insert
    suspend fun insert(entity: EvidenceEntity): Long

    @Query("SELECT * FROM evidence ORDER BY createdAt DESC")
    fun observeAll(): Flow<List<EvidenceEntity>>

    @Query("SELECT * FROM evidence ORDER BY createdAt DESC")
    suspend fun getAll(): List<EvidenceEntity>

    @Query("SELECT * FROM evidence WHERE id = :id")
    suspend fun getById(id: Long): EvidenceEntity?

    @Query("DELETE FROM evidence WHERE id = :id")
    suspend fun delete(id: Long)
}
