package com.wanganzhidun.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.wanganzhidun.data.EvidenceEntity
import com.wanganzhidun.databinding.ItemEventBinding

class EventAdapter : RecyclerView.Adapter<EventAdapter.VH>() {

    private val items = mutableListOf<EvidenceEntity>()

    fun submit(list: List<EvidenceEntity>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    class VH(val binding: ItemEventBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemEventBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val e = items[position]
        holder.binding.tvTarget.text = e.target
        holder.binding.tvTime.text = e.time
        holder.binding.tvContent.text = e.content
        holder.binding.tvClause.text = e.clause
    }

    override fun getItemCount(): Int = items.size
}
