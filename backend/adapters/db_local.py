import sqlite3
import json
import os
import threading
from typing import Optional, List, Dict, Any
from backend.core.ports.db import DbPort
from backend.core.models import Inspection, Finding, Challenge, ShareLink

class LocalDbAdapter(DbPort):
    def __init__(self, db_path: str = "data/carcheck.db"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS inspections (
                        inspection_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        data JSON NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_inspections_user ON inspections(user_id)")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS findings (
                        finding_id TEXT PRIMARY KEY,
                        inspection_id TEXT NOT NULL,
                        data JSON NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_findings_inspection ON findings(inspection_id)")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS challenges (
                        inspection_id TEXT PRIMARY KEY,
                        data JSON NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS share_links (
                        token TEXT PRIMARY KEY,
                        data JSON NOT NULL
                    )
                """)
                conn.commit()

    def save_inspection(self, inspection: Inspection) -> None:
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO inspections (inspection_id, user_id, data) VALUES (?, ?, ?)",
                    (inspection.inspectionId, inspection.userId, inspection.model_dump_json())
                )
                conn.commit()

    def get_inspection(self, user_id: str, inspection_id: str) -> Optional[Inspection]:
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT data FROM inspections WHERE inspection_id = ? AND user_id = ?", (inspection_id, user_id))
                row = cur.fetchone()
                if row:
                    return Inspection.model_validate_json(row["data"])
                return None

    def get_inspection_by_id(self, inspection_id: str) -> Optional[Inspection]:
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT data FROM inspections WHERE inspection_id = ?", (inspection_id,))
                row = cur.fetchone()
                if row:
                    return Inspection.model_validate_json(row["data"])
                return None

    def list_inspections(self, user_id: str) -> List[Inspection]:
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT data FROM inspections WHERE user_id = ? ORDER BY inspection_id DESC", (user_id,))
                rows = cur.fetchall()
                return [Inspection.model_validate_json(r["data"]) for r in rows]

    def delete_inspection(self, user_id: str, inspection_id: str) -> bool:
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM findings WHERE inspection_id = ?", (inspection_id,))
                conn.execute("DELETE FROM challenges WHERE inspection_id = ?", (inspection_id,))
                res = conn.execute("DELETE FROM inspections WHERE inspection_id = ? AND user_id = ?", (inspection_id, user_id))
                conn.commit()
                return res.rowcount > 0

    def save_findings(self, inspection_id: str, findings: List[Finding]) -> None:
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM findings WHERE inspection_id = ?", (inspection_id,))
                for f in findings:
                    conn.execute(
                        "INSERT OR REPLACE INTO findings (finding_id, inspection_id, data) VALUES (?, ?, ?)",
                        (f.id, inspection_id, f.model_dump_json())
                    )
                conn.commit()

    def get_findings(self, inspection_id: str) -> List[Finding]:
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT data FROM findings WHERE inspection_id = ?", (inspection_id,))
                rows = cur.fetchall()
                return [Finding.model_validate_json(r["data"]) for r in rows]

    def save_challenge(self, challenge: Challenge) -> None:
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO challenges (inspection_id, data) VALUES (?, ?)",
                    (challenge.inspectionId, challenge.model_dump_json())
                )
                conn.commit()

    def get_challenge(self, inspection_id: str) -> Optional[Challenge]:
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT data FROM challenges WHERE inspection_id = ?", (inspection_id,))
                row = cur.fetchone()
                if row:
                    return Challenge.model_validate_json(row["data"])
                return None

    def save_share_link(self, link: ShareLink) -> None:
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO share_links (token, data) VALUES (?, ?)",
                    (link.token, link.model_dump_json())
                )
                conn.commit()

    def get_share_link(self, token: str) -> Optional[ShareLink]:
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT data FROM share_links WHERE token = ?", (token,))
                row = cur.fetchone()
                if row:
                    return ShareLink.model_validate_json(row["data"])
                return None
