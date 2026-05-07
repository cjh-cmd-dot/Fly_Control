# ————————————————————————
#   基本简单任务检测
# ————————————————————————

import cv2
import numpy as np


class Vision:

    def __init__(self):
        pass

    # =========================
    #   颜色检测
    # =========================
    @staticmethod
    def _build_color_masks(hsv_frame):
        ranges = {
            "red": [
                (np.array([0, 50, 50]), np.array([10, 255, 255])),
                (np.array([170, 50, 50]), np.array([180, 255, 255]))
            ],
            "blue": [
                (np.array([90, 90, 50]), np.array([150, 255, 255]))
            ],
            "green": [
                (np.array([40, 50, 50]), np.array([80, 255, 255]))
            ],
            "yellow": [
                (np.array([20, 150, 100]), np.array([30, 255, 230]))
            ],
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

            contours, _ = cv2.findContours(
                mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            color_list.append((color, contours))

        return color_list, color_mask

    # =========================
    #   mask 预处理
    # =========================
    @staticmethod
    def _preprocess_mask(mask):
        kernel = np.ones((5, 5), np.uint8)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 3x3 比 5x5 更不容易把多边形角点抹圆
        mask = cv2.GaussianBlur(mask, (3, 3), 0)

        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

        return mask

    # =========================
    #   多边形拟合
    # =========================
    @staticmethod
    def _regularize_contour(cnt, epsilon_factor):
        perimeter = cv2.arcLength(cnt, True)

        if perimeter < 1e-5:
            return cnt

        epsilon = max(1.0, epsilon_factor * perimeter)

        approx = cv2.approxPolyDP(
            cnt,
            epsilon,
            True
        )

        if len(approx) >= 3 and not cv2.isContourConvex(approx):
            approx = cv2.convexHull(approx)

        return approx

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
    def _edge_ratio(approx, min_edge_length=8.0):
        edges = Vision._polygon_edge_lengths(approx)
        filtered = [e for e in edges if e > min_edge_length]

        if len(filtered) < 3:
            return 999.0

        min_e = min(filtered)

        if min_e <= 1e-6:
            return 999.0

        return max(filtered) / min_e

    # =========================
    #   多边形分类
    # =========================
    @staticmethod
    def _classify_polygon(cnt, approx):
        num_vertices = len(approx)

        if num_vertices == 3:
            return "triangle"

        if num_vertices == 4:
            x, y, w, h = cv2.boundingRect(cnt)

            if h <= 0:
                return "quadrilateral"

            aspect_ratio = float(w) / float(h)

            if 0.5 < aspect_ratio < 2.0:
                return "rectangle"

            return "quadrilateral"

        if num_vertices == 5:
            return "pentagon"

        if num_vertices == 6:
            return "hexagon"

        return None

    # =========================
    #   稳定多边形保护
    # =========================
    @staticmethod
    def _definite_polygon_guard(cnt):
        """
        明确多边形优先保护。

        目的：
            防止五边形/六边形因为边缘圆滑、透视变形，
            被圆形/椭圆判断抢走。

        返回：
            shape_name, approx
        """
        approx_fine = Vision._regularize_contour(cnt, 0.018)
        approx_main = Vision._regularize_contour(cnt, 0.025)
        approx_coarse = Vision._regularize_contour(cnt, 0.035)

        if approx_fine is None or approx_main is None or approx_coarse is None:
            return None, None

        n_fine = len(approx_fine)
        n_main = len(approx_main)
        n_coarse = len(approx_coarse)

        # 三角形 / 四边形
        if n_main in [3, 4]:
            return Vision._classify_polygon(cnt, approx_main), approx_main

        # 五边形保护：
        # 只要主拟合或粗拟合稳定出现 5 个点，就优先认为是五边形
        if n_main == 5 or n_coarse == 5:
            return "pentagon", approx_main if n_main == 5 else approx_coarse

        # 如果细拟合多出一个点，粗拟合回到 5，也认为是五边形毛刺
        if n_fine == 6 and n_main == 6 and n_coarse == 5:
            return "pentagon", approx_coarse

        # 六边形保护：
        # 三个尺度都支持 6，才认为是真六边形
        if n_fine == 6 and n_main == 6 and n_coarse == 6:
            ratio = Vision._edge_ratio(approx_main)

            # 这里放宽，不轻易 irregular
            if ratio <= 3.5:
                return "hexagon", approx_main

        return None, None

    # =========================
    #   圆形判断：收紧版
    # =========================
    @staticmethod
    def _is_circle_contour(
        cnt,
        area,
        circularity,
        circularity_threshold=0.86
    ):
        """
        标准圆判断。

        这里收紧到 0.86，
        防止多边形被圆形抢走。
        """
        if circularity < circularity_threshold:
            return False

        (_, _), radius = cv2.minEnclosingCircle(cnt)

        if radius <= 0:
            return False

        area_circle = np.pi * radius ** 2

        if area_circle <= 0:
            return False

        circle_fit_ratio = area / area_circle

        # 收紧：真实圆形才应该比较接近外接圆
        return circle_fit_ratio > 0.78

    # =========================
    #   椭圆 / 斜视圆判断：收紧版
    # =========================
    @staticmethod
    def _is_ellipse_contour(
        cnt,
        area,
        circularity,
        ellipticality_threshold=0.62,
        axis_ratio_threshold=0.55,
        fit_ratio_threshold=0.72
    ):
        """
        斜拍圆判断。

        注意：
            这一步放在明确多边形保护之后。
            只有不是稳定多边形，才允许判 circle。
        """
        if len(cnt) < 5:
            return False

        if circularity < ellipticality_threshold:
            return False

        try:
            _, (axis1, axis2), _ = cv2.fitEllipse(cnt)
        except cv2.error:
            return False

        if axis1 <= 0 or axis2 <= 0:
            return False

        major_axis = max(axis1, axis2)
        minor_axis = min(axis1, axis2)

        axis_ratio = minor_axis / major_axis

        if axis_ratio < axis_ratio_threshold:
            return False

        area_ellipse = np.pi * (major_axis / 2.0) * (minor_axis / 2.0)

        if area_ellipse <= 0:
            return False

        fit_ratio = area / area_ellipse

        return fit_ratio > fit_ratio_threshold

    # =========================
    #   形状检测函数
    # =========================
    @staticmethod
    def shape_detect(
        mask_frame,
        min_area=100,
        circularity_threshold=0.86,
        epsilon_factor=0.025
    ):
        """
        当前策略：

            1. 明确多边形保护先执行
            2. 稳定五边形/六边形优先判 polygon
            3. 不是稳定多边形时，才判断 circle
            4. 不轻易输出 irregular_polygon

        解决：
            多边形被误识别成 circle
        """

        shape_list = []

        try:
            processed_mask = Vision._preprocess_mask(mask_frame)

            contours, _ = cv2.findContours(
                processed_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            for cnt in contours:
                try:
                    area = cv2.contourArea(cnt)

                    if area < min_area:
                        continue

                    perimeter = cv2.arcLength(cnt, True)

                    if perimeter < 1e-5:
                        continue

                    circularity = 4.0 * np.pi * area / (perimeter ** 2)

                    M = cv2.moments(cnt)

                    if M["m00"] < 1e-5:
                        continue

                    # ==========================
                    # 1. 明确多边形优先保护
                    # ==========================
                    stable_poly_name, stable_poly_approx = Vision._definite_polygon_guard(cnt)

                    if stable_poly_name is not None:
                        shape_list.append((stable_poly_name, stable_poly_approx))
                        continue

                    # ==========================
                    # 2. 普通多边形判断
                    # ==========================
                    approx = Vision._regularize_contour(cnt, epsilon_factor)
                    shape_name = Vision._classify_polygon(cnt, approx)

                    if shape_name is not None:
                        # 五边形、六边形直接保留
                        if shape_name in ["pentagon", "hexagon"]:
                            shape_list.append((shape_name, approx))
                            continue

                        # 三角形、四边形也优先保留
                        if shape_name in ["triangle", "rectangle", "quadrilateral"]:
                            shape_list.append((shape_name, approx))
                            continue

                    # ==========================
                    # 3. 圆形检测：放在多边形之后
                    # ==========================
                    if Vision._is_circle_contour(
                        cnt,
                        area,
                        circularity,
                        circularity_threshold=circularity_threshold
                    ):
                        shape_list.append(("circle", cnt))
                        continue

                    # ==========================
                    # 4. 椭圆 / 斜视圆检测
                    # ==========================
                    if Vision._is_ellipse_contour(
                        cnt,
                        area,
                        circularity,
                        ellipticality_threshold=0.62,
                        axis_ratio_threshold=0.55,
                        fit_ratio_threshold=0.72
                    ):
                        shape_list.append(("circle", cnt))
                        continue

                    # ==========================
                    # 5. 兜底：尽量规则化
                    # ==========================
                    if approx is not None and len(approx) >= 3:
                        num_vertices = len(approx)

                        if num_vertices == 5:
                            shape_list.append(("pentagon", approx))
                            continue

                        if num_vertices == 6:
                            shape_list.append(("hexagon", approx))
                            continue

                        shape_list.append(("irregular_polygon", approx))
                        continue

                except Exception as e:
                    print(f"警告：处理轮廓时出错: {e}")
                    continue

            return shape_list, processed_mask

        except Exception as e:
            print(f"错误：形状检测失败: {e}")
            return [], None