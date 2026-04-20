#!/usr/bin/env python3
import cv2
import rclpy
from rclpy.node import Node
from vision_interfaces.msg import Target, TargetArray
from vision_pkg.cv_tools import CvTools
from vision_pkg.vision_base import Vision
import pyrealsense2 as rs
import numpy as np


class VisionPubNode(Node):
    def __init__(self):
        super().__init__('vision_pub_node')

        self.tools = CvTools()
        self.vision = Vision()
        self.num = 0   # 序号计数器

        # ======================
        # RealSense 初始化
        # ======================
        self.pipeline = rs.pipeline() # 创建管道
        config = rs.config() # 配置流

        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30) # 颜色流，分辨率640x480，格式BGR8，帧率30fps
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)  # 深度流，分辨率640x480，格式Z16，帧率30fps

        self.pipeline.start(config) # 启动管道

        self.align = rs.align(rs.stream.color) # 创建对齐对象，目标流为颜色流

        self.get_logger().info("D435 started.")
        # ======================

        # 发布器
        self.publisher_ = self.create_publisher(
            TargetArray,
            'D435/vision',
            10
        )

        # 定时器
        self.timer = self.create_timer(0.1, self.timer_callback)

    # ======================
    # 平均深度（抗噪）
    # ======================
    def get_avg_depth(self, depth_frame, x, y, size=2):
        values = []

        width = depth_frame.get_width()
        height = depth_frame.get_height()

        for i in range(-size, size + 1):
            for j in range(-size, size + 1):
                xi = int(x + i)
                yj = int(y + j)

                # 完整边界检查
                if xi < 0 or xi >= width or yj < 0 or yj >= height:
                    continue

                d = depth_frame.get_distance(xi, yj)

                if d > 0:
                    values.append(d)

        if len(values) == 0:
            return None

        return float(np.mean(values))

    # ======================
    # 主循环
    # ======================
    def timer_callback(self):
        frames = self.pipeline.wait_for_frames() # 获取帧数据，阻塞式
        aligned_frames = self.align.process(frames) # 对齐深度和颜色帧

        color_frame = aligned_frames.get_color_frame() # 获取颜色帧
        depth_frame = aligned_frames.get_depth_frame() # 获取深度帧

        if not color_frame or not depth_frame:
            return

        frame = np.asanyarray(color_frame.get_data()) # 转换为NumPy数组

        targets, frame_copy, color_mask_test = self.target_detect(frame, depth_frame) # 目标检测，返回targets列表和标记后的图像副本

        # 创建TargetArray消息
        msg = TargetArray()
        msg.targets = []
        self.num = 0  # 每帧置零

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

        # 日志
        if targets:
            self.get_logger().info(f'Published {len(targets)} targets', throttle_duration_sec=0.5)

        cv2.imshow("vision", frame_copy)
        cv2.imshow("color_mask", color_mask_test) # 显示颜色掩膜
        cv2.waitKey(1)

    # ======================
    # 目标检测
    # ======================
    def target_detect(self, frame, depth_frame):
        targets = []
        frame_copy = frame.copy()

        # 相机内参（必须每帧获取）
        intrinsics = depth_frame.profile.as_video_stream_profile().intrinsics

        # 颜色检测
        color_list, color_mask = self.vision.color_detect(frame_copy)

        # 形状检测（必须用二值图）
        result = self.vision.shape_detect(color_mask)
        #  如果形状检测失败，shape_list置空，避免后续错误
        if len(result) == 2:
            shape_list, _ = result
        else:
            shape_list = []

        for color_name, contours in color_list:
            for color_contour in contours:

                color_center = self.tools.mark(color_contour, frame_copy, "", 0)

                for shape_name, shape_contour in shape_list:

                    frame_copy, shape_center = self.tools.mark(shape_contour, frame_copy, shape_name, 1)

                    # 匹配中心
                    if abs(shape_center[0] - color_center[0]) <= 5 and abs(shape_center[1] - color_center[1]) <= 5:

                        cx, cy = int(color_center[0]), int(color_center[1])

                        # 获取深度
                        depth = self.get_avg_depth(depth_frame, cx, cy)
                        # 没有深度 → 跳过
                        if depth is None or depth < 0.1 or depth > 5:
                            continue

                        # 3D坐标计算
                        point = rs.rs2_deproject_pixel_to_point(intrinsics,
                            [float(cx), float(cy)],
                            float(depth))
                        X, Y, Z = point

                        # 添加到targets
                        targets.append({
                            'x': float(X),
                            'y': float(Y),
                            'z': float(Z),
                            'depth': float(depth),
                            'color': color_name,
                            'shape': shape_name
                        })

                        # 显示信息
                        cv2.putText(frame_copy,f"{X:.2f}m, {Z:.2f}m",(cx, cy - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,0.6, (0, 255, 0), 2)

                        break

        return targets, frame_copy, color_mask


    # ======================
    # 关闭
    # ======================
    def destroy_node(self):
        self.pipeline.stop() # 停止管道
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