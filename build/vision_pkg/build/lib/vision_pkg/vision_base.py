# ————————————————————————
#   基本简单任务检测
# ————————————————————————

import cv2
import numpy as np


class Vision:

    def __init__(self):
        pass

    # =========================
    #   颜色检测(测试过，功能正常）
    #   返回值：
    #       color_list: 轮廓列表[color, contours]
    #       test_frame: 合并mask（用于测试）
    # =========================
    @staticmethod
    def _build_color_masks(hsv_frame):
        ranges = {
            "red": [
                (np.array([0, 50, 50]), np.array([10, 255, 255])),
                (np.array([170, 50, 50]), np.array([180, 255, 255]))
            ],
            "blue": [(np.array([90, 90, 50]), np.array([150, 255, 255]))],
            "green": [(np.array([40, 50, 50]), np.array([80, 255, 255]))],
            "yellow": [(np.array([20, 150, 100]), np.array([30, 255, 230]))],
        }


        kernel = np.ones((5, 5), np.uint8)
        masks = {}

        for color, ranges_list in ranges.items():
            mask = None
            for lower, upper in ranges_list:
                current = cv2.inRange(hsv_frame, lower, upper)
                mask = current if mask is None else cv2.bitwise_or(mask, current)

            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            masks[color] = mask

        return masks

 #   形状检测（测试过，功能正常）
    @staticmethod
    def color_detect(frame):
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        masks = Vision._build_color_masks(hsv_frame)

        color_mask = np.zeros_like(next(iter(masks.values())))
        color_list = []

        for color, mask in masks.items():
            color_mask = cv2.bitwise_or(color_mask, mask)
            if cv2.countNonZero(mask) == 0:
                continue

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color_list.append((color, contours))

        return color_list, color_mask


    @staticmethod
    def _preprocess_mask(mask):
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        return mask

# 
    @staticmethod
    def _regularize_contour(cnt, epsilon_factor):
        perimeter = cv2.arcLength(cnt, True)
        epsilon = max(1.0, epsilon_factor * perimeter)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        if not cv2.isContourConvex(approx):
            approx = cv2.convexHull(approx)
        return approx

    @staticmethod
    def _is_circle_contour(cnt, area, circularity, circularity_threshold):
        if circularity <= circularity_threshold:
            return False

        (_, _), radius = cv2.minEnclosingCircle(cnt)
        if radius <= 0:
            return False

        area_circle = np.pi * radius ** 2
        circle_fit_ratio = area / area_circle
        return circle_fit_ratio > 0.80

    @staticmethod
    def _is_ellipse_contour(cnt, area, circularity,
                            ellipticality_threshold=0.55,
                            axis_ratio_threshold=0.55,
                            fit_ratio_threshold=0.70):
        if len(cnt) < 5:
            return False
        if circularity <= ellipticality_threshold:
            return False

        try:
            _, (major_axis, minor_axis), _ = cv2.fitEllipse(cnt)
        except cv2.error:
            return False

        if major_axis <= 0 or minor_axis <= 0:
            return False

        axis_ratio = min(major_axis, minor_axis) / max(major_axis, minor_axis)
        if axis_ratio < axis_ratio_threshold:
            return False

        area_ellipse = np.pi * (major_axis / 2) * (minor_axis / 2)
        if area_ellipse <= 0:
            return False

        fit_ratio = area / area_ellipse
        return fit_ratio > fit_ratio_threshold


    @staticmethod
    def _polygon_edge_lengths(approx):
        points = approx.reshape(-1, 2)
        edges = []
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            edges.append(float(np.linalg.norm(p1 - p2)))
        return edges

    @staticmethod
    def _is_irregular_polygon_by_edge(approx, min_edge_length=10.0, edge_diff_threshold=10.0):
        edges = Vision._polygon_edge_lengths(approx)
        if len(edges) < 3:
            return False
        filtered = [e for e in edges if e > min_edge_length]
        if len(filtered) < 2:
            return False
        return max(filtered) - min(filtered) > edge_diff_threshold

    @staticmethod
    def _classify_polygon(cnt, approx):
        num_vertices = len(approx)
        if num_vertices == 3:
            return "triangle"
        if num_vertices == 4:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h
            return "rectangle" if 0.5 < aspect_ratio < 2 else "quadrilateral"
        if num_vertices == 5:
            return "pentagon"
        if num_vertices == 6:
            return "hexagon"
        return None


#     形状检测函数（优化版）
#
#     Args:
#         frame: 输入图像
#         min_area: 最小轮廓面积阈值（像素²）
#         circularity_threshold: 圆度判断阈值 (0.7-0.85)
#         epsilon_factor: 多边形拟合精度因子
#
#     Returns:
#         shape_list: [(形状名称, 轮廓), ...]

    @staticmethod
    def shape_detect(mask_frame, min_area=100, circularity_threshold=0.85, epsilon_factor=0.02):

        shape_list = []

        try:
            # 预处理：形态学和二值化帮助抑制抖动噪声
            processed_mask = Vision._preprocess_mask(mask_frame)

            # 二值轮廓提取
            contours, _ = cv2.findContours(processed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                try:
                    # 计算轮廓属性
                    area = cv2.contourArea(cnt)
                    if area < min_area: # 修复：设置最小面积阈值
                        continue

                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter < 1e-5:  # 避免除以零
                        continue

                    # 计算圆度
                    circularity = 4 * np.pi * area / (perimeter ** 2)

                    # 计算重心
                    M = cv2.moments(cnt)
                    if M["m00"] < 1e-5:
                        continue

                    # ========== 多边形检测 ==========
                    approx = Vision._regularize_contour(cnt, epsilon_factor)
                    shape_name = Vision._classify_polygon(cnt, approx)
                    if shape_name:
                        if Vision._is_irregular_polygon_by_edge(approx):
                            shape_list.append(("irregular_polygon", approx))
                        else:
                            shape_list.append((shape_name, approx))
                        continue

                    # ========== 圆形检测 ==========
                    if Vision._is_circle_contour(cnt, area, circularity, circularity_threshold):
                        shape_list.append(("circle", cnt))
                        continue

                    # ========== 椭圆/透视圆检测 ==========
                    # 倾斜视角下，地面上的圆形会投影成椭圆，先尝试拟合椭圆
                    if Vision._is_ellipse_contour(cnt, area, circularity):
                        shape_list.append(("circle", cnt))
                        continue

                except Exception as e:
                    # 单个轮廓处理失败，继续下一个
                    print(f"警告：处理轮廓时出错: {e}")
                    continue
            return shape_list, processed_mask

        except Exception as e:
            print(f"错误：形状检测失败: {e}")
            return [], None