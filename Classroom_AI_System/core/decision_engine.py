import collections


class DecisionEngine:
    def __init__(self, window_size=10):
        self.score_history = collections.deque(maxlen=window_size)
        self.ema_alpha = 0.3  # 平滑系数，越小越平滑
        self.current_ema = None

    def update_and_decide(self, raw_score):
        """
        输入原始分值，输出平滑分值及教学建议
        """
        # 1. 指数平滑处理，防止数据剧烈跳跃
        if self.current_ema is None:
            self.current_ema = raw_score
        else:
            self.current_ema = (self.ema_alpha * raw_score) + (1 - self.ema_alpha) * self.current_ema

        self.score_history.append(self.current_ema)

        # 2. 趋势分析 (计算简单斜率)
        trend = "stable"
        if len(self.score_history) >= 5:
            diff = self.score_history[-1] - self.score_history[-5]
            if diff > 5:
                trend = "rising"
            elif diff < -5:
                trend = "falling"

        # 3. 拟人化决策逻辑
        advice = self._generate_advice(self.current_ema, trend)

        return round(self.current_ema, 2), advice

    def _generate_advice(self, score, trend):
        """温和感知决策矩阵"""
        if score > 85:
            if trend == "rising":
                return "🌟 全班进入深度学习‘心流’状态，建议强化关键知识点输出。"
            return "✅ 学生状态极佳，建议保持当前的互动强度。"

        elif 65 <= score <= 85:
            if trend == "falling":
                return "💡 专注度有下滑趋势，建议通过提问或切换 PPT 节奏来重新吸引注意。"
            return "📘 教学环境平稳，目前是进行课堂练习的好时机。"

        elif 40 <= score < 65:
            return "⚠️ 注意：部分学生可能出现疲劳。建议插入 1-2 分钟的案例分享或互动。"

        else:
            return "💤 当前专注度较低。建议暂停讲授，通过强制互动或短暂停顿唤醒课堂。"

    def get_status_color(self, score):
        """用于 UI 渲染的颜色建议"""
        if score > 80: return "#2ECC71"  # 积极绿
        if score > 60: return "#F1C40F"  # 警告黄
        return "#E74C3C"  # 危险红