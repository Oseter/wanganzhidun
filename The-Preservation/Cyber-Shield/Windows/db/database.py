"""数据层：SQLite 本地存储。

三张表：
    events    — 取证事件日志（时间、来源、命中关键词、证据路径）
    evidence  — 证据记录（关联事件，标准弹药字段）
    config_log — 配置快照（便于回溯与 T1 复活）

PC 端本地存储，不对外上传（红线：不爬取非授权数据）。
"""
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional


class Database:
    """SQLite 封装。"""

    def __init__(self, db_path: str = "wanganzhidun.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source_app TEXT,
                keyword TEXT,
                evidence_dir TEXT
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                target_account TEXT,
                violation_content TEXT,
                clause TEXT,
                attachments TEXT,
                FOREIGN KEY (event_id) REFERENCES events(id)
            );
            CREATE TABLE IF NOT EXISTS config_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                snapshot TEXT
            );
            """
        )
        self._conn.commit()

    def add_event(self, source_app: str, keyword: str,
                  evidence_dir: str) -> int:
        ts = datetime.now().isoformat()
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO events (timestamp, source_app, keyword, evidence_dir) "
            "VALUES (?,?,?,?)",
            (ts, source_app, keyword, evidence_dir),
        )
        self._conn.commit()
        return cur.lastrowid

    def add_evidence(self, event_id: int, ammo: Dict):
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO evidence (event_id, target_account, violation_content, "
            "clause, attachments) VALUES (?,?,?,?,?)",
            (
                event_id,
                ammo.get("target_account", ""),
                ammo.get("violation_content", ""),
                ammo.get("clause", ""),
                str(ammo.get("evidence_attachments", {})),
            ),
        )
        self._conn.commit()

    def log_config(self, snapshot: str):
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO config_log (timestamp, snapshot) VALUES (?,?)",
            (datetime.now().isoformat(), snapshot),
        )
        self._conn.commit()

    def recent_events(self, limit: int = 50) -> List[Dict]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]

    def close(self):
        self._conn.close()
