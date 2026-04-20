import os
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    """
    启动 vision_pkg 包下的两个节点：vision_camera 和 vision_d435
    """
    
    # 1. 定义 vision_camera 节点
    # 对应 setup.py 中的 'vision_camera = vision_pkg.vision_camera:main'
    camera_node = Node(
        package='vision_pkg',
        executable='vision_camera',
        name='vision_camera_node',
        output='screen',
        parameters=[{'use_sim_time': False}], # 示例参数，可删
        arguments=['--ros-args', '--log-level', 'info'] # 示例日志级别
    )

    # 2. 定义 vision_d435 节点
    # 对应 setup.py 中的 'vision_d435 = vision_pkg.vision_d435:main'
    d435_node = Node(
        package='vision_pkg',
        executable='vision_d435',
        name='vision_d435_node',
        output='screen'
    )

    # 3. 创建 LaunchDescription 对象并放入节点
    ld = LaunchDescription()
    ld.add_action(camera_node)
    ld.add_action(d435_node)

    return ld