#!/usr/bin/env python3
import cv2
import rclpy
from rclpy.node import Node
from vision_interfaces.msg import Target, TargetArray

from vision_pkg.cv_tools import CvTools
from vision_pkg.vision_base import Vision
from vision_pkg.ground_plane_mapper import GroundPlaneMapper

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
        # 1. 当前帧局部地面拟合模块
        # ======================
        self.ground_mapper = GroundPlaneMapper(
            roi_expand=90,             # 目标附近取点范围，目标太近可调大到 120
            sample_step=6,             # 实时性优先：6；更快可改 8；更准可改 4
            min_points=18,             # 局部地面点最少数量，太近时可以改 15
            plane_dist_thresh=0.07,    # 地面不平整，阈值放宽
            depth_min=0.15,
            depth_max=5.0,
            target_mask_expand=18,     # 排除所有目标区域，防止相邻目标污染地面点
            max_normal_angle_deg=80.0,
            logger=self.get_logger()
        )

        # ======================
        # 2. RealSense 初始化
        # ======================
        self.pipeline = rs.pipeline()
        config = rs.config()

        # 建议先用 640x480，虚拟机和 USB 更稳定，实时性也更好
        config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
        config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

        self.pipeline.start(config)

        # 深度图对齐到彩色图
        self.align = rs.align(rs.stream.color)

        # 只保留当前帧空间滤波，不用 temporal，因为你要求只考虑当前帧
        self.rs_spatial = rs.spatial_filter()

        self.get_logger().info("D435 启动：当前帧局部地面拟合版，已排除所有相邻目标区域")

        # 发布器
        self.publisher_ = self.create_publisher(TargetArray, 'D435/vision', 10)

        # 30Hz 定时器
        self.timer = self.create_timer(0.033, self.timer_callback)

    # ======================
    # 主循环
    # ======================
    def timer_callback(self):
        # 不用 wait_for_frames，避免 D435 偶尔掉帧导致节点崩溃
        ok, frames = self.pipeline.try_wait_for_frames(1000)

        if not ok:
            self.get_logger().warn("D435 当前帧超时，跳过这一帧")
            return

        aligned_frames = self.align.process(frames)

        color_frame = aligned_frames.get_color_frame()
        depth_frame = aligned_frames.get_depth_frame()

        if not color_frame or not depth_frame:
            self.get_logger().warn("D435 没有获取到 color 或 depth frame")
            return

        # 当前帧空间滤波
        depth_frame = self.rs_spatial.process(depth_frame)
        depth_frame = depth_frame.as_depth_frame()

        if depth_frame is None:
            self.get_logger().warn("depth_frame 转换失败")
            return

        frame = np.asanyarray(color_frame.get_data())

        targets, frame_copy, color_mask_test = self.target_detect(
            frame=frame,
            depth_frame=depth_frame,
            color_frame=color_frame
        )

        msg = TargetArray()
        msg.targets = []
        self.num = 0

        for target in targets:
            t = Target()
            t.x = target['z']
            t.y = -target['x']
            t.z = target['y']
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
    # 计算轮廓中心
    # ======================
    def contour_center(self, contour):
        M = cv2.moments(contour)

        if abs(M["m00"]) < 1e-6:
            x, y, w, h = cv2.boundingRect(contour)
            return int(x + w / 2), int(y + h / 2)

        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        return cx, cy

    # ======================
    # 根据颜色中心匹配最近的形状
    # ======================
    def find_matched_shape(self, color_center, shape_list, max_center_error=12):
        """
        只根据颜色中心和形状中心匹配。
        """
        if color_center is None:
            return None

        cx, cy = color_center

        best_shape_name = None
        best_shape_contour = None
        best_shape_center = None
        best_dist = 1e9

        for shape_name, shape_contour in shape_list:
            sx, sy = self.contour_center(shape_contour)

            dist = math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2)

            if dist < best_dist:
                best_dist = dist
                best_shape_name = shape_name
                best_shape_contour = shape_contour
                best_shape_center = (sx, sy)

        if best_shape_name is None:
            return None

        if best_dist > max_center_error:
            return None

        return best_shape_name, best_shape_contour, best_shape_center

    # ======================
    # 目标检测
    # ======================
    def target_detect(self, frame, depth_frame, color_frame):
        targets = []
        frame_copy = frame.copy()

        # 深度图已经对齐到彩色图，所以使用彩色相机内参
        color_intrinsics = color_frame.profile.as_video_stream_profile().intrinsics

        # ======================
        # 1. 颜色检测：保持你原来的逻辑
        # ======================
        color_list, color_mask = self.vision.color_detect(frame_copy)

        # ======================
        # 2. 形状检测：保持你原来的逻辑
        # ======================
        result = self.vision.shape_detect(color_mask)

        if len(result) == 2:
            shape_list, _ = result
        else:
            shape_list = []

        # 没有目标时，不报错，直接返回空 targets
        if len(shape_list) == 0 or len(color_list) == 0:
            return targets, frame_copy, color_mask

        # ======================
        # 3. 遍历颜色轮廓
        # ======================
        for color_name, contours in color_list:
            for color_contour in contours:
                # 用你原来的 mark 做显示，同时拿颜色中心
                color_center = self.tools.mark(
                    color_contour,
                    frame_copy,
                    "",
                    0
                )

                if color_center is None:
                    continue

                cx, cy = int(color_center[0]), int(color_center[1])

                # ======================
                # 4. 匹配形状
                # ======================
                matched = self.find_matched_shape(
                    color_center=(cx, cy),
                    shape_list=shape_list,
                    max_center_error=12
                )

                if matched is None:
                    continue

                shape_name, shape_contour, shape_center = matched
                if shape_name == "irregular_polygon":
                    continue

                # 正式画出形状标记
                frame_copy, shape_center = self.tools.mark(
                    shape_contour,
                    frame_copy,
                    shape_name,
                    1
                )

                # ======================
                # 5. 当前帧局部地面拟合
                # ======================
                # 关键点：
                #     all_target_mask=color_mask
                #     这样采样地面点时会排除当前帧中所有彩色目标，
                #     不只是当前这个目标。
                coord = self.ground_mapper.estimate_target_coord(
                    depth_frame=depth_frame,
                    intrinsics=color_intrinsics,
                    center_u=cx,
                    center_v=cy,
                    contour=shape_contour,
                    all_target_mask=color_mask
                )

                if coord is None:
                    cv2.putText(
                        frame_copy,
                        "local plane fail",
                        (cx - 35, cy + 32),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (0, 0, 255),
                        1
                    )
                    continue

                x_world = coord["x"]
                y_world = coord["y"]
                z_world = coord["z"]

                point_cam = coord["point_cam"]
                x_cam, y_cam, z_cam = point_cam

                # corrected_depth 是目标中心射线和平面交点的相机 Z
                corrected_depth = float(z_cam)

                real_distance = math.sqrt(
                    x_cam ** 2 +
                    y_cam ** 2 +
                    z_cam ** 2
                )

                # 前方距离基本过滤
                if z_world <= 0.0 or z_world > 2.0:
                    continue

                targets.append({
                    'x': float(x_world),
                    'y': float(y_world),
                    'z': float(z_world),
                    'depth': float(corrected_depth),
                    'color': color_name,
                    'shape': shape_name
                })

                # ======================
                # 6. 显示检测结果
                # ======================
                cv2.putText(
                    frame_copy,
                    f"{color_name} {shape_name}",
                    (cx - 35, cy - 38),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 255),
                    2
                )

                cv2.putText(
                    frame_copy,
                    f"X:{x_world:.2f} Z:{z_world:.2f}m",
                    (cx - 35, cy - 14),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame_copy,
                    f"Y:{y_world:.2f} D:{real_distance:.2f}m",
                    (cx - 35, cy + 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 0),
                    1
                )

                cv2.putText(
                    frame_copy,
                    f"pts:{coord['inliers']} roi:{coord['used_roi']}",
                    (cx - 35, cy + 32),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42,
                    (255, 180, 0),
                    1
                )

                self.get_logger().info(
                    f"[{color_name} {shape_name}] "
                    f"X={x_world:.3f}, "
                    f"Y={y_world:.3f}, "
                    f"Z={z_world:.3f}, "
                    f"D={real_distance:.3f}, "
                    f"inliers={coord['inliers']}, "
                    f"roi={coord['used_roi']}"
                )

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