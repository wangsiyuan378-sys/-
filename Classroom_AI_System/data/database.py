import sqlite3
import threading
from datetime import datetime
import os
class ClassroomDB:
    _instance_lock = threading.Lock()

    def __init__(self, db_path="data/classroom_v2.db"):
        # 获取文件夹路径 (即 "data")
        db_dir = os.path.dirname(db_path)
        
        # 如果文件夹不存在，则自动创建它
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            print(f"检测到目录不存在，已创建: {db_dir}")
            
        self.db_path = db_path
        self._create_table()

    def _get_connection(self):
        # 核心：check_same_thread=False 允许在多线程中访问
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _create_table(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS analytics_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    focus_score REAL,
                    decision_advice TEXT,
                    student_count INTEGER
                )
            ''')
            conn.commit()

    def insert_record(self, score, advice, count=1):
        """记录一次实时分析结果"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO analytics_logs (focus_score, decision_advice, student_count) VALUES (?, ?, ?)",
                    (score, advice, count)
                )
                conn.commit()
        except Exception as e:
            print(f"Database Error: {e}")

    def get_latest_history(self, limit=50):
        """获取最近的历史记录用于绘图"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT timestamp, focus_score FROM analytics_logs ORDER BY id DESC LIMIT ?", (limit,)
            )
            return cursor.fetchall()[::-1] # 翻转以按时间正序排列
