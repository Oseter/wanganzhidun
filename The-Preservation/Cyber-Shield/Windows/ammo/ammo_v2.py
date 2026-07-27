"""弹药 v2 格式（预留）。

扩展字段：
  - related_groups:       关联群列表（追加论输出）
  - attack_chain_topology: 攻击链拓扑（组织化进攻标记）
  - multi_target_tags:     多目标标签
"""
from typing import Any, Dict, List


def upgrade_v1_to_v2(v1_data: dict) -> dict:
    return {
        **v1_data,
        "version": "v2",
        "related_groups": [],
        "attack_chain_topology": {},
        "multi_target_tags": [],
    }
