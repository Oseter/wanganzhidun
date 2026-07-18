package com.wanganzhidun

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.EditText
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.wanganzhidun.core.CaptureOrchestrator
import com.wanganzhidun.core.KeywordEngine
import com.wanganzhidun.data.AppDatabase
import com.wanganzhidun.databinding.ActivityMainBinding
import com.wanganzhidun.service.CaptureService
import com.wanganzhidun.ui.EventAdapter
import kotlinx.coroutines.launch
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val adapter = EventAdapter()
    private var capturing = false

    private val projectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val intent = Intent(this, CaptureService::class.java).apply {
                putExtra("resultCode", result.resultCode)
                putExtra("data", result.data)
            }
            ContextCompat.startForegroundService(this, intent)
            setCapturing(true)
        } else {
            Toast.makeText(this, R.string.hint_enable_capture, Toast.LENGTH_SHORT).show()
        }
    }

    private val notifPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.eventList.layoutManager = LinearLayoutManager(this)
        binding.eventList.adapter = adapter

        binding.btnCapture.setOnClickListener { toggleCapture() }
        binding.btnEvidence.setOnClickListener { openEvidence() }
        binding.btnTest.setOnClickListener { CaptureOrchestrator.testForensics() }
        binding.btnSettings.setOnClickListener { editKeywords() }

        binding.chipListener.setOnClickListener {
            if (!isNotificationListenerEnabled())
                startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
        binding.chipAccessibility.setOnClickListener {
            if (!isAccessibilityEnabled())
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notifPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        observeEvents()
        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    private fun observeEvents() {
        lifecycleScope.launch {
            AppDatabase.getInstance(this@MainActivity).evidenceDao().observeAll().collect {
                adapter.submit(it)
            }
        }
    }

    private fun refreshStatus() {
        updateChip(binding.chipListener, isNotificationListenerEnabled(), R.string.status_listener)
        updateChip(binding.chipAccessibility, isAccessibilityEnabled(), R.string.status_accessibility)
        updateChip(binding.chipCapture, capturing, R.string.status_capture)
    }

    private fun updateChip(chip: com.google.android.material.chip.Chip, on: Boolean, labelRes: Int) {
        chip.text = "${getString(labelRes)}：${getString(if (on) R.string.status_on else R.string.status_off)}"
        chip.setChipBackgroundColorResource(
            if (on) R.color.shield_primary else R.color.shield_surface_2
        )
    }

    private fun toggleCapture() {
        if (capturing) {
            stopService(Intent(this, CaptureService::class.java))
            setCapturing(false)
        } else {
            val mpm = getSystemService(MediaProjectionManager::class.java)
            projectionLauncher.launch(mpm.createScreenCaptureIntent())
        }
    }

    private fun setCapturing(v: Boolean) {
        capturing = v
        binding.btnCapture.setText(if (v) R.string.btn_stop_capture else R.string.btn_start_capture)
        updateChip(binding.chipCapture, v, R.string.status_capture)
    }

    private fun openEvidence() {
        // A5 修复：FileProvider 不能直接分享「目录」，多数文件管理器无法打开目录，
        // 会走 catch 回退 toast。改为收集最新事件目录内的文件，用 ACTION_SEND_MULTIPLE
        // 一次性分享多个带 Uri 的文件。
        val root = File(filesDir, Constants.EVIDENCE_DIR)
        if (!root.exists()) root.mkdirs()
        val latestDir = root.listFiles()?.filter { it.isDirectory }
            ?.maxByOrNull { it.lastModified() } ?: root

        val files = if (latestDir.isDirectory) {
            latestDir.listFiles()?.toList().orEmpty()
        } else {
            listOf(latestDir)
        }
        if (files.isEmpty()) {
            Toast.makeText(this, R.string.no_evidence_yet, Toast.LENGTH_SHORT).show()
            return
        }

        val uris = ArrayList<Uri>()
        for (f in files) {
            try {
                uris.add(FileProvider.getUriForFile(this, "$packageName.fileprovider", f))
            } catch (_: Exception) {
                // 跳过无法生成 Uri 的条目
            }
        }
        if (uris.isEmpty()) {
            Toast.makeText(this, latestDir.absolutePath, Toast.LENGTH_LONG).show()
            return
        }

        val intent = Intent(Intent.ACTION_SEND_MULTIPLE).apply {
            type = "*/*"
            putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            startActivity(Intent.createChooser(intent, getString(R.string.btn_open_evidence)))
        } catch (_: Exception) {
            Toast.makeText(this, latestDir.absolutePath, Toast.LENGTH_LONG).show()
        }
    }

    private fun editKeywords() {
        val file = File(filesDir, Constants.KEYWORDS_FILE)
        val current = KeywordEngine.keywords.joinToString("\n")
        val edit = EditText(this).apply {
            setText(current)
            minLines = 4
            gravity = android.view.Gravity.TOP
        }
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.btn_open_settings)
            .setMessage(R.string.ammo_format_hint)
            .setView(edit)
            .setPositiveButton(android.R.string.ok) { _, _ ->
                val list = edit.text.lines().map { it.trim() }.filter { it.isNotBlank() }
                KeywordEngine.save(file, list)
                Toast.makeText(this, "已保存 ${list.size} 个关键词", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        return enabled?.contains(packageName) == true
    }

    private fun isAccessibilityEnabled(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver, "enabled_accessibility_services")
        return enabled?.contains(packageName) == true
    }
}
