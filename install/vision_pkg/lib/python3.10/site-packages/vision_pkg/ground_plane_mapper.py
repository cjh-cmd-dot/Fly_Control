#!/usr/bin/env python3
import math
import numpy as np
import pyrealsense2 as rs
import cv2


class GroundPlaneMapper:
    """
    当前帧局部地面拟合版

    功能：
        1. 不保存上一帧地面模型
        2. 不做 EMA 滤波
        3. 不做全局地面拟合
        4. 每个目标单独在附近采样地面点
        5. 排除整张图里的所有目标区域，避免相邻目标污染地面拟合
        6. 用目标中心像素射线与局部地面平面求交，得到目标落在地面上的坐标

    RealSense 相机坐标系：
        X：向右
        Y：向下
        Z：向前

    输出地面坐标：
        x_ground：左右方向
        y_ground：离地高度，地面图案理论上接近 0
        z_ground：地面前方距离
    """

    def __init__(
        self,
        roi_expand=90,
        sample_step=6,
        min_points=18,
        plane_dist_thresh=0.07,
        depth_min=0.15,
        depth_max=5.0,
        target_mask_expand=18,
        max_normal_angle_deg=80.0,
        logger=None
    ):
        """
        参数说明：

        roi_expand:
            在目标外接框周围扩大多少像素采样地面点。
            两个目标靠得很近时，可以调大，比如 100、120。

        sample_step:
            采样步长。
            越小越准，但越慢。
            实时性优先建议 6~10。

        min_points:
            局部地面拟合最少点数。
            两个目标很近时，地面点会变少，可以适当调小，比如 15~20。

        plane_dist_thresh:
            平面内点距离阈值，单位 m。
            地面不平整时放宽，比如 0.06~0.10。

        target_mask_expand:
            目标掩码膨胀像素。
            两个目标很近时，建议 15~25，避免目标边缘参与地面拟合。

        max_normal_angle_deg:
            地面法向量和相机上方向的最大夹角。
            局部地面拟合容易变化，所以这里放宽。
        """
        self.roi_expand = roi_expand
        self.sample_step = sample_step
        self.min_points = min_points
        self.plane_dist_thresh = plane_dist_thresh
        self.depth_min = depth_min
        self.depth_max = depth_max
        self.target_mask_expand = target_mask_expand
        self.max_normal_angle_deg = max_normal_angle_deg
        self.logger = logger

        # RealSense 相机坐标：Y 向下，所以相机上方向约为 [0, -1, 0]
        self.camera_up = np.array([0.0, -1.0, 0.0], dtype=np.float32)

    def log_debug(self, text):
        if self.logger is not None:
            self.logger.debug(text)

    def log_warn(self, text):
        if self.logger is not None:
            self.logger.warn(text)

    # ======================
    # 深度单位
    # ======================
    def get_depth_units(self, depth_frame):
        try:
            return float(depth_frame.get_units())
        except Exception:
            # D435 常见深度单位是 0.001 m
            return 0.001

    # ======================
    # 读取某个像素深度
    # ======================
    def depth_at(self, depth_image, depth_units, u, v):
        h, w = depth_image.shape[:2]

        if u < 0 or u >= w or v < 0 or v >= h:
            return 0.0

        raw = depth_image[int(v), int(u)]

        if raw <= 0:
            return 0.0

        return float(raw) * depth_units

    # ======================
    # 像素反投影到相机坐标
    # ======================
    def deproject(self, intrinsics, u, v, depth):
        point = rs.rs2_deproject_pixel_to_point(
            intrinsics,
            [float(u), float(v)],
            float(depth)
        )

        return np.array(point, dtype=np.float32)

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

        cos_angle = float(np.dot(v1, v2))
        cos_angle = max(-1.0, min(1.0, cos_angle))

        return math.degrees(math.acos(cos_angle))

    # ======================
    # SVD 拟合平面
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

        # 保证法向量大致朝向相机上方
        if np.dot(normal, self.camera_up) < 0:
            normal = -normal
            d = -d

        return normal.astype(np.float32), float(d)

    # ======================
    # 鲁棒拟合平面
    # ======================
    def fit_plane_robust(self, points):
        """
        两次拟合：
            1. 第一次粗拟合；
            2. 剔除离平面太远的点；
            3. 第二次重新拟合。
        """
        normal, d = self.fit_plane_svd(points)

        if normal is None:
            return None, None, 0

        distances = np.abs(points @ normal + d)
        inliers = points[distances < self.plane_dist_thresh]

        if len(inliers) < self.min_points:
            return normal, d, len(points)

        normal2, d2 = self.fit_plane_svd(inliers)

        if normal2 is None:
            return normal, d, len(points)

        return normal2, d2, len(inliers)

    # ======================
    # 构建排除目标区域的 mask
    # ======================
    def build_target_exclude_mask(self, image_shape, contour=None, all_target_mask=None):
        """
        生成目标排除遮罩。

        重点：
            如果传入 all_target_mask，就排除整张图中所有彩色目标区域。
            这样两个图形靠得很近时，另一个图形不会被当成地面点。
        """
        h, w = image_shape[:2]

        if all_target_mask is not None:
            mask = all_target_mask.copy()

            if len(mask.shape) == 3:
                mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

            _, mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
        else:
            mask = np.zeros((h, w), dtype=np.uint8)

            if contour is not None:
                cv2.drawContours(mask, [contour], -1, 255, thickness=-1)

        if self.target_mask_expand > 0:
            kernel_size = self.target_mask_expand * 2 + 1
            kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)

        return mask

    # ======================
    # 在目标附近采样地面点
    # ======================
    def sample_local_ground_points(
        self,
        depth_frame,
        intrinsics,
        center_u,
        center_v,
        contour,
        all_target_mask=None,
        roi_expand=None
    ):
        """
        在目标附近采样地面点。

        改进：
            1. 采样区域是目标外接框扩大后的 ROI；
            2. 排除整张图中的所有目标区域；
            3. 如果两个目标太近，不会把另一个目标当成地面。
        """
        depth_image = np.asanyarray(depth_frame.get_data())
        depth_units = self.get_depth_units(depth_frame)

        h, w = depth_image.shape[:2]

        if roi_expand is None:
            roi_expand = self.roi_expand

        x, y, bw, bh = cv2.boundingRect(contour)

        x1 = max(0, x - roi_expand)
        y1 = max(0, y - roi_expand)
        x2 = min(w - 1, x + bw + roi_expand)
        y2 = min(h - 1, y + bh + roi_expand)

        exclude_mask = self.build_target_exclude_mask(
            image_shape=(h, w),
            contour=contour,
            all_target_mask=all_target_mask
        )

        points = []

        for v in range(y1, y2, self.sample_step):
            for u in range(x1, x2, self.sample_step):
                # 排除所有目标区域，不只是当前目标
                if exclude_mask[v, u] > 0:
                    continue

                depth = self.depth_at(depth_image, depth_units, u, v)

                if depth < self.depth_min or depth > self.depth_max:
                    continue

                point = self.deproject(intrinsics, u, v, depth)
                points.append(point)

        if len(points) < self.min_points:
            return None

        return np.array(points, dtype=np.float32)

    # ======================
    # 判断平面是否像地面
    # ======================
    def check_plane_reasonable(self, normal):
        angle = self.angle_between_vectors_deg(normal, self.camera_up)

        if angle > self.max_normal_angle_deg:
            self.log_debug(f"局部地面法向量角度过大: {angle:.1f} deg")
            return False

        return True

    # ======================
    # 目标中心射线和平面求交
    # ======================
    def intersect_center_ray_with_plane(self, intrinsics, center_u, center_v, normal, d):
        """
        平面：
            normal · P + d = 0

        射线：
            P = t * ray

        所以：
            t = -d / (normal · ray)
        """
        ray = self.deproject(intrinsics, center_u, center_v, 1.0)

        denom = float(np.dot(normal, ray))

        if abs(denom) < 1e-6:
            return None

        t = -d / denom

        if t <= 0:
            return None

        point = ray * t

        return point.astype(np.float32)

    # ======================
    # 建立局部地面坐标系
    # ======================
    def build_ground_axes(self, normal):
        """
        地面坐标系：
            ex：地面左右方向
            ey：地面法向方向
            ez：地面前方方向
        """
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
    # 相机坐标转局部地面坐标
    # ======================
    def point_to_ground_coord(self, point_cam, normal, d):
        ex, ey, ez = self.build_ground_axes(normal)

        if ex is None:
            return None

        # 相机原点在局部地面上的投影点
        ground_origin = -d * normal

        rel = point_cam - ground_origin

        x_ground = float(np.dot(rel, ex))
        y_ground = float(np.dot(rel, ey))
        z_ground = float(np.dot(rel, ez))

        return x_ground, y_ground, z_ground

    # ======================
    # 对单个目标估计坐标
    # ======================
    def estimate_target_coord(
        self,
        depth_frame,
        intrinsics,
        center_u,
        center_v,
        contour,
        all_target_mask=None
    ):
        """
        对单个目标估计坐标。

        逻辑：
            1. 在目标附近取地面点；
            2. 排除所有彩色目标区域；
            3. 如果点数不够，自动扩大 ROI；
            4. 拟合当前帧局部地面；
            5. 用目标中心射线和平面求交；
            6. 输出地面坐标。
        """
        try_roi_list = [
            self.roi_expand,
            int(self.roi_expand * 1.5),
            int(self.roi_expand * 2.0)
        ]

        points = None
        used_roi = None

        for roi in try_roi_list:
            points = self.sample_local_ground_points(
                depth_frame=depth_frame,
                intrinsics=intrinsics,
                center_u=center_u,
                center_v=center_v,
                contour=contour,
                all_target_mask=all_target_mask,
                roi_expand=roi
            )

            if points is not None and len(points) >= self.min_points:
                used_roi = roi
                break

        if points is None:
            self.log_debug("目标附近地面点不足，扩大 ROI 后仍然失败")
            return None

        normal, d, inliers = self.fit_plane_robust(points)

        if normal is None:
            self.log_debug("局部地面拟合失败")
            return None

        if not self.check_plane_reasonable(normal):
            return None

        point_cam = self.intersect_center_ray_with_plane(
            intrinsics=intrinsics,
            center_u=center_u,
            center_v=center_v,
            normal=normal,
            d=d
        )

        if point_cam is None:
            self.log_debug("目标中心射线和平面无有效交点")
            return None

        ground_coord = self.point_to_ground_coord(point_cam, normal, d)

        if ground_coord is None:
            return None

        x_ground, y_ground, z_ground = ground_coord

        return {
            "x": float(x_ground),
            "y": float(y_ground),
            "z": float(z_ground),
            "point_cam": point_cam,
            "normal": normal,
            "d": float(d),
            "inliers": int(inliers),
            "used_roi": int(used_roi)
        }