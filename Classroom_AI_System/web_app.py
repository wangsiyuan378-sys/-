import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import cv2
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime

# --- 1. 环境兼容性补丁 (解决日志中的 OperationalError) ---
for folder in ["data", "reports/generated"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 导入核心模块
from core.detector import ConcentrationDetector
from core.decision_engine import DecisionEngine
from data.database import ClassroomDB
from reports.generator import ReportGenerator

# 使用缓存加载模型，防止 Web 端重复初始化导致卡顿
@st.cache_resource
def load_system_engines():
    return ConcentrationDetector(), DecisionEngine(), ClassroomDB(), ReportGenerator()

detector, engine, db, report_gen = load_system_engines()

# --- 2. 增强型视频处理类 (支持前端提取数据) ---
class VideoProcessor:
    def __init__(self):
        self.out_score = 0.0
        self.out_advice = "等待分析..."

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")

        # 执行视觉分析 (确保 detector.py 使用 mp.solutions 标准导入)
        raw_score = detector.analyze_frame(img)
        smooth_score, advice = engine.update_and_decide(raw_score)

        # 更新实例变量，供主 UI 线程实时读取
        self.out_score = smooth_score
        self.out_advice = advice

        # 每 5 秒自动记录一次数据到 SQLite
        if int(time.time()) % 5 == 0:
            db.insert_record(smooth_score, advice)

        # 在视频画面叠加实时分值
        color = (46, 204, 113) if smooth_score > 70 else (231, 76, 60)
        cv2.putText(img, f"Focus: {smooth_score}", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# --- 3. UI 界面与实时可视化逻辑 ---
def main():
    st.title("📖 教学效能辅助决策系统")
    
    # 侧边栏：报告管理
    with st.sidebar:
        st.header("📋 报告中心")
        if st.button("🚀 生成当前课堂效能报告"):
            history = db.get_latest_history(limit=50)
            if history:
                # 获取平均分
                avg_s = np.mean([x[1] for x in history])
                pdf_path = report_gen.generate_pdf("CLASS_2026", round(avg_s, 2), "课堂整体状态平稳", history)
                with open(pdf_path, "rb") as f:
                    st.download_button("💾 下载分析报告 (PDF)", f, file_name="Teaching_Report.pdf")
            else:
                st.warning("暂无数据，请先开启摄像头。")

    # 主界面分栏
    col_vid, col_stat = st.columns([2, 1])

    with col_vid:
        ctx = webrtc_streamer(
            key="classroom-v2",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTCConfiguration(
                {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            ),
            video_processor_factory=VideoProcessor,
            async_processing=True,
        )

    with col_stat:
        st.subheader("实时分析看板")
        # 创建动态占位符，用于在原地更新数据
        score_metric = st.empty()
        advice_box = st.empty()
        chart_viz = st.empty()

        # 实时同步循环：只要摄像头开着，就不断从 VideoProcessor 抓取结果
        while ctx.state.playing:
            if ctx.video_processor:
                # 获取后台线程的最新数据
                s = ctx.video_processor.out_score
                a = ctx.video_processor.out_advice
                
                # 更新前端组件
                score_metric.metric("实时专注评分", f"{s}", delta=f"{s-85:.1f}")
                advice_box.info(f"🤖 **辅助决策建议**：\n\n{a}")
                
                # 动态图表显示
                history = db.get_latest_history(limit=20)
                if history:
                    df = pd.DataFrame(history, columns=["Time", "Score"])
                    chart_viz.line_chart(df.set_index("Time"))
            
            time.sleep(0.5) # 每 0.5 秒刷新一次前端界面

if __name__ == "__main__":
    main()
