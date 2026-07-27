"""接口封锁原子（预留）。

频率检测在 monitor/freq_detect.py（AntiTag）。
实际封锁需对接各平台隐私设置 API 或 UI 自动化。
当前模块提供封锁建议清单与状态查询。
"""

LOCKDOWN_CHECKS = [
    ("QID 搜索", "关闭 QID/Q 号搜索添加"),
    ("临时会话", "关闭临时会话/私聊权限"),
    ("陌生人拉群", "关闭陌生人拉群权限"),
    ("加好友验证", "开启加好友验证问题"),
    ("添加方式", "限制添加方式为仅扫码"),
    ("群邀请验证", "开启群邀请需要我确认"),
]


def get_lockdown_checks() -> list:
    return list(LOCKDOWN_CHECKS)
