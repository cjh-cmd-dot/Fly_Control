#!/usr/bin/env python3
import cv2
import rclpy
from rclpy.node import Node
from vision_interfaces.msg import Target, TargetArray

# 请确保这些是你自己工作空间中的包，保持不变
from vision_pkg.cv_tools import CvTools
from vision_pkg.vision_base import Vision

import pyrealsense2 as rs
import numpy as np
import math


class VisionPubNode(Node):
    def __init__(self):
        super().__init__('vision_pub_node')

        self.tools = CvTools()
        self.vision = Vision()
        self.num = 0

        # ======================
        # 1. 地面拟合参数
        # ======================

        # 相机大致离地高度，用于判断拟合出来的平面像不像地面
        # 如果你的相机实际高度不是 1.0m，请改这里
        self.CAMERA_HEIGHT = 1.0
        self.HEIGHT_TOLERANCE = 0.25

        # 地面点采样步长，越小越准，但算力更大
        self.GROUND_SAMPLE_STEP = 30

        # 每隔多少帧更新一次地面模型
        self.GROUND_UPDATE_INTERVAL = 5

        # 拟合地面至少需要的点数
        self.GROUND_MIN_POINTS = 50

        # 平面内点距离阈值，单位 m
        self.GROUND_DIST_THRESH = 0.03

        # 目标点离地允许误差，单位 m
        self.GROUND_Y_THRESH = 0.08

        # 最大识别前方距离，单位 m
        self.MAX_GROUND_Z = 2.5

        # 地面模型 EMA 平滑系数
        # 越接近 1 越稳，但响应越慢
        self.GROUND_EMA_ALPHA = 0.90

        # RealSense 相机坐标系：
        # X 右，Y 下，Z 前
        # 所以相机上方方向约为 [0, -1, 0]
        self.CAMERA_UP = np.array([0.0, -1.0, 0.0], dtype=np.float32)

        # 拟合地面法向量与 CAMERA_UP 的最大允许夹角
        # 太大说明可能把墙/箱子拟合成地面
        self.MAX_NORMAL_ANGLE_DEG = 60.0

        # 新旧法向量最大允许突变角度
        self.MAX_NORMAL_JUMP_DEG = 15.0

        self.frame_count = 0

        # 地面模型参数
        self.ground_valid = False
        self.ground_normal = None
        self.ground_d = None
        self.ground_ex = None
        self.ground_ey = None
        self.ground_ez = None

        # ======================
        # 2. RealSense 初始化
        # ======================
        self.pipeline = rs.pipeline()
        config = rs.config()

        config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
        config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

        self.pipeline.start(config)

        # 深度图对齐到彩色图
        self.align = rs.align(rs.stream.color)

        # RealSense 官方滤波器
        self.rs_spatial = rs.spatial_filter()
        self.rs_temporal = rs.temporal_filter()

        self.get_logger().info("D435 启动：地面平面拟合 + EMA 平滑测距")

        # 发布器与定时器
        self.publisher_ = self.create_publisher(TargetArray, 'D435/vision', 10)
        self.timer = self.create_timer(0.1, self.timer_callback)

    # ======================
    # 中值深度获取
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
    # 采样地面点
    # ======================
    def sample_ground_points(self, depth_frame, intrinsics):
        points = []

        width = depth_frame.get_width()
        height = depth_frame.get_height()

        # 只从图像下半部分采样
        y_start = int(height * 0.55)
        y_end = int(height * 0.95)

        for v in range(y_start, y_end, self.GROUND_SAMPLE_STEP):
            for u in range(0, width, self.GROUND_SAMPLE_STEP):
                depth = depth_frame.get_distance(u, v)

                if depth < 0.2 or depth > 5.0:
                    continue

                point = rs.rs2_deproject_pixel_to_point(
                    intrinsics,
                    [float(u), float(v)],
                    float(depth)
                )

                points.append(point)

        if len(points) < self.GROUND_MIN_POINTS:
            return None

        return np.array(points, dtype=np.float32)

    # ======================
    # SVD 拟合平面
    # 平面方程：normal · p + d = 0
    # ======================
    def fit_plane_svd(self, points):
        if points is None or len(points) < self.GROUND_MIN_POINTS:
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
        inliers = points[distances < self.GROUND_DIST_THRESH]

        if len(inliers) < self.GROUND_MIN_POINTS:
            return normal, d

        normal2, d2 = self.fit_plane_svd(inliers)

        if normal2 is None:
            return normal, d

        return normal2, d2

    # ======================
    # 计算两个向量夹角
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
    # 判断拟合结果是否像地面
    # ======================
    def is_ground_model_reasonable(self, normal, d):
        if normal is None:
            return False

        # 1. 高度检查
        if abs(d - self.CAMERA_HEIGHT) > self.HEIGHT_TOLERANCE:
            self.get_logger().warn(
                f"拒绝地面更新：高度异常 d={d:.3f}m，期望约 {self.CAMERA_HEIGHT:.3f}m"
            )
            return False

        # 2. 法向量方向检查
        angle_to_up = self.angle_between_vectors_deg(normal, self.CAMERA_UP)

        if angle_to_up > self.MAX_NORMAL_ANGLE_DEG:
            self.get_logger().warn(
                f"拒绝地面更新：法向量不像地面，angle_to_up={angle_to_up:.1f}°"
            )
            return False

        # 3. 新旧模型突变检查
        if self.ground_valid and self.ground_normal is not None:
            angle_jump = self.angle_between_vectors_deg(normal, self.ground_normal)

            if angle_jump > self.MAX_NORMAL_JUMP_DEG:
                self.get_logger().warn(
                    f"拒绝地面更新：地面法向量突变 {angle_jump:.1f}°"
                )
                return False

        return True

    # ======================
    # EMA 平滑地面 normal 和 d
    # ======================
    def smooth_ground_model(self, new_normal, new_d):
        new_normal = np.array(new_normal, dtype=np.float32)
        new_normal = new_normal / np.linalg.norm(new_normal)

        # 第一次直接使用
        if not self.ground_valid or self.ground_normal is None:
            self.ground_normal = new_normal
            self.ground_d = float(new_d)
            return

        old_normal = self.ground_normal
        old_normal = old_normal / np.linalg.norm(old_normal)

        # 防止法向量方向相反
        if np.dot(old_normal, new_normal) < 0:
            new_normal = -new_normal
            new_d = -new_d

        alpha = self.GROUND_EMA_ALPHA

        smooth_normal = alpha * old_normal + (1.0 - alpha) * new_normal
        smooth_normal = smooth_normal / np.linalg.norm(smooth_normal)

        smooth_d = alpha * self.ground_d + (1.0 - alpha) * float(new_d)

        self.ground_normal = smooth_normal.astype(np.float32)
        self.ground_d = float(smooth_d)

    # ======================
    # 建立地面坐标系
    # ======================
    def build_ground_axes(self, normal):
        # ey：地面法向量，近似离地向上
        ey = normal / np.linalg.norm(normal)

        # 相机 Z 轴投影到地面，作为地面前方
        camera_z = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        ez = camera_z - np.dot(camera_z, ey) * ey
        ez_norm = np.linalg.norm(ez)

        if ez_norm < 1e-6:
            return None, None, None

        ez = ez / ez_norm

        if np.dot(ez, camera_z) < 0:
            ez = -ez

        # 地面右方
        ex = np.cross(ez, ey)
        ex_norm = np.linalg.norm(ex)

        if ex_norm < 1e-6:
            return None, None, None

        ex = ex / ex_norm

        return ex.astype(np.float32), ey.astype(np.float32), ez.astype(np.float32)

    # ======================
    # 更新地面模型
    # ======================
    def update_ground_model(self, depth_frame, intrinsics):
        self.frame_count += 1

        need_update = (
            not self.ground_valid or
            self.frame_count % self.GROUND_UPDATE_INTERVAL == 0
        )

        if not need_update:
            return self.ground_valid

        # 1. 采样点
        points = self.sample_ground_points(depth_frame, intrinsics)

        if points is None:
            self.get_logger().warn("地面点数量不足，沿用历史模型")
            return self.ground_valid

        # 2. 拟合平面
        normal, d = self.fit_ground_plane_robust(points)

        if normal is None:
            self.get_logger().warn("地面平面拟合失败，沿用历史模型")
            return self.ground_valid

        # 3. 安全检查
        if not self.is_ground_model_reasonable(normal, d):
            return self.ground_valid

        # 4. EMA 平滑
        self.smooth_ground_model(normal, d)

        # 5. 用平滑后的 normal 建立坐标系
        ex, ey, ez = self.build_ground_axes(self.ground_normal)

        if ex is None:
            self.get_logger().warn("地面坐标系建立失败，沿用历史模型")
            return self.ground_valid

        self.ground_ex = ex
        self.ground_ey = ey
        self.ground_ez = ez
        self.ground_valid = True

        angle_to_up = self.angle_between_vectors_deg(
            self.ground_normal,
            self.CAMERA_UP
        )

        self.get_logger().debug(
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

    # ======================
    # 主循环
    # ======================
    def timer_callback(self):
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.align.process(frames)

        color_frame = aligned_frames.get_color_frame()
        depth_frame = aligned_frames.get_depth_frame()

        if not color_frame or not depth_frame:
            return

        # 深度滤波
        depth_frame = self.rs_spatial.process(depth_frame)
        depth_frame = self.rs_temporal.process(depth_frame)
        depth_frame = depth_frame.as_depth_frame()

        if depth_frame is None:
            return

        frame = np.asanyarray(color_frame.get_data())

        targets, frame_copy, color_mask_test = self.target_detect(
            frame,
            depth_frame,
            color_frame
        )

        msg = TargetArray()
        msg.targets = []
        self.num = 0

        for target in targets:
            t = Target()
            t.x = target['x']
            t.y = target['y']
            t.z = target['z']
            t.number = float(self.num)
            t.depth = target['depth']
            t.color = target['color']
            t.shape = target['shape']
            msg.targets.append(t)
            self.num += 1

        self.publisher_.publish(msg)

        cv2.imshow("vision", frame_copy)
        cv2.imshow("color_mask", color_mask_test)
        cv2.waitKey(1)

    # ======================
    # 目标检测
    # 颜色、形状检测部分保持你的原逻辑
    # ======================
    def target_detect(self, frame, depth_frame, color_frame):
        targets = []
        frame_copy = frame.copy()

        # 深度图已对齐到彩色图，所以使用彩色相机内参
        color_intrinsics = color_frame.profile.as_video_stream_profile().intrinsics

        # 先更新地面模型
        ground_ok = self.update_ground_model(depth_frame, color_intrinsics)

        # 保持你的颜色检测逻辑
        color_list, color_mask = self.vision.color_detect(frame_copy)

        if not ground_ok:
            self.get_logger().warn("地面模型无效，当前帧不发布目标坐标")
            return targets, frame_copy, color_mask

        # 保持你的形状检测逻辑
        result = self.vision.shape_detect(color_mask)

        if len(result) == 2:
            shape_list, _ = result
        else:
            shape_list = []

        for color_name, contours in color_list:
            for color_contour in contours:
                color_center = self.tools.mark(color_contour, frame_copy, "", 0)

                for shape_name, shape_contour in shape_list:
                    frame_copy, shape_center = self.tools.mark(
                        shape_contour,
                        frame_copy,
                        shape_name,
                        1
                    )

                    if abs(shape_center[0] - color_center[0]) <= 5 and \
                       abs(shape_center[1] - color_center[1]) <= 5:

                        cx, cy = int(color_center[0]), int(color_center[1])

                        # 1. 获取目标中心深度
                        depth = self.get_median_depth(depth_frame, cx, cy)

                        if depth is None or depth < 0.1 or depth > 5.0:
                            continue

                        # 2. 像素反投影到相机坐标系
                        point = rs.rs2_deproject_pixel_to_point(
                            color_intrinsics,
                            [float(cx), float(cy)],
                            float(depth)
                        )

                        x_cam, y_cam, z_cam = point

                        # 3. 相机坐标转地面坐标
                        ground_coord = self.point_to_ground_coord(point)

                        if ground_coord is None:
                            continue

                        x_world, y_world, z_world = ground_coord

                        # 4. 地面图案理论上 y_world 应接近 0
                        if abs(y_world) > self.GROUND_Y_THRESH:
                            self.get_logger().debug(
                                f"目标点离地过大，丢弃: Y={y_world:.3f}m"
                            )
                            continue

                        # 5. 相机到目标中心点的实际空间直线距离
                        real_distance = math.sqrt(
                            x_cam ** 2 +
                            y_cam ** 2 +
                            z_cam ** 2
                        )

                        self.get_logger().info(
                            f"[地面坐标] X={x_world:.3f}m, "
                            f"Y={y_world:.3f}m, "
                            f"Z={z_world:.3f}m, "
                            f"depth={depth:.3f}m, "
                            f"distance={real_distance:.3f}m"
                        )

                        # 6. 前方距离过滤
                        if 0.0 < z_world <= self.MAX_GROUND_Z:
                            targets.append({
                                'x': float(x_world),
                                'y': float(y_world),
                                'z': float(z_world),
                                'depth': float(depth),
                                'color': color_name,
                                'shape': shape_name
                            })

                            cv2.putText(
                                frame_copy,
                                f"X:{x_world:.2f} Z:{z_world:.2f}m",
                                (cx - 20, cy - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 255, 0),
                                2
                            )

                            cv2.putText(
                                frame_copy,
                                f"D:{depth:.2f} L:{real_distance:.2f}m",
                                (cx - 20, cy + 15),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (255, 255, 0),
                                1
                            )

                        break

        return targets, frame_copy, color_mask

    def destroy_node(self):
        self.pipeline.stop()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VisionPubNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()