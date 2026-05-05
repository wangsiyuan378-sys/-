import cv2
import mediapipe as mp
import numpy as np
import time


class ConcentrationDetector:
    def __init__(self):
        # 初始化 MediaPipe 方案
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=10,  # 支持多人数识别
            refine_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.7)

    def _get_ear(self, landmarks, eye_indices):
        """计算眼睛纵横比 (Eye Aspect Ratio)，用于判断疲劳度"""
        # 简化版 EAR 计算
        pts = [np.array([landmarks[i].x, landmarks[i].y]) for i in eye_indices]
        dist1 = np.linalg.norm(pts[1] - pts[5])
        dist2 = np.linalg.norm(pts[2] - pts[4])
        dist3 = np.linalg.norm(pts[0] - pts[3])
        return (dist1 + dist2) / (2.0 * dist3)

    def analyze_frame(self, frame):
        """
        核心分析函数
        返回: (float) 综合专注度分值 0-100, (list) 原始特征数据
        """
        results_face = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        scores = []

        if results_face.multi_face_landmarks:
            for face_landmarks in results_face.multi_face_landmarks:
                # 1. 头部朝向评估 (通过鼻尖与面部边缘的相对位置简化模拟)
                nose_tip = face_landmarks.landmark[1]
                left_edge = face_landmarks.landmark[234]
                right_edge = face_landmarks.landmark[454]

                # 计算对称性：越对称说明正视前方
                offset = abs((nose_tip.x - left_edge.x) - (right_edge.x - nose_tip.x))
                orientation_score = max(0, 100 - (offset * 500))

                # 2. 眨眼/视线权重 (EAR)
                left_eye_ear = self._get_ear(face_landmarks.landmark, [33, 160, 158, 133, 153, 144])
                # EAR 正常在 0.2-0.3，闭眼趋近 0
                gaze_score = 100 if left_eye_ear > 0.2 else 30

                # 综合单人评分 (加权平均)
                individual_score = (orientation_score * 0.7) + (gaze_score * 0.3)
                scores.append(individual_score)

        # 全班平均分处理
        if not scores:
            return 0.0

        final_score = np.mean(scores)
        # 确保分值不溢出，留出 5% 的展示冗余空间
        return min(100.0, max(0.0, final_score))

    def release(self):
        self.face_mesh.close()
        self.pose.close()