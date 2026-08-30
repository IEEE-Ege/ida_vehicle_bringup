#!/usr/bin/env python3
"""
master_hw.launch.py — Kademeli (staged) Gerçek Donanım Başlatma (Jetson Nano)
============================================================================
KTR §2.1: Jetson Nano kaynak-kısıtlı olduğundan düğümler TimerAction ile
kademeli başlatılır (hepsi aynı anda başlatılırsa CPU/RAM darboğazı ve başlatma
hataları oluşur):

  T+0  Sürücüler + güvenlik : robot_state_publisher, mavros, kamera,
                              camera_processor, cloud_preprocessor, estop_node, fdir_node
  T+5  Algı + kayıt         : hdbscan, yolo, fusion, loggerlar
  T+20 Navigasyon           : Nav2 (planner/controller/costmap)
  T+30 Kontrol + görev      : guidance_governor, cmd_vel_relay, failsafe_node,
                              mission_node, calibration_node

real_hw.launch.py hepsini aynı anda başlatan basit/geliştirme sürümüdür;
master_hw.launch.py yarışma/üretim launch'ıdır.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg_bringup    = get_package_share_directory('ida_bringup')
    pkg_navigation = get_package_share_directory('ida_navigation')
    pkg_perception = get_package_share_directory('ida_perception')
    pkg_mission    = get_package_share_directory('ida_mission')
    pkg_bridge     = get_package_share_directory('ida_mavros_bridge')
    pkg_logger     = get_package_share_directory('ida_data_logger')
    pkg_camera     = get_package_share_directory('ida_camera')
    pkg_safety     = get_package_share_directory('ida_safety')

    urdf_path = os.path.join(pkg_bringup, 'urdf', 'mavi_inci.urdf.xacro')
    robot_desc = xacro.process_file(urdf_path).toxml()

    nav2_params = os.path.join(pkg_navigation, 'config', 'nav2_params.yaml')
    perc_params = os.path.join(pkg_perception, 'config', 'perception_params.yaml')
    mission_cfg = os.path.join(pkg_mission, 'config', 'mission_params.yaml')
    bridge_cfg  = os.path.join(pkg_bridge, 'config', 'mavros_bridge_params.yaml')
    logger_cfg  = os.path.join(pkg_logger, 'config', 'logger_params.yaml')
    camera_cfg  = os.path.join(pkg_camera, 'config', 'camera_params.yaml')
    safety_cfg  = os.path.join(pkg_safety, 'config', 'safety_params.yaml')
    # apm.launch, mavros'un ROS 2 XML launch dosyasıdır (<launch>...</launch>,
    # "ft=xml" vim modeline'ı ile işaretli) — PythonLaunchDescriptionSource ile
    # dahil edilirse Python olarak parse edilmeye çalışılır ve "invalid syntax
    # line 1" hatası verir (dosyanın ilk satırı geçerli Python değil). Doğru
    # kaynak tipi XMLLaunchDescriptionSource'tur.
    mavros_launch = os.path.join(
        get_package_share_directory('mavros'), 'launch', 'apm.launch')
    nav2_launch = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch', 'navigation_launch.py')

    # ── T+0: Sürücüler + güvenlik ──────────────────────────────────────────
    stage0 = [
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher',
             parameters=[{'robot_description': robot_desc, 'use_sim_time': False}]),
        IncludeLaunchDescription(
            XMLLaunchDescriptionSource(mavros_launch),
            launch_arguments={'fcu_url': LaunchConfiguration('fcu_url'),
                              'gcs_url': ''}.items()),
        Node(package='v4l2_camera', executable='v4l2_camera_node', name='camera',
             parameters=[{'video_device': '/dev/video0', 'image_width': 1920,
                          'image_height': 1080, 'pixel_format': 'YUYV',
                          'camera_frame_id': 'camera_link'}]),
        Node(package='ida_camera', executable='camera_processor_node',
             name='camera_processor', parameters=[camera_cfg]),
        Node(package='ida_lidar', executable='cloud_preprocessor',
             name='cloud_preprocessor',
             parameters=[{'lidar_topic': '/scan', 'input_type': 'laserscan',
                          'use_sim_time': False}]),
        # Güvenlik erken başlar
        Node(package='ida_mavros_bridge', executable='estop_node',
             name='estop_node', parameters=[bridge_cfg]),
        Node(package='ida_safety', executable='fdir_node',
             name='fdir_node', parameters=[safety_cfg]),
    ]

    # ── T+5: Algı + kayıt ──────────────────────────────────────────────────
    stage5 = [
        Node(package='ida_perception', executable='hdbscan_node',
             name='hdbscan_node', parameters=[perc_params]),
        Node(package='ida_perception', executable='yolo_node',
             name='yolo_node', parameters=[perc_params]),
        Node(package='ida_perception', executable='fusion_node',
             name='fusion_node', parameters=[perc_params]),
        Node(package='ida_data_logger', executable='video_logger',
             name='video_logger', parameters=[logger_cfg]),
        Node(package='ida_data_logger', executable='lidar_video_logger',
             name='lidar_video_logger', parameters=[logger_cfg]),
        Node(package='ida_data_logger', executable='telemetry_logger',
             name='telemetry_logger', parameters=[logger_cfg]),
        Node(package='ida_data_logger', executable='costmap_logger',
             name='costmap_logger', parameters=[logger_cfg]),
    ]

    # ── T+20: Nav2 ─────────────────────────────────────────────────────────
    stage20 = [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_launch),
            launch_arguments={'params_file': nav2_params,
                              'use_sim_time': 'false'}.items()),
    ]

    # ── T+30: Kontrol + görev ──────────────────────────────────────────────
    stage30 = [
        Node(package='ida_mavros_bridge', executable='guidance_governor',
             name='guidance_governor', parameters=[bridge_cfg]),
        Node(package='ida_mavros_bridge', executable='cmd_vel_relay',
             name='cmd_vel_relay', parameters=[bridge_cfg]),
        Node(package='ida_mavros_bridge', executable='failsafe_node',
             name='failsafe_node', parameters=[bridge_cfg]),
        Node(package='ida_mavros_bridge', executable='calibration_node',
             name='calibration_node', parameters=[bridge_cfg]),
        Node(package='ida_mavros_bridge', executable='mavlink_command_bridge',
             name='mavlink_command_bridge', parameters=[bridge_cfg]),
        Node(package='ida_mission', executable='mission_node', name='mission_node',
             parameters=[mission_cfg,
                         {'target_color': LaunchConfiguration('target')}]),
    ]

    return LaunchDescription([
        # Pixhawk, Jetson 40-pin UART (pin 8 TXD / pin 10 RXD → /dev/ttyTHS1) ile
        # bağlı (USB değil). USB kullanılırsa fcu_url:=serial:///dev/ttyACM0:921600.
        DeclareLaunchArgument('fcu_url', default_value='serial:///dev/ttyTHS1:921600'),
        DeclareLaunchArgument('target', default_value='yellow'),

        *stage0,
        TimerAction(period=5.0,  actions=stage5),
        TimerAction(period=20.0, actions=stage20),
        TimerAction(period=30.0, actions=stage30),
    ])
