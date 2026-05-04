import sqlite3
from datetime import datetime


class ClassroomDB:
    def __init__(self, db_path="data/classroom.db"):
        # 连接数据库，check_same_thread=False 允许在 PyQt 多线程中使用
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """
        创建数据表
        新增 true_label 字段：1 表示真实专注，0 表示真实走神，None 表示未标注（实时模式）
        """
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS focus_log
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              timestamp TEXT, 
                              score REAL, 
                              status TEXT,
                              action_type TEXT,
                              true_label INTEGER)''')
        self.conn.commit()

    def insert_record(self, score, status, action="Normal", true_label=None):
        """
        插入检测记录
        :param true_label: 如果是测试模式，传入 0 或 1；如果是实时模式，保持 None
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''INSERT INTO focus_log 
                               (timestamp, score, status, action_type, true_label) 
                               VALUES (?, ?, ?, ?, ?)''',
                            (ts, score, status, action, true_label))
        self.conn.commit()

    def get_recent_data(self, limit=100):
        """获取最近的得分列表，用于 UI 曲线绘制"""
        self.cursor.execute("SELECT score FROM focus_log ORDER BY id DESC LIMIT ?", (limit,))
        return [x[0] for x in self.cursor.fetchall()][::-1]

    def get_evaluation_pairs(self, limit=500):
        """
        获取预测状态与真实标签的对照组，用于计算准确率
        预测状态逻辑：status为'专注'记为1，其余记为0
        """
        self.cursor.execute('''SELECT status, true_label FROM focus_log 
                               WHERE true_label IS NOT NULL 
                               ORDER BY id DESC LIMIT ?''', (limit,))
        raw_data = self.cursor.fetchall()

        # 转换格式：[(预测1, 真实1), (预测0, 真实0), ...]
        pairs = []
        for status, true_val in raw_data:
            pred_val = 1 if status == "专注" else 0
            pairs.append((pred_val, true_val))
        return pairs

    def clear_data(self):
        """清空数据（用于开始新的测试视频时）"""
        self.cursor.execute("DELETE FROM focus_log")
        self.conn.commit()