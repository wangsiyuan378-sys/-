import sys
import cv2
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout,
                             QHBoxLayout, QWidget, QPushButton, QTextEdit,
                             QMessageBox, QSizePolicy)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap

# 导入自定义模块
from core.detector import FocusDetector
from core.decision_engine import DecisionEngine
from data.database import ClassroomDB
from ui.dashboard_view import DashboardChart
from reports.export_pdf import export_to_pdf


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("计算机设计大赛 - 教学成效辅助决策系统 v2.0")
        self.setGeometry(100, 100, 1200, 800)

        # 1. 确保必要的目录存在
        for folder in ['data', 'reports']:
            if not os.path.exists(folder):
                os.makedirs(folder)

        # 2. 初始化核心模块
        self.db = ClassroomDB()
        self.detector = FocusDetector()
        self.advisor = DecisionEngine()

        # 3. 构建 UI 界面
        self.init_ui()

        # 4. 启动视频采集
        self.cap = cv2.VideoCapture(0)
        # 强制设置分辨率，避免系统AI自动裁剪导致画面放大
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(30)

    def init_ui(self):
        """构建界面布局"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # --- 左侧：视频流显示 ---
        self.video_label = QLabel("正在初始化摄像头...")
        self.video_label.setStyleSheet("background-color: black; border: 2px solid #333; border-radius: 5px;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 核心修复：防止图片撑大Label导致布局无限膨胀
        self.video_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.video_label.setMinimumSize(640, 480)

        layout.addWidget(self.video_label, 2)

        # --- 右侧：控制与数据面板 ---
        side_panel = QVBoxLayout()

        # --- A. 实时曲线图 (针对坐标轴进行了深度优化) ---
        import pyqtgraph as pg
        self.plot_widget = pg.PlotWidget(title="课堂专注度实时趋势")

        # 1. 锁定 Y 轴：专注度固定在 0-100，顶部留 5 像素缓冲
        self.plot_widget.setYRange(0, 105, padding=0)
        # 2. 锁定 X 轴：显示最近 100 个数据点
        self.plot_widget.setXRange(0, 100, padding=0)
        # 3. 禁用鼠标缩放和拖拽，防止坐标轴乱跑
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.hideButtons()
        # 4. 显示背景网格
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        self.chart = DashboardChart(self.plot_widget)
        side_panel.addWidget(self.plot_widget)

        # --- B. AI 决策建议文本框 ---
        self.advice_box = QTextEdit()
        self.advice_box.setReadOnly(True)
        self.advice_box.setPlaceholderText("系统正在分析课堂状态...")
        self.advice_box.setStyleSheet("font-size: 15px; background-color: #fcfcfc; border: 1px solid #ddd;")
        side_panel.addWidget(self.advice_box)

        # --- C. 操作按钮组 ---
        btn_layout = QHBoxLayout()

        self.acc_btn = QPushButton("查看识别准确率")
        self.acc_btn.clicked.connect(self.show_accuracy_report)
        self.acc_btn.setStyleSheet(
            "height: 45px; background-color: #3498db; color: white; font-weight: bold; border-radius: 5px;")

        self.export_btn = QPushButton("生成课堂分析报告")
        self.export_btn.clicked.connect(self.handle_export)
        self.export_btn.setStyleSheet(
            "height: 45px; background-color: #2ecc71; color: white; font-weight: bold; border-radius: 5px;")

        btn_layout.addWidget(self.acc_btn)
        btn_layout.addWidget(self.export_btn)
        side_panel.addLayout(btn_layout)

        # --- D. 重置按钮 ---
        self.clear_btn = QPushButton("清空当前数据")
        self.clear_btn.clicked.connect(self.reset_session)
        self.clear_btn.setStyleSheet("height: 30px; color: #666;")
        side_panel.addWidget(self.clear_btn)

        layout.addLayout(side_panel, 1)

    def process_frame(self):
        """主处理循环：识别 -> 存储 -> 更新 UI"""
        ret, frame = self.cap.read()
        if ret:
            try:
                # 1. 算法检测
                score, status, action = self.detector.get_focus_score(frame)

                # 2. 存入数据库
                # 如果是录制好的测试视频，可以在这里手动设置 true_label=1 或 0
                self.db.insert_record(score, status, action, true_label=None)

                # 3. 更新视频画面 (增加平滑处理)
                rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_img.shape
                q_img = QImage(rgb_img.data, w, h, ch * w, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img).scaled(
                    self.video_label.width(),
                    self.video_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.video_label.setPixmap(pixmap)

                # 4. 更新波形图表
                recent_data = self.db.get_recent_data()
                if recent_data:
                    self.chart.update(recent_data)

                # 5. 每 50 帧更新一次 AI 建议，防止文字刷新过快
                if len(recent_data) % 50 == 0:
                    advice = self.advisor.generate_advice(recent_data)
                    self.advice_box.setText(advice)

            except Exception as e:
                print(f"数据处理异常: {e}")
        else:
            self.video_label.setText("摄像头连接断开")

    def show_accuracy_report(self):
        """弹出性能评估报告"""
        pairs = self.db.get_evaluation_pairs()
        if not pairs:
            QMessageBox.information(self, "评估提示",
                                    "当前为实时模式，暂无标注对比数据。\n\n提示：在测试视频时将 insert_record 中的 true_label 设为 1 即可生成此报告。")
            return

        self.detector.reset_metrics()
        for pred, true in pairs:
            if pred == 1 and true == 1:
                self.detector.metrics["TP"] += 1
            elif pred == 1 and true == 0:
                self.detector.metrics["FP"] += 1
            elif pred == 0 and true == 0:
                self.detector.metrics["TN"] += 1
            elif pred == 0 and true == 1:
                self.detector.metrics["FN"] += 1
            self.detector.metrics["total"] += 1

        res = self.detector.get_accuracy_report()
        msg = f"--- 算法性能分析 ---\n\n样本总数: {res['Samples']}\n识别准确率: {res['Accuracy']}\n精准识别率: {res['Precision']}"
        QMessageBox.information(self, "性能分析报告", msg)

    def handle_export(self):
        """导出 PDF 报告"""
        success, message = export_to_pdf()
        if success:
            QMessageBox.information(self, "导出成功", f"报告路径: {message}")
        else:
            QMessageBox.warning(self, "导出失败", message)

    def reset_session(self):
        """重置数据"""
        reply = QMessageBox.question(self, '数据重置', '确定要删除所有监测数据并清空图表吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_data()
            self.detector.reset_metrics()
            self.advice_box.clear()
            self.advice_box.setPlaceholderText("数据已重置，等待新输入...")

    def closeEvent(self, event):
        """安全退出"""
        if self.cap.isOpened():
            self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 使用 Fusion 样式确保跨平台 UI 一致性
    app.setStyle("Fusion")
    window = MainApp()
    window.show()
    sys.exit(app.exec())