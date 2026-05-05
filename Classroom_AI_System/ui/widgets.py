from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import pyqtgraph as pg


class RealTimeChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        # 配置 pyqtgraph 绘制外观
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('transparent')  # 保持温和的透明感
        self.plot_widget.setYRange(0, 105)  # 锁定坐标轴
        self.plot_widget.showGrid(x=False, y=True, alpha=0.3)

        # 定义曲线样式：抗锯齿 + 柔和的蓝色
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#4A90E2', width=3),
            antialias=True
        )

        self.data_buffer = []
        self.layout.addWidget(self.plot_widget)

    def update_plot(self, new_score):
        """动态更新图表"""
        self.data_buffer.append(new_score)
        if len(self.data_buffer) > 100:  # 只保留最近100个点
            self.data_buffer.pop(0)
        self.curve.setData(self.data_buffer)


class AdviceCard(QWidget):
    """用于展示温和建议的卡片组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border-radius: 15px;
                border: 1px solid #E9ECEF;
            }
        """)
        self.label = QLabel("正在初始化决策引擎...")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)

    def set_text(self, text):
        self.label.setText(text)