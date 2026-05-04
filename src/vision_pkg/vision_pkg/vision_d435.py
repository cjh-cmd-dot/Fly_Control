#!/usr/bin/env python3
import cv2
import rclpy
from rclpy.node import Node
from vision_interfaces.msg import Target, TargetArray

from vision_pkg.cv_tools import CvTools
from vision_pkg.vision_base import Vision
from vision_pkg.ground_plane_mapper_d435 import GroundPlaneMapper

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
        # 1. 地面拟合模块
        # ======================
        self.ground_mapper = GroundPlaneMapper(
            camera_height=1.0,          # 相机镜头离地高度，按实际改
            height_tolerance=0.25,      # 高度容差
            sample_step=30,             # 地面采样步长
            update_interval=5,          # 每 5 帧更新一次地面模型
            min_points=50,              # 最少地面点数
            plane_dist_thresh=0.03,     # 平面内点距离阈值
            ground_y_thresh=0.08,       # 目标点离地允许误差
            max_ground_z=2.5,           # 最大前方识别距离
            ema_alpha=0.90,             # 地面模型平滑系数
            max_normal_angle_deg=60.0,  # 防止墙面误拟合
            max_normal_jump_deg=15.0,   # 防止地面模型突变
            roi_y_start=0.55,
            roi_y_end=0.95,
            logger=self.get_logger()
        )

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

        self.get_logger().info("D435 启动：地面拟合代码已拆分到 ground_plane_mapper.py")

        # 发布器与定时器
        self.publisher_ = self.create_publisher(TargetArray, 'D435/vision', 10)
        self.timer = self.create_timer(0.1, self.timer_callback)

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
    # 颜色、形状检测保持原逻辑
    # ======================
    def target_detect(self, frame, depth_frame, color_frame):
        targets = []
        frame_copy = frame.copy()

        # 深度图已对齐到彩色图，所以使用彩色相机内参
        color_intrinsics = color_frame.profile.as_video_stream_profile().intrinsics

        # 更新地面模型
        ground_ok = self.ground_mapper.update(depth_frame, color_intrinsics)

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
                        depth = self.ground_mapper.get_median_depth(
                            depth_frame,
                            cx,
                            cy,
                            size=2
                        )

                        if depth is None or depth < 0.1 or depth > 5.0:
                            continue

                        # 2. 像素反投影到相机坐标系
                        point = self.ground_mapper.deproject_pixel_to_point(
                            color_intrinsics,
                            cx,
                            cy,
                            depth
                        )

                        x_cam, y_cam, z_cam = point

                        # 3. 相机坐标转地面坐标
                        ground_coord = self.ground_mapper.point_to_ground_coord(point)

                        if ground_coord is None:
                            continue

                        x_world, y_world, z_world = ground_coord

                        # 4. 地面图案理论上 y_world 应接近 0
                        if not self.ground_mapper.is_target_on_ground(y_world):
                            self.get_logger().debug(
                                f"目标点离地过大，丢弃: Y={y_world:.3f}m"
                            )
                            continue

                        # 5. 相机到目标中心点的真实空间直线距离
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
                        if self.ground_mapper.is_target_in_range(z_world):
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