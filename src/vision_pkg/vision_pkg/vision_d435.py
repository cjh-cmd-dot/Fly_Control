#!/usr/bin/env python3
import cv2
import rclpy
from rclpy.node import Node

from vision_interfaces.msg import Target, TargetArray

from vision_pkg.cv_tools import CvTools
from vision_pkg.vision_base import Vision
from vision_pkg.local_ground_mapper_d435 import LocalGroundMapper

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
        # 局部地面拟合模块
        # ======================
        self.local_ground_mapper = LocalGroundMapper(
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

            # 注意：
            # 这两个不是用来慢平滑，而是拒绝明显错误帧
            max_normal_jump_deg=35.0,
            max_d_jump=0.20,

            max_ground_z=3.0,
            logger=self.get_logger()
        )

        # ======================
        # RealSense 初始化
        # ======================
        self.pipeline = rs.pipeline()
        config = rs.config()

        config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
        config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

        self.pipeline.start(config)

        self.align = rs.align(rs.stream.color)

        # RealSense 深度滤波
        self.rs_spatial = rs.spatial_filter()
        self.rs_temporal = rs.temporal_filter()
        self.rs_hole_filling = rs.hole_filling_filter()

        try:
            self.rs_spatial.set_option(rs.option.filter_magnitude, 2)
            self.rs_spatial.set_option(rs.option.filter_smooth_alpha, 0.5)
            self.rs_spatial.set_option(rs.option.filter_smooth_delta, 20)
        except Exception:
            pass

        try:
            self.rs_temporal.set_option(rs.option.filter_smooth_alpha, 0.35)
            self.rs_temporal.set_option(rs.option.filter_smooth_delta, 20)
        except Exception:
            pass

        self.publisher_ = self.create_publisher(
            TargetArray,
            'D435/vision',
            10
        )

        # 10Hz
        self.timer = self.create_timer(0.1, self.timer_callback)

        self.get_logger().info(
            "D435 启动：局部地面拟合 + 像素射线求交模式"
        )

    # ======================
    # 主循环
    # ======================
    def timer_callback(self):
        try:
            frames = self.pipeline.wait_for_frames()
            aligned_frames = self.align.process(frames)

            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()

            if not color_frame or not depth_frame:
                return

            # 深度滤波
            depth_frame = self.rs_spatial.process(depth_frame)
            depth_frame = self.rs_temporal.process(depth_frame)
            depth_frame = self.rs_hole_filling.process(depth_frame)
            depth_frame = depth_frame.as_depth_frame()

            if depth_frame is None:
                return

            frame = np.asanyarray(color_frame.get_data())

            targets, frame_copy, debug_mask = self.target_detect(
                frame,
                depth_frame,
                color_frame
            )

            msg = TargetArray()
            msg.targets = []
            self.num = 0

            for target in targets:
                t = Target()

                t.x = float(target['x'])
                t.y = float(target['y'])
                t.z = float(target['z'])
                t.number = float(self.num)

                # 这里 depth 不再代表目标中心深度
                # 而是保留为局部地面拟合 RMS，方便你调试
                t.depth = float(target['depth'])

                t.color = target['color']
                t.shape = target['shape']

                msg.targets.append(t)
                self.num += 1

            self.publisher_.publish(msg)

            cv2.imshow("vision", frame_copy)

            if debug_mask is not None:
                cv2.imshow("local_ground_ring_mask", debug_mask)

            cv2.waitKey(1)

        except Exception as e:
            self.get_logger().error(f"timer_callback 出错: {e}")

    # ======================
    # 目标检测
    # ======================
    def target_detect(self, frame, depth_frame, color_frame):
        targets = []
        frame_copy = frame.copy()

        debug_ring_mask = None

        color_intrinsics = color_frame.profile.as_video_stream_profile().intrinsics

        # ======================
        # 1. 颜色检测
        # ======================
        color_list, color_mask = self.vision.color_detect(frame_copy)

        # ======================
        # 2. 形状检测
        # ======================
        result = self.vision.shape_detect(color_mask)

        if len(result) == 2:
            shape_list, processed_mask = result
        else:
            shape_list = []
            processed_mask = color_mask

        # ======================
        # 3. 颜色轮廓和形状轮廓匹配
        # ======================
        for color_name, color_contours in color_list:
            for color_contour in color_contours:
                color_area = cv2.contourArea(color_contour)

                if color_area < 300:
                    continue

                color_center = self.tools.mark(
                    color_contour,
                    frame_copy,
                    "",
                    0
                )

                if color_center is None:
                    continue

                cx_color, cy_color = int(color_center[0]), int(color_center[1])

                for shape_name, shape_contour in shape_list:
                    shape_area = cv2.contourArea(shape_contour)

                    if shape_area < 300:
                        continue

                    frame_copy, shape_center = self.tools.mark(
                        shape_contour,
                        frame_copy,
                        shape_name,
                        1
                    )

                    if shape_center is None:
                        continue

                    cx_shape, cy_shape = int(shape_center[0]), int(shape_center[1])

                    # 颜色中心和形状中心足够接近，认为是同一个目标
                    if abs(cx_shape - cx_color) > 8 or abs(cy_shape - cy_color) > 8:
                        continue

                    cx = cx_color
                    cy = cy_color

                    # ======================
                    # 4. 局部地面拟合 + 像素射线求交
                    # ======================
                    success, result = self.local_ground_mapper.estimate_target_ground_coord(
                        depth_frame=depth_frame,
                        intrinsics=color_intrinsics,
                        image_shape=frame.shape,
                        contour=color_contour,
                        cx=cx,
                        cy=cy
                    )

                    if "ring_mask" in result and result["ring_mask"] is not None:
                        debug_ring_mask = result["ring_mask"]

                    if not success:
                        self.get_logger().warn(
                            f"目标 {color_name}-{shape_name} 本帧拒绝发布: "
                            f"{result.get('reason', 'unknown')}"
                        )

                        cv2.putText(
                            frame_copy,
                            "REJECT",
                            (cx - 30, cy - 20),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 0, 255),
                            2
                        )

                        continue

                    x_ground = result["x"]
                    y_ground = result["y"]
                    z_ground = result["z"]

                    plane_rms = result["plane_rms"]
                    inlier_ratio = result["inlier_ratio"]
                    inlier_count = result["inlier_count"]
                    total_count = result["total_count"]

                    # 这里 y_ground 理论上接近 0
                    # 如果太大，说明目标像素射线和局部地面交点不可信
                    if abs(y_ground) > 0.05:
                        self.get_logger().warn(
                            f"目标离局部地面过大，拒绝: y={y_ground:.3f}"
                        )
                        continue

                    targets.append({
                        'x': float(x_ground),
                        'y': float(y_ground),
                        'z': float(z_ground),

                        # depth 字段这里暂存 plane_rms，方便调试
                        'depth': float(plane_rms),

                        'color': color_name,
                        'shape': shape_name
                    })

                    self.get_logger().info(
                        f"[局部地面坐标] "
                        f"{color_name}-{shape_name}: "
                        f"X={x_ground:.3f}, "
                        f"Y={y_ground:.3f}, "
                        f"Z={z_ground:.3f}, "
                        f"rms={plane_rms:.3f}, "
                        f"inlier={inlier_count}/{total_count}, "
                        f"ratio={inlier_ratio:.2f}"
                    )

                    cv2.putText(
                        frame_copy,
                        f"{color_name} {shape_name}",
                        (cx - 40, cy - 45),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame_copy,
                        f"X:{x_ground:.2f} Z:{z_ground:.2f}",
                        (cx - 40, cy - 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame_copy,
                        f"rms:{plane_rms:.3f} in:{inlier_ratio:.2f}",
                        (cx - 40, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (255, 255, 0),
                        1
                    )

                    # 一个颜色轮廓匹配到一个形状后就跳出
                    break

        return targets, frame_copy, debug_ring_mask

    # ======================
    # 节点销毁
    # ======================
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