#!/usr/bin/env python3
import math
import numpy as np
import pyrealsense2 as rs


class GroundPlaneMapper:
    """
    GroundPlaneMapper 使用说明
    ==========================

    这个类专门负责 D435 的地面平面拟合和坐标转换。

    它解决的问题：
        当 D435 摄像头倾斜向下看地面时，不需要提前知道相机俯仰角。
        程序会从深度图中采样一批地面点，拟合出地面平面，
        然后把目标中心点转换成地面坐标系下的 X、Y、Z。

    一、输入数据
    ----------
    需要输入：
        1. depth_frame
            D435 对齐到彩色图后的深度帧。

        2. intrinsics
            彩色相机内参。
            因为你的代码使用 rs.align(rs.stream.color)，
            深度图已经对齐到彩色图，所以反投影时要用 color_intrinsics。

        3. 目标中心点像素坐标 cx, cy
            由你的颜色检测和形状检测得到。

    二、典型使用流程
    ---------------
    在 node 初始化中创建对象：

        self.ground_mapper = GroundPlaneMapper(
            camera_height=1.0,
            height_tolerance=0.25,
            sample_step=30,
            update_interval=5
        )

    在每帧 target_detect() 中先更新地面模型：

        ground_ok = self.ground_mapper.update(depth_frame, color_intrinsics)

    对目标中心点获取深度：

        depth = self.ground_mapper.get_median_depth(depth_frame, cx, cy)

    反投影到相机坐标：

        point = self.ground_mapper.deproject_pixel_to_point(
            color_intrinsics,
            cx,
            cy,
            depth
        )

    转成地面坐标：

        ground_coord = self.ground_mapper.point_to_ground_coord(point)

    三、输出坐标含义
    ---------------
    point_to_ground_coord(point) 返回：

        x_ground:
            目标点在地面坐标系中的左右距离。
            一般右侧为正，单位 m。

        y_ground:
            目标点离地高度。
            因为你检测的是地面图案，所以理论上应该接近 0。

        z_ground:
            目标点在地面坐标系中的前方距离。
            这个才是适合给机器人使用的前方距离。

    注意：
        depth 不是地面前方距离。
        depth 是 D435 相机 Z 轴方向深度。
        z_ground 才是转换后的地面前方距离。

    四、安全机制
    ------------
    这个类加入了三个保护：

        1. 高度检查
            如果拟合出的地面离相机距离和 camera_height 差太多，就拒绝更新。

        2. 法向量方向检查
            防止把墙面、纸箱正面误拟合成地面。

        3. EMA 平滑
            防止每隔几帧更新地面模型时，X/Z 坐标出现轻微跳变。

    五、常调参数
    ------------
    camera_height:
        相机镜头离地高度，单位 m。
        例如相机离地 1 米，就写 1.0。

    height_tolerance:
        高度容差。
        例如 0.25 表示允许拟合高度在 camera_height ± 0.25m 内。

    sample_step:
        地面采样步长。
        30 比较均衡。
        数值越小越准，但算力越大。

    update_interval:
        每隔多少帧更新一次地面平面。
        5 表示每 5 帧更新一次。

    ema_alpha:
        EMA 平滑系数。
        0.90 比较稳。
        越接近 1 越平滑，但响应越慢。

    ground_y_thresh:
        判断目标点是否在地面附近的阈值。
        例如 0.08 表示允许目标点离地 ±8cm。
    """

    def __init__(
        self,
        camera_height=1.0,
        height_tolerance=0.25,
        sample_step=30,
        update_interval=5,
        min_points=50,
        plane_dist_thresh=0.03,
        ground_y_thresh=0.08,
        max_ground_z=2.5,
        ema_alpha=0.90,
        max_normal_angle_deg=60.0,
        max_normal_jump_deg=15.0,
        roi_y_start=0.55,
        roi_y_end=0.95,
        logger=None
    ):
        self.camera_height = camera_height
        self.height_tolerance = height_tolerance

        self.sample_step = sample_step
        self.update_interval = update_interval
        self.min_points = min_points
        self.plane_dist_thresh = plane_dist_thresh

        self.ground_y_thresh = ground_y_thresh
        self.max_ground_z = max_ground_z

        self.ema_alpha = ema_alpha
        self.max_normal_angle_deg = max_normal_angle_deg
        self.max_normal_jump_deg = max_normal_jump_deg

        self.roi_y_start = roi_y_start
        self.roi_y_end = roi_y_end

        self.logger = logger

        # RealSense 相机坐标系：X 右，Y 下，Z 前
        # 所以相机上方方向约为 [0, -1, 0]
        self.camera_up = np.array([0.0, -1.0, 0.0], dtype=np.float32)

        self.frame_count = 0

        self.ground_valid = False
        self.ground_normal = None
        self.ground_d = None

        self.ground_ex = None
        self.ground_ey = None
        self.ground_ez = None

    def log_warn(self, text):
        if self.logger is not None:
            self.logger.warn(text)

    def log_debug(self, text):
        if self.logger is not None:
            self.logger.debug(text)

    # ======================
    # 中值深度
    # ======================
    def get_median_depth(self, depth_frame, x, y, size=2):
        values = []

        width = depth_frame.get_width()
        height = depth_frame.get_height()

        for i in range(-size, size + 1):
            for j in range(-size, size + 1):
                xi = int(x + i)
                yj = int(y + j)

                if xi < 0 or xi >= width or yj < 0 or yj >= height:
                    continue

                d = depth_frame.get_distance(xi, yj)

                if 0.1 <= d <= 5.0:
                    values.append(d)

        if len(values) == 0:
            return None

        return float(np.median(values))

    # ======================
    # 像素反投影
    # ======================
    def deproject_pixel_to_point(self, intrinsics, x, y, depth):
        point = rs.rs2_deproject_pixel_to_point(
            intrinsics,
            [float(x), float(y)],
            float(depth)
        )

        return np.array(point, dtype=np.float32)

    # ======================
    # 采样地面点
    # ======================
    def sample_ground_points(self, depth_frame, intrinsics):
        points = []

        width = depth_frame.get_width()
        height = depth_frame.get_height()

        y_start = int(height * self.roi_y_start)
        y_end = int(height * self.roi_y_end)

        for v in range(y_start, y_end, self.sample_step):
            for u in range(0, width, self.sample_step):
                depth = depth_frame.get_distance(u, v)

                if depth < 0.2 or depth > 5.0:
                    continue

                point = rs.rs2_deproject_pixel_to_point(
                    intrinsics,
                    [float(u), float(v)],
                    float(depth)
                )

                points.append(point)

        if len(points) < self.min_points:
            return None

        return np.array(points, dtype=np.float32)

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
        d = -np.dot(normal, centroid)

        # 保证法向量朝向相机这一侧
        if d < 0:
            normal = -normal
            d = -d

        return normal.astype(np.float32), float(d)

    # ======================
    # 剔除离群点后重新拟合
    # ======================
    def fit_ground_plane_robust(self, points):
        normal, d = self.fit_plane_svd(points)

        if normal is None:
            return None, None

        distances = np.abs(points @ normal + d)
        inliers = points[distances < self.plane_dist_thresh]

        if len(inliers) < self.min_points:
            return normal, d

        normal2, d2 = self.fit_plane_svd(inliers)

        if normal2 is None:
            return normal, d

        return normal2, d2

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
    # 判断是否像地面
    # ======================
    def is_ground_model_reasonable(self, normal, d):
        if normal is None:
            return False

        # 1. 高度检查
        if abs(d - self.camera_height) > self.height_tolerance:
            self.log_warn(
                f"拒绝地面更新：高度异常 d={d:.3f}m，期望约 {self.camera_height:.3f}m"
            )
            return False

        # 2. 法向量方向检查
        angle_to_up = self.angle_between_vectors_deg(normal, self.camera_up)

        if angle_to_up > self.max_normal_angle_deg:
            self.log_warn(
                f"拒绝地面更新：法向量不像地面，angle_to_up={angle_to_up:.1f}°"
            )
            return False

        # 3. 新旧模型突变检查
        if self.ground_valid and self.ground_normal is not None:
            angle_jump = self.angle_between_vectors_deg(normal, self.ground_normal)

            if angle_jump > self.max_normal_jump_deg:
                self.log_warn(
                    f"拒绝地面更新：地面法向量突变 {angle_jump:.1f}°"
                )
                return False

        return True

    # ======================
    # EMA 平滑
    # ======================
    def smooth_ground_model(self, new_normal, new_d):
        new_normal = np.array(new_normal, dtype=np.float32)
        new_normal = new_normal / np.linalg.norm(new_normal)

        if not self.ground_valid or self.ground_normal is None:
            self.ground_normal = new_normal
            self.ground_d = float(new_d)
            return

        old_normal = self.ground_normal
        old_normal = old_normal / np.linalg.norm(old_normal)

        if np.dot(old_normal, new_normal) < 0:
            new_normal = -new_normal
            new_d = -new_d

        alpha = self.ema_alpha

        smooth_normal = alpha * old_normal + (1.0 - alpha) * new_normal
        smooth_normal = smooth_normal / np.linalg.norm(smooth_normal)

        smooth_d = alpha * self.ground_d + (1.0 - alpha) * float(new_d)

        self.ground_normal = smooth_normal.astype(np.float32)
        self.ground_d = float(smooth_d)

    # ======================
    # 建立地面坐标系
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
    # 更新地面模型
    # ======================
    def update(self, depth_frame, intrinsics):
        self.frame_count += 1

        need_update = (
            not self.ground_valid or
            self.frame_count % self.update_interval == 0
        )

        if not need_update:
            return self.ground_valid

        points = self.sample_ground_points(depth_frame, intrinsics)

        if points is None:
            self.log_warn("地面点数量不足，沿用历史模型")
            return self.ground_valid

        normal, d = self.fit_ground_plane_robust(points)

        if normal is None:
            self.log_warn("地面平面拟合失败，沿用历史模型")
            return self.ground_valid

        if not self.is_ground_model_reasonable(normal, d):
            return self.ground_valid

        self.smooth_ground_model(normal, d)

        ex, ey, ez = self.build_ground_axes(self.ground_normal)

        if ex is None:
            self.log_warn("地面坐标系建立失败，沿用历史模型")
            return self.ground_valid

        self.ground_ex = ex
        self.ground_ey = ey
        self.ground_ez = ez
        self.ground_valid = True

        angle_to_up = self.angle_between_vectors_deg(
            self.ground_normal,
            self.camera_up
        )

        self.log_debug(
            f"地面模型更新成功：height={self.ground_d:.3f}m, "
            f"angle_to_up={angle_to_up:.1f}°"
        )

        return True

    # ======================
    # 相机坐标转地面坐标
    # ======================
    def point_to_ground_coord(self, point_cam):
        if not self.ground_valid:
            return None

        p = np.array(point_cam, dtype=np.float32)

        # 相机原点在地面上的投影点
        ground_origin = -self.ground_d * self.ground_normal

        rel = p - ground_origin

        x_ground = float(np.dot(rel, self.ground_ex))
        y_ground = float(np.dot(rel, self.ground_ey))
        z_ground = float(np.dot(rel, self.ground_ez))

        return x_ground, y_ground, z_ground

    def is_target_on_ground(self, y_ground):
        return abs(y_ground) <= self.ground_y_thresh

    def is_target_in_range(self, z_ground):
        return 0.0 < z_ground <= self.max_ground_z