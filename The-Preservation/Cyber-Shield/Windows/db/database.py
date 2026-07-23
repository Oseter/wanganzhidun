"""SQLite 本地存储：事件日志、证据记录、配置快照。"""
import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Optional


class Database:
    def __init__(self, db_path: str = "wanganzhidun.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source_app TEXT,
                    keyword TEXT,
                    event_type TEXT DEFAULT 'forensics',
                    evidence_dir TEXT,
                    status TEXT DEFAULT 'pending'
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    ammo_json TEXT,
                    attachments TEXT,
                    clause TEXT,
                    created_at TEXT,
                    FOREIGN KEY (event_id) REFERENCES events(id)
                );
                CREATE TABLE IF NOT EXISTS config_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    snapshot TEXT
                );
                CREATE TABLE IF NOT EXISTS counterstrike_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    channel TEXT,
                    success INTEGER,
                    note TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (event_id) REFERENCES events(id)
                );
                CREATE TABLE IF NOT EXISTS anti_tag_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT,
                    count INTEGER,
                    threshold INTEGER,
                    action_taken TEXT
                );
            """)
            self._conn.commit()

    def add_event(self, source_app: str, keyword: str,
                  evidence_dir: str, event_type: str = "forensics") -> int:
        ts = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO events (timestamp, source_app, keyword, event_type, evidence_dir) "
                "VALUES (?,?,?,?,?)",
                (ts, source_app, keyword, event_type, evidence_dir),
            )
            self._conn.commit()
            return cur.lastrowid

    def add_evidence(self, event_id: int, ammo_json: str,
                     attachments: str, clause: str):
        ts = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO evidence (event_id, ammo_json, attachments, clause, created_at) "
                "VALUES (?,?,?,?,?)",
                (event_id, ammo_json, attachments, clause, ts),
            )
            self._conn.commit()

    def log_counterstrike(self, event_id: int, channel: str,
                          success: bool, note: str = ""):
        ts = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO counterstrike_log (event_id, channel, success, note, timestamp) "
                "VALUES (?,?,?,?,?)",
                (event_id, channel, 1 if success else 0, note, ts),
            )
            self._conn.commit()

    def log_anti_tag(self, event_type: str, count: int,
                     threshold: int, action_taken: str = ""):
        ts = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO anti_tag_log (timestamp, event_type, count, threshold, action_taken) "
                "VALUES (?,?,?,?,?)",
                (ts, event_type, count, threshold, action_taken),
            )
            self._conn.commit()

    def log_config(self, snapshot: str):
        ts = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO config_log (timestamp, snapshot) VALUES (?,?)",
                (ts, snapshot),
            )
            self._conn.commit()

    def recent_events(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    def update_event_status(self, event_id: int, status: str):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("UPDATE events SET status = ? WHERE id = ?",
                        (status, event_id))
            self._conn.commit()

    def close(self):
        self._conn.close()
