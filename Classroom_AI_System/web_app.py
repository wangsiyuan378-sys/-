import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration, WebRtcMode
import av
import cv2
import pandas as pd
import numpy as np
from datetime import datetime

# 导入你之前写的核心模块
from core.detector import ConcentrationDetector
from core.decision_engine import DecisionEngine
from data.database import ClassroomDB

# 页面配置
st.set_page_config(page_title="教学效能 Web 终端 v2.0", layout="wide")

# 初始化组件
db = ClassroomDB()
detector = ConcentrationDetector()
engine = DecisionEngine()

# 注入极简主义 CSS
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    .status-card { 
        padding: 20px; 
        border-radius: 15px; 
        background: white; 
        border: 1px solid #E9ECEF;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    </style>
    """, unsafe_allow_html=True)


# --- WebRTC 核心处理类 ---
class VideoProcessor:
    def __init__(self):
        self.detector = detector
        self.engine = engine
        self.db = db

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")

        # 1. 执行视觉分析
        raw_score = self.detector.analyze_frame(img)
        smooth_score, advice = self.engine.update_and_decide(raw_score)

        # 2. 异步存入数据库 (竞赛演示建议记录关键帧数据)
        if int(datetime.now().second) % 5 == 0:  # 每5秒记录一次，避免数据库写拥堵
            self.db.insert_record(smooth_score, advice)

        # 3. 在画面上绘制温和的 UI 遮罩（可选）
        color = (46, 204, 113) if smooth_score > 70 else (231, 76, 60)
        cv2.putText(img, f"Focus: {smooth_score}", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# --- UI 布局 ---
def main():
    st.title("📖 教学效能辅助决策系统 - WebRTC 实时终端")
    st.info("本终端已激活云端摄像头权限。点击 'Start' 即可开启实时教学感知。")

    col_vid, col_stat = st.columns([2, 1])

    with col_vid:
        # WebRTC 控件
        webrtc_streamer(
            key="classroom-streamer",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTCConfiguration(
                {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            ),
            video_processor_factory=VideoProcessor,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )

    with col_stat:
        st.subheader("📊 实时统计")

        # 模拟动态仪表盘
        # 注意：由于 WebRTC 在独立线程，主界面通常显示数据库中的聚合结果
        st.write("📈 **近期趋势 (最近 1 分钟)**")
        history = db.get_latest_history(limit=20)
        if history:
            df = pd.DataFrame(history, columns=["Time", "Score"])
            st.line_chart(df.set_index("Time"))

        st.markdown("---")
        st.markdown("""
            <div class="status-card">
                <h4>🤖 教学策略引擎</h4>
                <p>系统已连接。实时分析结果将同步至云端数据库并生成分析报告。</p>
            </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()