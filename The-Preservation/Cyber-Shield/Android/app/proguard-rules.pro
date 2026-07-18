# 网安智盾 Android 混淆规则
# 默认关闭 minify，规则仅作预留；上线前按需收紧

# Room
-keep class * extends androidx.room.RoomDatabase
-keep class * extends androidx.room.Entity
-keep @androidx.room.Entity class *
-keepclassmembers class * extends androidx.room.RoomDatabase { *; }

# 数据模型（JSON 序列化）
-keep class com.wanganzhidun.data.** { *; }

# 服务保留（系统绑定）
-keep class com.wanganzhidun.service.** { *; }
