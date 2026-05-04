import streamlit as st
import cv2
import pandas as pd
import altair as alt
import av
import queue
import time
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode

# 1. 极简 UI
st.set_page_config(page_title="教学观察看板", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden;} .stApp{background-color:#FAFAFA;}</style>",
            unsafe_allow_html=True)

# 导入你的算法
from core.detector import FocusDetector
from core.decision_engine import DecisionEngine


@st.cache_resource
def load_core():
    return FocusDetector(), DecisionEngine()


detector, advisor = load_core()


# 2. 视频处理器：不再依赖 st.session_state
class VideoProcessor(VideoProcessorBase):
    def __init__(self, q):
        self.q = q
        self.frame_count = 0

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        self.frame_count += 1

        # 降频处理，每 10 帧算一次，救救老电脑
        if self.frame_count % 10 == 0:
            try:
                small_img = cv2.resize(img, (320, 240))
                score, status, _ = detector.get_focus_score(small_img)
                # 往传入的队列里塞数据
                self.q.put({"score": score, "status": status})
            except:
                pass
        return av.VideoFrame.from_ndarray(img, format="bgr24")


# --- 关键：确保队列在每一轮运行中都存在 ---

# 如果 session_state 里没队列，创建一个
if "data_queue" not in st.session_state:
    st.session_state.data_queue = queue.Queue()
if "history" not in st.session_state:
    st.session_state.history = []

# 【核心修复点】：在这里手动提取一次实例
# 这样 result_q 就是一个具体的对象指针，不再是 st.session_state 的代理
result_q = st.session_state.data_queue

st.title("课堂成效观察站")

left, right = st.columns([1.6, 1])

with left:
    ctx = webrtc_streamer(
        key="focus-v4",
        mode=WebRtcMode.SENDRECV,
        # 这里直接用局部变量 result_q，不要写 st.session_state.data_queue
        video_processor_factory=lambda: VideoProcessor(result_q),
        media_stream_constraints={"video": {"width": 640}, "audio": False},
        async_processing=True,
    )

with right:
    status_card = st.empty()
    chart_area = st.empty()
    advice_area = st.empty()

# --- 主循环：轮询本地 result_q ---
if ctx.state.playing:
    while True:
        current_data = None
        # 使用 local 变量 result_q，更稳定
        while not result_q.empty():
            current_data = result_q.get()
            st.session_state.history.append(current_data["score"])

        if current_data:
            # 更新状态和图表
            color = "#2ECC71" if current_data["status"] == "专注" else "#E74C3C"
            status_card.markdown(f"""
                <div style="background:white; padding:20px; border-radius:10px; border:1px solid #EEE;">
                    <span style='color:#666;'>状态：</span><b style='color:{color}; font-size:24px;'>{current_data["status"]}</b>
                    <span style='float:right; font-size:20px;'>{current_data["score"]} pts</span>
                </div>
            """, unsafe_allow_html=True)

            if len(st.session_state.history) > 40:
                st.session_state.history = st.session_state.history[-40:]

            df = pd.DataFrame({"y": st.session_state.history, "x": range(len(st.session_state.history))})
            chart = alt.Chart(df).mark_area(color='#3498DB', opacity=0.3).encode(
                x=alt.X('x', axis=None),
                y=alt.Y('y', scale=alt.Scale(domain=[0, 105]), axis=None)
            ).properties(height=180)
            chart_area.altair_chart(chart, use_container_width=True)

        time.sleep(0.5)