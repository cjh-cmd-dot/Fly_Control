import cv2
import numpy as np

#   工具类
#   获取视屏信息
#   展示&保存视频
#   标记坐标
#   逆光补偿
#   质心法轮廓去重

class CvTools:
    def __init__(self):
        pass
# ---------------------------------------------
# --------------------基本类--------------------
# ---------------------------------------------

    # 获取视频信息
    @staticmethod
    def get_video_info(capture):
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = capture.get(cv2.CAP_PROP_FPS)

        out = cv2.VideoWriter('output_video.mp4', cv2.VideoWriter_fourcc(
            *'mp4v'), fps, (width, height))  # 创建VideoWriter对象

        return width, height, fps, out

    # 展示&保存视频
    @staticmethod
    def imshow_and_save(frame, out):
        windows_name: str = 'Camera 720p'
        cv2.namedWindow(windows_name, cv2.WINDOW_NORMAL)  # 窗口大小任意调节
        cv2.imshow(windows_name, frame)
        out.write(frame)  # 写入视频

    # 标记中心
    # 当flag == 0时返回识别轮廓的中心点
    # 当flag == 1时按照轮廓绘图，反之不绘图
    @staticmethod
    def mark(contour, frame_copy, shape, flag):

        x, y, w, h = cv2.boundingRect(contour)

        M = cv2.moments(contour)
        if M["m00"] == 0:
            return frame_copy, [0, 0]

        center_x = int(M['m10'] / M['m00'])
        center_y = int(M['m01'] / M['m00'])
        center = [center_x, center_y]

        if flag == 0:
            return center

        if flag == 1:

            if shape == "circle":
                radius = int(max(w, h) / 2)

                cv2.circle(frame_copy,(center_x, center_y),
                           radius,(0, 255, 0),2)

                cv2.putText(frame_copy, "circle",(center_x, center_y),cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,(0, 255, 0),2)

            else:
                cv2.polylines(frame_copy, [contour], True, (0, 255, 0), 2)

                cv2.putText(frame_copy, shape,(center_x, center_y),cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,(0, 255, 0),2)

            return frame_copy, center

    # 计算轮廓中心坐标
    #   frame 绘制后的图像
    #   coordinate：计算后的坐标
    @staticmethod
    def cal_coordinate(contour, frame):

        M = cv2.moments(contour)
        if M["m00"] == 0:
            return frame, [0, 0]
        #   轮廓中心
        center_x = int(M['m10'] / M['m00'])
        center_y = int(M['m01'] / M['m00'])
        #   图像中心
        img_h, img_w = frame.shape[:2]
        img_center_x = img_w // 2
        img_center_y = img_h // 2

        #   绘制轮廓中心与图像中心
        cv2.circle(frame, (center_x, center_y), 1, (0, 0, 255), -1)
        cv2.circle(frame, (img_center_x, img_center_y), 1, (0, 0, 255), -1)
        #   绘制坐标轴（以图像中心为原点）
        cv2.line(frame, (0, img_center_y), (img_w, img_center_y), (0, 0, 0), 3)  # X轴
        cv2.line(frame, (img_center_x, 0), (img_center_x, img_h), (0, 0, 0), 3)  # Y轴
        #   连线，图像中心到轮廓中心
        cv2.line(frame,(img_center_x, img_center_y),(center_x, center_y),(255, 0, 0), 1)

        #   计算出在中心坐标轴的坐标
        dx = center_x - img_center_x
        dy = img_center_y - center_y
        coordinate = [dx, dy]
        #   在图像上显示出
        text = f"({dx}, {dy})"
        cv2.putText(frame, text,(center_x + 10, center_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5, (0, 0, 255), 1)

        return frame, coordinate

    # 逆光补偿
    @staticmethod
    def backlight_compensation(frame):
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = clahe.apply(l)
        lab = cv2.merge((l, a, b))
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return result

    # 质心法轮廓去重
    @staticmethod
    def filter_contours_by_centroid(contours, min_dist=20):
        contour_centers = []
        filtered_contours = []

        for cnt in contours:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                # 检查是否与已有质心距离过近
                if all(np.hypot(cx - x, cy - y) > min_dist for x, y in contour_centers):
                    contour_centers.append((cx, cy))
                    filtered_contours.append(cnt)  # 仅保留间距足够的轮廓

        return filtered_contours

    # 设置ROI区域，并且在图像上画框显示坐标轴
    @staticmethod
    def set_roi(frame, x, y, w, h):
        roi = frame[y:y+h, x:x+w]
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        # 绘制坐标轴
        cv2.line(frame, (x + w//2, y), (x + w//2, y + h), (255, 0, 0), 1)  # 垂直线
        cv2.line(frame, (x, y + h//2), (x + w, y + h//2), (255, 0, 0), 1)  # 水平线
        return roi
