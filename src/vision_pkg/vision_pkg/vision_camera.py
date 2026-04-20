#!/usr/bin/env python3
import cv2
import rclpy
from rclpy.node import Node
from vision_interfaces.msg import Vision as VisionMsg
from vision_pkg.cv_tools import CvTools
from vision_pkg.vision_base import Vision

#   像素与实际距离的比例
imagw_object_ratio = 0.5

class VisionPubNode(Node):
    def __init__(self):

        num = 0   # 序号计数器
        super().__init__('vision_pub_node')

        self.tools = CvTools()
        self.vision = Vision()

        # 创建发布器（Point类型）
        self.publisher_ = self.create_publisher(
            VisionMsg,
            'Camera/vision',
            10
        )

        # 打开摄像头
        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            self.get_logger().error("Camera not opened!")
        else:
            self.get_logger().info("Camera started.")

        # 定时器（10Hz）
        self.timer = self.create_timer(0.1, self.timer_callback)

    #  主循环 
    def timer_callback(self):
        ret, frame = self.cap.read()
        frame = CvTools.set_roi(frame, 100, 100, 400, 300)  # 设置ROI区域
        if not ret:
            self.get_logger().warning("Failed to read frame")
            return

        targets, frame_copy = self.target_detect(frame)

        # 显示画面（可选）
        cv2.imshow("vision", frame_copy)
        cv2.waitKey(1)


    # ======================
    # 目标检测
    # ======================
    def target_detect(self, frame):
        targets = []
        frame_copy = frame.copy()

        # 颜色检测
        color_list, color_mask = self.vision.color_detect(frame_copy)

        # 形状检测（必须用二值图）
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
                        shape_contour, frame_copy, shape_name, 1)

                    # 匹配中心
                    if abs(shape_center[0] - color_center[0]) <= 5 and \
                       abs(shape_center[1] - color_center[1]) <= 5:

                        cx, cy = int(color_center[0]), int(color_center[1])

                        # 添加到targets
                        targets.append({
                            'cx': float(cx * imagw_object_ratio),  # 转换为实际距离
                            'cy': float(cy * imagw_object_ratio),  # 转换为实际距离
                            'color': color_name,
                            'shape': shape_name
                        })

                        # 显示信息
                        cv2.putText(frame_copy,f"{cx * imagw_object_ratio:.2f}m, {cy * imagw_object_ratio:.2f}m",(cx, cy - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,0.6, (0, 255, 0), 2)

                        break

        return targets, frame_copy


    # 关闭节点 
    def destroy_node(self):
        self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


#   主函数
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