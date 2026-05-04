import numpy as np


class DecisionEngine:
    @staticmethod
    def generate_advice(scores):
        if not scores: return "等待数据输入..."
        avg_score = np.mean(scores)

        if avg_score < 40:
            return "【严重预警】当前课堂互动率极低。建议：立即停止讲授，通过提问或小组讨论唤醒学生注意力。"
        elif avg_score < 70:
            return "【教学建议】注意力出现小幅波动。建议：增加教学课件的视觉刺激，或调整讲课语调。"
        else:
            return "【成效良好】学生专注度较高。建议：进入深度知识点讲解，当前是教学黄金时间。"