import cv2
import numpy as np
import mediapipe as mp

# 建议把初始化放在类外面或使用延迟加载
class FocusDetector:
    def __init__(self):
        # 显式尝试获取 solutions
        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_drawing = mp.solutions.drawing_utils
        except AttributeError:
            # 如果还是找不到，尝试动态导入
            import mediapipe.solutions.face_mesh as fm
            self.mp_face_mesh = fm
        
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            refine_landmarks=True,
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # 2. 关键点索引
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]

        # 3. 性能评估统计器 (混淆矩阵计数)
        self.reset_metrics()

    def reset_metrics(self):
        """重置评估指标"""
        self.metrics = {
            "TP": 0, "FP": 0, "TN": 0, "FN": 0, "total": 0
        }

    def _calculate_ear(self, landmarks, eye_indices):
        """计算眼睛纵横比 (EAR)"""
        pts = [np.array([landmarks[i].x, landmarks[i].y]) for i in eye_indices]
        v1 = np.linalg.norm(pts[1] - pts[5])
        v2 = np.linalg.norm(pts[2] - pts[4])
        h = np.linalg.norm(pts[0] - pts[3])
        return (v1 + v2) / (2.0 * h)

    def get_focus_score(self, frame, true_label=None):
        """
        核心识别函数
        frame: 图像帧
        true_label: 选填。当前帧的真实标签 (1表示专注, 0表示走神/分心/离席)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        # 默认预测值
        score = 95
        status = "专注"
        action = "Listening"
        pred_label = 1  # 预测标签：专注

        if not results.multi_face_landmarks:
            score, status, action, pred_label = 0, "离席", "No Face", 0
        else:
            landmarks = results.multi_face_landmarks[0].landmark
            avg_ear = (self._calculate_ear(landmarks, self.LEFT_EYE) +
                       self._calculate_ear(landmarks, self.RIGHT_EYE)) / 2.0

            nose = landmarks[1].x
            face_left = landmarks[234].x
            face_right = landmarks[454].x
            symmetry = abs((nose - face_left) / (face_right - face_left) - 0.5)

            if avg_ear < 0.21:
                score, status, action, pred_label = 30, "疲劳", "Drowsy", 0
            elif symmetry > 0.18:
                score, status, action, pred_label = 50, "分心", "Looking Around", 0

        # --- 准确率计算逻辑 ---
        if true_label is not None:
            self.metrics["total"] += 1
            if pred_label == 1 and true_label == 1:
                self.metrics["TP"] += 1
            elif pred_label == 1 and true_label == 0:
                self.metrics["FP"] += 1
            elif pred_label == 0 and true_label == 0:
                self.metrics["TN"] += 1
            elif pred_label == 0 and true_label == 1:
                self.metrics["FN"] += 1

        return score, status, action

    def get_accuracy_report(self):
        """计算并返回准确率报告"""
        m = self.metrics
        if m["total"] == 0: return "无测试数据"

        # 准确率 (Accuracy): 预测正确的比例
        acc = (m["TP"] + m["TN"]) / m["total"]

        # 精确率 (Precision): 报警确实准确的比例
        precision = m["TP"] / (m["TP"] + m["FP"]) if (m["TP"] + m["FP"]) > 0 else 0

        return {
            "Accuracy": f"{acc:.2%}",
            "Precision": f"{precision:.2%}",
            "Samples": m["total"]
        }
