# ————————————————————————
#   基本简单任务检测
# ————————————————————————

import cv2
import numpy as np


class Vision:

    def __init__(self):
        pass

    # =========================
    # 颜色阈值
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

            # 原代码 yellow 的 V 上限是 230。
            # 如果你的黄色目标有反光，建议改成 255。
            # 如果你不想识别太亮的淡黄色，可以再改回 230。
            "yellow": [
                (np.array([20, 150, 100]), np.array([30, 255, 255]))
            ],
        }

        kernel = np.ones((5, 5), np.uint8)
        masks = {}

        for color, ranges_list in ranges.items():
            mask = None

            for lower, upper in ranges_list:
                current = cv2.inRange(hsv_frame, lower, upper)
                mask = current if mask is None else cv2.bitwise_or(mask, current)

            # 去除小噪点
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # 填补目标内部小空洞
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            masks[color] = mask

        return masks

    # =========================
    # 颜色检测
    # 返回：
    #   color_list: [(color_name, contours), ...]
    #   color_mask: 所有颜色合并 mask
    # =========================
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
    # mask 预处理
    # =========================
    @staticmethod
    def _preprocess_mask(mask):
        kernel = np.ones((5, 5), np.uint8)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        _, mask = cv2.threshold(
            mask,
            127,
            255,
            cv2.THRESH_BINARY
        )

        return mask

    # =========================
    # 多边形拟合
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

        # 对多边形检测来说，凸包能减少破碎边缘影响
        if len(approx) >= 3 and not cv2.isContourConvex(approx):
            approx = cv2.convexHull(approx)

        return approx

    # =========================
    # 计算多边形边长
    # =========================
    @staticmethod
    def _polygon_edge_lengths(approx):
        points = approx.reshape(-1, 2)

        edges = []

        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]

            edges.append(float(np.linalg.norm(p1 - p2)))

        return edges

    # =========================
    # 判断边长是否过于不规则
    # =========================
    @staticmethod
    def _is_irregular_polygon_by_edge(
        approx,
        min_edge_length=10.0,
        edge_ratio_threshold=2.0
    ):
        edges = Vision._polygon_edge_lengths(approx)

        if len(edges) < 3:
            return False

        filtered = [e for e in edges if e > min_edge_length]

        if len(filtered) < 2:
            return False

        min_e = min(filtered)

        if min_e < 1e-5:
            return True

        return (max(filtered) / min_e) > edge_ratio_threshold

    # =========================
    # 稳定多边形候选判断
    # =========================
    @staticmethod
    def _is_regular_polygon_candidate(
        approx,
        expected_vertices,
        edge_ratio_threshold=2.0,
        min_edge_length=8.0
    ):
        """
        判断是否是稳定的规则/近规则多边形。

        主要用途：
            防止规则六边形被 fitEllipse 误识别成圆。

        注意：
            这里不是要求绝对规则，只要求：
                1. 顶点数符合
                2. 是凸多边形
                3. 边长比例不要太离谱
        """
        if approx is None:
            return False

        if len(approx) != expected_vertices:
            return False

        if not cv2.isContourConvex(approx):
            return False

        edges = Vision._polygon_edge_lengths(approx)

        if len(edges) != expected_vertices:
            return False

        filtered = [e for e in edges if e > min_edge_length]

        if len(filtered) != expected_vertices:
            return False

        min_e = min(filtered)
        max_e = max(filtered)

        if min_e < 1e-5:
            return False

        edge_ratio = max_e / min_e

        if edge_ratio > edge_ratio_threshold:
            return False

        return True

    # =========================
    # 明确六边形判断
    # =========================
    @staticmethod
    def _is_definite_hexagon(cnt):
        """
        判断是否是明确的六边形。

        这个函数必须在椭圆检测前使用。

        原因：
            六边形轮廓点足够多时，cv2.fitEllipse 也能拟合出椭圆。
            拟合成功不代表它就是圆/椭圆。
        """
        perimeter = cv2.arcLength(cnt, True)

        if perimeter < 1e-5:
            return False

        # 较大的 epsilon：寻找主要角点
        approx_coarse = cv2.approxPolyDP(
            cnt,
            0.025 * perimeter,
            True
        )

        if not Vision._is_regular_polygon_candidate(
            approx_coarse,
            expected_vertices=6,
            edge_ratio_threshold=2.0,
            min_edge_length=8.0
        ):
            return False

        # 较小的 epsilon：验证角点是否稳定
        approx_fine = cv2.approxPolyDP(
            cnt,
            0.012 * perimeter,
            True
        )

        # 真六边形在更小 epsilon 下，顶点数通常仍接近 6。
        # 斜视圆/椭圆在更小 epsilon 下会出现更多点。
        if 6 <= len(approx_fine) <= 8:
            return True

        return False

    # =========================
    # 标准圆检测
    # =========================
    @staticmethod
    def _is_circle_contour(
        cnt,
        area,
        circularity,
        circularity_threshold
    ):
        """
        标准圆检测。

        对摄像头正对目标时效果好。
        斜放时圆会变成椭圆，可能走下面的 _is_ellipse_contour。
        """
        if circularity <= circularity_threshold:
            return False

        (_, _), radius = cv2.minEnclosingCircle(cnt)

        if radius <= 0:
            return False

        area_circle = np.pi * radius ** 2

        if area_circle <= 0:
            return False

        circle_fit_ratio = area / area_circle

        # 圆的实际面积应该接近外接圆面积
        return circle_fit_ratio > 0.80

    # =========================
    # 椭圆 / 斜视圆检测
    # =========================
    @staticmethod
    def _is_ellipse_contour(
        cnt,
        area,
        circularity,
        ellipticality_threshold=0.45,
        axis_ratio_threshold=0.35,
        fit_ratio_threshold=0.60,
        polygon_vertex_reject=True
    ):
        """
        判断是否是椭圆。

        用途：
            摄像头斜放时，地面圆形会投影成椭圆。
            这里把这种椭圆仍然当作 circle 返回。

        防误判：
            1. 明确六边形直接拒绝
            2. 明显稳定多边形直接拒绝
            3. 面积比例过小或过大拒绝
        """
        if len(cnt) < 5:
            return False

        if circularity <= ellipticality_threshold:
            return False

        perimeter = cv2.arcLength(cnt, True)

        if perimeter < 1e-5:
            return False

        if polygon_vertex_reject:
            # 明确六边形，不允许识别成圆
            if Vision._is_definite_hexagon(cnt):
                return False

            # 明确的三角形、四边形、五边形、六边形，不走椭圆逻辑
            approx_poly = cv2.approxPolyDP(
                cnt,
                0.02 * perimeter,
                True
            )

            if len(approx_poly) in [3, 4, 5, 6]:
                if cv2.isContourConvex(approx_poly):
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

        # 太扁一般不是正常斜视圆，可能是边缘残缺或噪声
        if axis_ratio < axis_ratio_threshold:
            return False

        area_ellipse = np.pi * (major_axis / 2.0) * (minor_axis / 2.0)

        if area_ellipse <= 0:
            return False

        fit_ratio = area / area_ellipse

        # fit_ratio 太小：轮廓不像完整椭圆
        # fit_ratio 太大：可能是其他异常轮廓
        if not (fit_ratio_threshold <= fit_ratio <= 1.20):
            return False

        return True

    # =========================
    # 多边形分类
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

            aspect_ratio = float(w) / h

            if 0.5 < aspect_ratio < 2.0:
                return "rectangle"

            return "quadrilateral"

        if num_vertices == 5:
            return "pentagon"

        if num_vertices == 6:
            return "hexagon"

        return None

    # =========================
    # 形状检测函数
    # =========================
    @staticmethod
    def shape_detect(
        mask_frame,
        min_area=300,
        circularity_threshold=0.75,
        epsilon_factor=0.012
    ):
        """
        形状检测函数。

        检测顺序非常重要：

            1. 明确六边形保护
            2. 标准圆检测
            3. 斜视圆/椭圆检测
            4. 其他多边形检测

        这样可以做到：
            摄像头斜放时，圆可以识别成 circle；
            摄像头斜放时，六边形不会被识别成 circle。
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

                    circularity = 4 * np.pi * area / (perimeter ** 2)

                    M = cv2.moments(cnt)

                    if M["m00"] < 1e-5:
                        continue

                    # ==================================================
                    # 1. 先保护明确六边形
                    # ==================================================
                    # 这一步必须放在椭圆检测前。
                    # 因为六边形也可能被 fitEllipse 拟合成椭圆。
                    if Vision._is_definite_hexagon(cnt):
                        approx_hex = Vision._regularize_contour(
                            cnt,
                            epsilon_factor=0.02
                        )

                        shape_list.append(("hexagon", approx_hex))
                        continue

                    # ==================================================
                    # 2. 标准圆检测
                    # ==================================================
                    if Vision._is_circle_contour(
                        cnt,
                        area,
                        circularity,
                        circularity_threshold
                    ):
                        shape_list.append(("circle", cnt))
                        continue

                    # ==================================================
                    # 3. 椭圆 / 斜视圆检测
                    # ==================================================
                    # 地面上的圆在摄像头斜放时会投影成椭圆。
                    # 但这里内部已经排除了明确六边形。
                    if Vision._is_ellipse_contour(
                        cnt,
                        area,
                        circularity,
                        ellipticality_threshold=0.45,
                        axis_ratio_threshold=0.35,
                        fit_ratio_threshold=0.60,
                        polygon_vertex_reject=True
                    ):
                        shape_list.append(("circle", cnt))
                        continue

                    # ==================================================
                    # 4. 最后判断其他多边形
                    # ==================================================
                    approx = Vision._regularize_contour(
                        cnt,
                        epsilon_factor
                    )

                    shape_name = Vision._classify_polygon(
                        cnt,
                        approx
                    )

                    if shape_name:
                        if Vision._is_irregular_polygon_by_edge(approx):
                            shape_list.append(("irregular_polygon", approx))
                        else:
                            shape_list.append((shape_name, approx))

                        continue

                except Exception as e:
                    print(f"警告：处理轮廓时出错: {e}")
                    continue

            return shape_list, processed_mask

        except Exception as e:
            print(f"错误：形状检测失败: {e}")
            return [], None