#!/usr/bin/env python3
import cv2
import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool
from vision_interfaces.msg import Target, TargetArray

from vision_pkg.cv_tools import CvTools
from vision_pkg.vision_base import Vision
from vision_pkg.local_ground_mapper_d435 import LocalGroundMapper

import pyrealsense2 as rs
import numpy as np


class VisionPubNode(Node):
    def __init__(self):
        super().__init__('vision_pub_node')

        self.tools = CvTools()
        self.vision = Vision()
        self.num = 0

        # ======================
        # /takeoff_finish 标志位
        # ======================
        self.takeoff_finish = False

        self.takeoff_finish_sub = self.create_subscription(
            Bool,
            '/takeoff_finished',
            self.takeoff_finish_callback,
            10
        )

        # ======================
        # 地面锁定相关变量
        # 不改 local_ground_mapper_d435.py，
        # 所以这些变量放在主节点里维护
        # ======================
        self.ground_fit_target_count = 10

        self.ground_fit_normals = []
        self.ground_fit_ds = []
        self.ground_fit_rms_list = []

        self.ground_locked = False
        self.locked_normal = None
        self.locked_d = None
        self.locked_rms = 0.0

        # ======================
        # 局部地面拟合模块
        # local_ground_mapper_d435.py 不需要改
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
            "D435 启动：/takeoff_finish=True 后拟合地面10次，然后锁定平面"
        )

    # ======================
    # /takeoff_finish 回调
    # ======================
    def takeoff_finish_callback(self, msg: Bool):
        self.takeoff_finish = bool(msg.data)

        if self.takeoff_finish:
            if self.ground_locked:
                self.get_logger().info(
                    "收到 /takeoff_finish=True，但地面已锁定，不再拟合"
                )
            else:
                self.get_logger().info(
                    f"收到 /takeoff_finish=True，允许地面拟合: "
                    f"{len(self.ground_fit_normals)}/{self.ground_fit_target_count}"
                )
        else:
            self.get_logger().info(
                "收到 /takeoff_finish=False，未锁定前不会进行地面拟合"
            )

    # ======================
    # 保存一次拟合结果，并判断是否锁定
    # ======================
    def add_ground_plane_sample_and_maybe_lock(self, plane_result):
        normal = plane_result["normal"].astype(np.float32)
        d = float(plane_result["d"])
        rms = float(plane_result["rms"])

        # 保证 normal 方向一致，避免平均时抵消
        if len(self.ground_fit_normals) > 0:
            ref_normal = self.ground_fit_normals[0]
            if float(np.dot(normal, ref_normal)) < 0.0:
                normal = -normal
                d = -d

        self.ground_fit_normals.append(normal)
        self.ground_fit_ds.append(d)
        self.ground_fit_rms_list.append(rms)

        fit_count = len(self.ground_fit_normals)

        self.get_logger().info(
            f"地面拟合成功 {fit_count}/{self.ground_fit_target_count}, "
            f"rms={rms:.4f}, d={d:.4f}"
        )

        if fit_count < self.ground_fit_target_count:
            return

        normals = np.array(self.ground_fit_normals, dtype=np.float32)
        ds = np.array(self.ground_fit_ds, dtype=np.float32)

        avg_normal = np.mean(normals, axis=0)
        norm = np.linalg.norm(avg_normal)

        if norm < 1e-6:
            self.get_logger().warn("地面锁定失败：平均法向量异常")
            return

        avg_normal = avg_normal / norm
        avg_d = float(np.mean(ds))

        # 和 LocalGroundMapper 保持一致：
        # RealSense 相机坐标中，Y 向下，所以相机上方是 [0, -1, 0]
        camera_up = np.array([0.0, -1.0, 0.0], dtype=np.float32)

        if float(np.dot(avg_normal, camera_up)) < 0.0:
            avg_normal = -avg_normal
            avg_d = -avg_d

        if avg_d < 0.0:
            avg_normal = -avg_normal
            avg_d = -avg_d

        self.locked_normal = avg_normal.astype(np.float32)
        self.locked_d = float(avg_d)
        self.locked_rms = float(np.mean(self.ground_fit_rms_list))
        self.ground_locked = True

        # 同步更新 mapper 的上一帧可信平面，避免内部质量检查状态不一致
        self.local_ground_mapper.last_valid_normal = self.locked_normal
        self.local_ground_mapper.last_valid_d = self.locked_d

        self.get_logger().info(
            f"地面平面已锁定：normal=("
            f"{self.locked_normal[0]:.4f}, "
            f"{self.locked_normal[1]:.4f}, "
            f"{self.locked_normal[2]:.4f}), "
            f"d={self.locked_d:.4f}, "
            f"avg_rms={self.locked_rms:.4f}"
        )

    # ======================
    # 用指定平面计算目标坐标
    # ======================
    def estimate_coord_with_plane(
        self,
        intrinsics,
        cx,
        cy,
        normal,
        d,
        plane_rms,
        inlier_ratio,
        inlier_count,
        total_count,
        ring_mask,
        mode
    ):
        point_on_ground = self.local_ground_mapper.intersect_pixel_ray_with_plane(
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

        ground_coord = self.local_ground_mapper.point_to_local_ground_coord(
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

        if not (0.0 < z_ground <= self.local_ground_mapper.max_ground_z):
            return False, {
                "reason": f"z_ground out of range: {z_ground:.3f}",
                "ring_mask": ring_mask
            }

        return True, {
            "x": float(x_ground),
            "y": float(y_ground),
            "z": float(z_ground),

            "plane_rms": float(plane_rms),
            "inlier_ratio": float(inlier_ratio),
            "inlier_count": int(inlier_count),
            "total_count": int(total_count),

            "ring_mask": ring_mask,

            "mode": mode,
            "fit_count": int(len(self.ground_fit_normals)),
            "ground_locked": bool(self.ground_locked)
        }

    # ======================
    # 坐标计算主逻辑
    # 不改 detection，只替换原来 estimate_target_ground_coord 的调用方式
    # ======================
    def estimate_target_coord_by_locked_ground(
        self,
        depth_frame,
        intrinsics,
        image_shape,
        contour,
        cx,
        cy
    ):
        # ======================
        # 情况1：地面已经锁定
        # 后续不再地面拟合，所有目标用固定平面计算
        # ======================
        if self.ground_locked:
            return self.estimate_coord_with_plane(
                intrinsics=intrinsics,
                cx=cx,
                cy=cy,
                normal=self.locked_normal,
                d=self.locked_d,
                plane_rms=self.locked_rms,
                inlier_ratio=1.0,
                inlier_count=0,
                total_count=0,
                ring_mask=None,
                mode="LOCKED_PLANE"
            )

        # ======================
        # 情况2：还没锁定，并且飞控没发 True
        # 不进行拟合，不发布坐标
        # ======================
        if not self.takeoff_finish:
            return False, {
                "reason": "ground plane not locked and /takeoff_finish is False",
                "ring_mask": None
            }

        # ======================
        # 情况3：还没锁定，但 /takeoff_finish=True
        # 开始进行地面拟合
        # ======================
        points, ring_mask = self.local_ground_mapper.sample_local_ground_points(
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

        plane_result = self.local_ground_mapper.fit_plane_ransac(points)

        ok, reason = self.local_ground_mapper.check_plane_quality(plane_result)

        if not ok:
            return False, {
                "reason": reason,
                "ring_mask": ring_mask
            }

        normal = plane_result["normal"]
        d = plane_result["d"]

        # 更新 mapper 内部上一帧可信平面
        self.local_ground_mapper.last_valid_normal = normal
        self.local_ground_mapper.last_valid_d = d

        # 保存一次成功拟合，达到10次后锁定
        self.add_ground_plane_sample_and_maybe_lock(plane_result)

        # 如果刚刚第10次拟合后完成锁定，则当前目标也用锁定平面计算
        if self.ground_locked:
            return self.estimate_coord_with_plane(
                intrinsics=intrinsics,
                cx=cx,
                cy=cy,
                normal=self.locked_normal,
                d=self.locked_d,
                plane_rms=self.locked_rms,
                inlier_ratio=float(plane_result["inlier_ratio"]),
                inlier_count=int(plane_result["inlier_count"]),
                total_count=int(plane_result["total_count"]),
                ring_mask=ring_mask,
                mode="LOCKED_PLANE"
            )

        # 还没满10次时，当前目标先用当前拟合平面计算
        return self.estimate_coord_with_plane(
            intrinsics=intrinsics,
            cx=cx,
            cy=cy,
            normal=normal,
            d=d,
            plane_rms=float(plane_result["rms"]),
            inlier_ratio=float(plane_result["inlier_ratio"]),
            inlier_count=int(plane_result["inlier_count"]),
            total_count=int(plane_result["total_count"]),
            ring_mask=ring_mask,
            mode="FITTING_PLANE"
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

                # depth 字段这里继续用作调试：
                # 未锁定时：当前拟合 RMS
                # 锁定后：锁定平面平均 RMS
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
    # 检测逻辑保持不变
    # 只把坐标计算函数换成 estimate_target_coord_by_locked_ground()
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
                    # 4. 地面锁定坐标计算
                    # ======================
                    success, result = self.estimate_target_coord_by_locked_ground(
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

                    mode = result.get("mode", "unknown")
                    fit_count = result.get("fit_count", 0)
                    locked = result.get("ground_locked", False)

                    # y_ground 理论上接近 0
                    # 如果太大，说明目标像素射线和地面交点不可信
                    if abs(y_ground) > 0.05:
                        self.get_logger().warn(
                            f"目标离拟合/锁定地面过大，拒绝: y={y_ground:.3f}"
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
                        f"[地面坐标/{mode}] "
                        f"{color_name}-{shape_name}: "
                        f"X={x_ground:.3f}, "
                        f"Y={y_ground:.3f}, "
                        f"Z={z_ground:.3f}, "
                        f"rms={plane_rms:.3f}, "
                        f"inlier={inlier_count}/{total_count}, "
                        f"ratio={inlier_ratio:.2f}, "
                        f"fit={fit_count}/{self.ground_fit_target_count}, "
                        f"locked={locked}"
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
                        f"{mode} {fit_count}/{self.ground_fit_target_count}",
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