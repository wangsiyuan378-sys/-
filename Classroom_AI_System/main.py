import sys
import cv2
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

# 导入自定义模块
from core.detector import ConcentrationDetector
from core.decision_engine import DecisionEngine
from data.database import ClassroomDB
from ui.widgets import RealTimeChart, AdviceCard


class VideoThread(QThread):
    # 定义信号，将检测结果传回 UI 线程
    change_pixmap_signal = pyqtSignal(QImage)
    data_signal = pyqtSignal(float, str)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.detector = ConcentrationDetector()
        self.engine = DecisionEngine()
        self.db = ClassroomDB()

    def run(self):
        cap = cv2.VideoCapture(0)  # 开启默认摄像头
        while self._run_flag:
            ret, frame = cap.read()
            if ret:
                # 1. 核心分析
                raw_score = self.detector.analyze_frame(frame)
                smooth_score, advice = self.engine.update_and_decide(raw_score)

                # 2. 存入数据库
                self.db.insert_record(smooth_score, advice)

                # 3. 发送数据信号
                self.data_signal.emit(smooth_score, advice)

                # 4. 视频流画面处理
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.change_pixmap_signal.emit(qt_image.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio))

        cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Classroom AI System v2.0 - 实时监控终端")
        self.setMinimumSize(1000, 700)

        # 初始化 UI 布局
        self.init_ui()

        # 启动计算线程
        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.data_signal.connect(self.update_metrics)
        self.thread.start()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 左侧：视频流展示
        self.video_label = QLabel("正在初始化摄像头...")
        self.video_label.setStyleSheet("background-color: black; border-radius: 10px;")
        layout.addWidget(self.video_label, stretch=2)

        # 右侧：分析仪表盘
        right_panel = QVBoxLayout()
        self.chart = RealTimeChart()
        self.advice_card = AdviceCard()

        right_panel.addWidget(QLabel("📈 专注度实时趋势 (0-105)"))
        right_panel.addWidget(self.chart)
        right_panel.addWidget(QLabel("🤖 教学决策建议"))
        right_panel.addWidget(self.advice_card)

        layout.addLayout(right_panel, stretch=1)

    def update_image(self, qt_img):
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def update_metrics(self, score, advice):
        self.chart.update_plot(score)
        self.advice_card.set_text(advice)

    def closeEvent(self, event):
        self.thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置应用字体，提升视觉美感
    app.setStyleSheet("QLabel { font-family: 'Microsoft YaHei'; font-size: 14px; }")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())