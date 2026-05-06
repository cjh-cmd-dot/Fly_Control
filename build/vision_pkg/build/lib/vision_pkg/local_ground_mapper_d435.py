#!/usr/bin/env python3
import math
import cv2
import numpy as np
import pyrealsense2 as rs


class LocalGroundMapper:
    """
    局部地面拟合 + 像素射线求交模块

    设计目标：
        1. 不需要提前知道摄像头安装角度
        2. 不依赖目标中心深度
        3. 不依赖全局地面模型
        4. 每个目标附近单独拟合局部地面
        5. 质量差时直接拒绝，不发布错误坐标

    RealSense 相机坐标系：
        X: 右
        Y: 下
        Z: 前

    输出地面坐标：
        x_ground: 地面左右方向
        y_ground: 离局部地面的高度，理论上接近 0
        z_ground: 沿局部地面向前方向
    """

    def __init__(
        self,
        sample_step=6,
        ring_margin=45,
        target_dilate=18,
        min_depth=0.20,
        max_depth=5.00,

        min_points=60,
        ransac_iterations=120,
        ransac_dist_thresh=0.025,

        max_plane_rms=0.025,
        min_inlier_ratio=0.45,

        depth_edge_thresh=0.08,
        max_ray_plane_angle_deg=82.0,

        max_normal_jump_deg=35.0,
        max_d_jump=0.20,

        max_ground_z=3.0,
        logger=None
    ):
        # 采样参数
        self.sample_step = sample_step
        self.ring_margin = ring_margin
        self.target_dilate = target_dilate
        self.min_depth = min_depth
        self.max_depth = max_depth

        # RANSAC 参数
        self.min_points = min_points
        self.ransac_iterations = ransac_iterations
        self.ransac_dist_thresh = ransac_dist_thresh

        # 质量评分阈值
        self.max_plane_rms = max_plane_rms
        self.min_inlier_ratio = min_inlier_ratio
        self.depth_edge_thresh = depth_edge_thresh
        self.max_ray_plane_angle_deg = max_ray_plane_angle_deg

        # 防止明显错误平面突变
        self.max_normal_jump_deg = max_normal_jump_deg
        self.max_d_jump = max_d_jump

        self.max_ground_z = max_ground_z
        self.logger = logger

        # RealSense 相机坐标：Y 向下，所以相机“上方”是 [0, -1, 0]
        self.camera_up = np.array([0.0, -1.0, 0.0], dtype=np.float32)

        # 保存上一帧可信局部平面，仅用于拒绝明显错误，不用于慢平滑
        self.last_valid_normal = None
        self.last_valid_d = None

    # ======================
    # 日志
    # ======================
    def log_warn(self, text):
        if self.logger is not None:
            self.logger.warn(text)

    def log_debug(self, text):
        if self.logger is not None:
            self.logger.debug(text)

    # ======================
    # 像素转相机射线
    # ======================
    def pixel_to_ray(self, intrinsics, u, v):
        """
        根据相机内参，把像素点转换成相机坐标系下的一条射线。

        注意：
            这里不使用目标中心深度。
            只使用像素方向。
        """
        x = (float(u) - intrinsics.ppx) / intrinsics.fx
        y = (float(v) - intrinsics.ppy) / intrinsics.fy
        z = 1.0

        ray = np.array([x, y, z], dtype=np.float32)
        norm = np.linalg.norm(ray)

        if norm < 1e-6:
            return None

        return ray / norm

    # ======================
    # 深度边缘判断
    # ======================
    def is_depth_edge_point(self, depth_frame, u, v):
        """
        判断采样点附近深度是否突变。

        作用：
            过滤台阶边缘、目标边缘、深度空洞边缘。
            这些地方不适合参与地面拟合。
        """
        width = depth_frame.get_width()
        height = depth_frame.get_height()

        offsets = [
            (0, 0),
            (-3, 0),
            (3, 0),
            (0, -3),
            (0, 3)
        ]

        values = []

        for du, dv in offsets:
            x = int(u + du)
            y = int(v + dv)

            if x < 0 or x >= width or y < 0 or y >= height:
                continue

            d = depth_frame.get_distance(x, y)

            if self.min_depth <= d <= self.max_depth:
                values.append(d)

        if len(values) < 3:
            return True

        return (max(values) - min(values)) > self.depth_edge_thresh

    # ======================
    # 中值深度
    # ======================
    def get_median_depth_at(self, depth_frame, u, v, size=2):
        values = []

        width = depth_frame.get_width()
        height = depth_frame.get_height()

        for dy in range(-size, size + 1):
            for dx in range(-size, size + 1):
                x = int(u + dx)
                y = int(v + dy)

                if x < 0 or x >= width or y < 0 or y >= height:
                    continue

                d = depth_frame.get_distance(x, y)

                if self.min_depth <= d <= self.max_depth:
                    values.append(d)

        if len(values) == 0:
            return None

        return float(np.median(values))

    # ======================
    # 反投影
    # ======================
    def deproject(self, intrinsics, u, v, depth):
        point = rs.rs2_deproject_pixel_to_point(
            intrinsics,
            [float(u), float(v)],
            float(depth)
        )

        return np.array(point, dtype=np.float32)

    # ======================
    # 构造目标周围环形采样 mask
    # ======================
    def build_ring_sample_mask(self, image_shape, contour):
        """
        在目标轮廓周围构造环形区域：

            外部矩形区域
                -
            目标膨胀区域
                =
            目标周围地面采样区域

        这样可以避免采到目标本身的深度。
        """
        height, width = image_shape[:2]

        x, y, w, h = cv2.boundingRect(contour)

        x1 = max(0, x - self.ring_margin)
        y1 = max(0, y - self.ring_margin)
        x2 = min(width - 1, x + w + self.ring_margin)
        y2 = min(height - 1, y + h + self.ring_margin)

        outer_mask = np.zeros((height, width), dtype=np.uint8)
        outer_mask[y1:y2, x1:x2] = 255

        target_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.drawContours(target_mask, [contour], -1, 255, thickness=-1)

        kernel_size = max(3, int(self.target_dilate))
        kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)

        dilated_target = cv2.dilate(target_mask, kernel, iterations=1)

        ring_mask = cv2.bitwise_and(
            outer_mask,
            cv2.bitwise_not(dilated_target)
        )

        return ring_mask, (x1, y1, x2, y2)

    # ======================
    # 采样目标附近局部地面点
    # ======================
    def sample_local_ground_points(self, depth_frame, intrinsics, contour, image_shape):
        ring_mask, bbox = self.build_ring_sample_mask(image_shape, contour)

        x1, y1, x2, y2 = bbox

        points = []

        for v in range(y1, y2, self.sample_step):
            for u in range(x1, x2, self.sample_step):
                if ring_mask[v, u] == 0:
                    continue

                if self.is_depth_edge_point(depth_frame, u, v):
                    continue

                depth = self.get_median_depth_at(depth_frame, u, v, size=1)

                if depth is None:
                    continue

                if depth < self.min_depth or depth > self.max_depth:
                    continue

                point = self.deproject(intrinsics, u, v, depth)
                points.append(point)

        if len(points) < self.min_points:
            return None, ring_mask

        return np.array(points, dtype=np.float32), ring_mask

    # ======================
    # 三点拟合平面
    # ======================
    def fit_plane_from_3points(self, p1, p2, p3):
        v1 = p2 - p1
        v2 = p3 - p1

        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal)

        if norm < 1e-6:
            return None, None

        normal = normal / norm
        d = -float(np.dot(normal, p1))

        # 让法向量朝向相机上方一侧
        if np.dot(normal, self.camera_up) < 0:
            normal = -normal
            d = -d

        if d < 0:
            normal = -normal
            d = -d

        return normal.astype(np.float32), float(d)

    # ======================
    # SVD 精拟合
    # ======================
    def fit_plane_svd(self, points):
        if points is None or len(points) < self.min_points:
            return None, None

        centroid = np.mean(points, axis=0)
        centered = points - centroid

        try:
            _, _, vh = np.linalg.svd(centered)
        except np.linalg.LinAlgError:
            return None, None

        normal = vh[-1, :]
        norm = np.linalg.norm(normal)

        if norm < 1e-6:
            return None, None

        normal = normal / norm
        d = -float(np.dot(normal, centroid))

        if np.dot(normal, self.camera_up) < 0:
            normal = -normal
            d = -d

        if d < 0:
            normal = -normal
            d = -d

        return normal.astype(np.float32), float(d)

    # ======================
    # 向量夹角
    # ======================
    def angle_between_vectors_deg(self, v1, v2):
        v1 = np.array(v1, dtype=np.float32)
        v2 = np.array(v2, dtype=np.float32)

        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)

        if n1 < 1e-6 or n2 < 1e-6:
            return 180.0

        v1 = v1 / n1
        v2 = v2 / n2

        cos_value = float(np.dot(v1, v2))
        cos_value = max(-1.0, min(1.0, cos_value))

        return math.degrees(math.acos(cos_value))

    # ======================
    # RANSAC 局部平面拟合
    # ======================
    def fit_plane_ransac(self, points):
        if points is None or len(points) < self.min_points:
            return None

        n_points = len(points)

        best_normal = None
        best_d = None
        best_inlier_mask = None
        best_score = -1

        for _ in range(self.ransac_iterations):
            ids = np.random.choice(n_points, 3, replace=False)

            normal, d = self.fit_plane_from_3points(
                points[ids[0]],
                points[ids[1]],
                points[ids[2]]
            )

            if normal is None:
                continue

            distances = np.abs(points @ normal + d)
            inlier_mask = distances < self.ransac_dist_thresh
            inlier_count = int(np.sum(inlier_mask))

            if inlier_count < self.min_points:
                continue

            if inlier_count > best_score:
                best_score = inlier_count
                best_normal = normal
                best_d = d
                best_inlier_mask = inlier_mask

        if best_normal is None or best_inlier_mask is None:
            return None

        inliers = points[best_inlier_mask]

        # 用内点再 SVD 精拟合
        normal2, d2 = self.fit_plane_svd(inliers)

        if normal2 is None:
            normal2 = best_normal
            d2 = best_d

        distances = np.abs(points @ normal2 + d2)
        final_inlier_mask = distances < self.ransac_dist_thresh
        final_inliers = points[final_inlier_mask]

        if len(final_inliers) < self.min_points:
            return None

        rms = float(np.sqrt(np.mean((final_inliers @ normal2 + d2) ** 2)))
        inlier_ratio = float(len(final_inliers)) / float(len(points))

        result = {
            "normal": normal2,
            "d": float(d2),
            "inliers": final_inliers,
            "inlier_count": int(len(final_inliers)),
            "total_count": int(len(points)),
            "inlier_ratio": inlier_ratio,
            "rms": rms
        }

        return result

    # ======================
    # 平面质量检查
    # ======================
    def check_plane_quality(self, plane_result):
        if plane_result is None:
            return False, "plane_result is None"

        normal = plane_result["normal"]
        d = plane_result["d"]
        rms = plane_result["rms"]
        inlier_ratio = plane_result["inlier_ratio"]
        inlier_count = plane_result["inlier_count"]

        if inlier_count < self.min_points:
            return False, f"inlier_count too small: {inlier_count}"

        if inlier_ratio < self.min_inlier_ratio:
            return False, f"inlier_ratio too low: {inlier_ratio:.2f}"

        if rms > self.max_plane_rms:
            return False, f"plane rms too large: {rms:.3f}"

        # 防止明显不是地面的平面
        angle_to_up = self.angle_between_vectors_deg(normal, self.camera_up)

        if angle_to_up > 80.0:
            return False, f"normal unreasonable: {angle_to_up:.1f} deg"

        # 和上一帧可信平面差异太大，认为当前帧深度可能坏了
        if self.last_valid_normal is not None:
            angle_jump = self.angle_between_vectors_deg(
                normal,
                self.last_valid_normal
            )

            if angle_jump > self.max_normal_jump_deg:
                return False, f"normal jump too large: {angle_jump:.1f} deg"

        if self.last_valid_d is not None:
            d_jump = abs(d - self.last_valid_d)

            if d_jump > self.max_d_jump:
                return False, f"d jump too large: {d_jump:.3f} m"

        return True, "ok"

    # ======================
    # 像素射线和平面求交
    # ======================
    def intersect_pixel_ray_with_plane(self, intrinsics, u, v, normal, d):
        ray = self.pixel_to_ray(intrinsics, u, v)

        if ray is None:
            return None

        denom = float(np.dot(normal, ray))

        if abs(denom) < 1e-6:
            return None

        # 射线与平面：
        # n · (t * ray) + d = 0
        # t = -d / (n · ray)
        t = -float(d) / denom

        if t <= 0:
            return None

        # 射线太贴近地面时，交点会被放大得很远，不可靠
        angle = self.angle_between_vectors_deg(ray, normal)
        ray_plane_angle = abs(90.0 - angle)

        if ray_plane_angle > self.max_ray_plane_angle_deg:
            return None

        point = t * ray

        return point.astype(np.float32)

    # ======================
    # 建立局部地面坐标系
    # ======================
    def build_ground_axes(self, normal):
        ey = normal / np.linalg.norm(normal)

        camera_z = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        ez = camera_z - np.dot(camera_z, ey) * ey
        ez_norm = np.linalg.norm(ez)

        if ez_norm < 1e-6:
            return None, None, None

        ez = ez / ez_norm

        if np.dot(ez, camera_z) < 0:
            ez = -ez

        ex = np.cross(ez, ey)
        ex_norm = np.linalg.norm(ex)

        if ex_norm < 1e-6:
            return None, None, None

        ex = ex / ex_norm

        return ex.astype(np.float32), ey.astype(np.float32), ez.astype(np.float32)

    # ======================
    # 相机点转局部地面坐标
    # ======================
    def point_to_local_ground_coord(self, point_cam, normal, d):
        ex, ey, ez = self.build_ground_axes(normal)

        if ex is None:
            return None

        # 相机原点在局部地面上的投影
        ground_origin = -d * normal

        rel = point_cam - ground_origin

        x_ground = float(np.dot(rel, ex))
        y_ground = float(np.dot(rel, ey))
        z_ground = float(np.dot(rel, ez))

        return x_ground, y_ground, z_ground

    # ======================
    # 主接口：根据目标轮廓和中心点计算地面坐标
    # ======================
    def estimate_target_ground_coord(
        self,
        depth_frame,
        intrinsics,
        image_shape,
        contour,
        cx,
        cy
    ):
        """
        返回：
            success, result

        success=True:
            result = {
                "x": ...,
                "y": ...,
                "z": ...,
                "plane_rms": ...,
                "inlier_ratio": ...,
                "inlier_count": ...,
                "total_count": ...,
                "ring_mask": ...
            }

        success=False:
            result = {
                "reason": ...,
                "ring_mask": ...
            }
        """
        points, ring_mask = self.sample_local_ground_points(
            depth_frame,
            intrinsics,
            contour,
            image_shape
        )

        if points is None:
            return False, {
                "reason": "local ground points not enough",
                "ring_mask": ring_mask
            }

        plane_result = self.fit_plane_ransac(points)

        ok, reason = self.check_plane_quality(plane_result)

        if not ok:
            return False, {
                "reason": reason,
                "ring_mask": ring_mask
            }

        normal = plane_result["normal"]
        d = plane_result["d"]

        point_on_ground = self.intersect_pixel_ray_with_plane(
            intrinsics,
            cx,
            cy,
            normal,
            d
        )

        if point_on_ground is None:
            return False, {
                "reason": "ray plane intersection failed",
                "ring_mask": ring_mask
            }

        ground_coord = self.point_to_local_ground_coord(
            point_on_ground,
            normal,
            d
        )

        if ground_coord is None:
            return False, {
                "reason": "build local ground coord failed",
                "ring_mask": ring_mask
            }

        x_ground, y_ground, z_ground = ground_coord

        if not (0.0 < z_ground <= self.max_ground_z):
            return False, {
                "reason": f"z_ground out of range: {z_ground:.3f}",
                "ring_mask": ring_mask
            }

        # 当前帧质量合格，立即更新上一帧可信平面
        # 注意：这里只保存，不做 EMA 慢平滑
        self.last_valid_normal = normal
        self.last_valid_d = d

        return True, {
            "x": float(x_ground),
            "y": float(y_ground),
            "z": float(z_ground),
            "plane_rms": float(plane_result["rms"]),
            "inlier_ratio": float(plane_result["inlier_ratio"]),
            "inlier_count": int(plane_result["inlier_count"]),
            "total_count": int(plane_result["total_count"]),
            "ring_mask": ring_mask
        }