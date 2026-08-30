#!/usr/bin/env python3
"""
real_hw.launch.py — Gerçek Donanım Başlatma (Jetson Nano)
=========================================================
Başlatılan düğümler:
  robot_state_publisher  (URDF → TF ağacı)
  mavros                 (ArduPilot FCU bağlantısı + odom/GPS/IMU)
  v4l2_camera            (Logitech C920, 1920x1080)
  camera_processor       (ida_camera: undistort/CLAHE/letterbox → /camera/image_ml)
  cloud_preprocessor     (LiDAR PCL pipeline — RPLIDAR C1 /scan, LaserScan)
  hdbscan_node           (kümeleme)
  yolo_node              (TRT algılama → /camera/image_annotated + /camera/detections)
  fusion_node            (kamera-LiDAR füzyon → /buoy_detections)
  guidance_governor      (hedefe yönelme + motor güç% karar katmanı → /cmd_vel)
  cmd_vel_relay          (/cmd_vel → MAVROS GUIDED setpoint)
  failsafe_node          (MAVROS bağlantı kaybı → RTL)
  estop_node             (uzaktan güç kesme kill-switch + fail-safe heartbeat GPIO)
  nav2_bringup           (RPP + costmap)
  mission_node           (görev durum makinesi)
  video_logger           (kamera MP4 — Dosya 1a)
  lidar_video_logger     (LiDAR kuşbakışı MP4 — Dosya 1b)
  telemetry_logger       (CSV — Dosya 2)
  costmap_logger         (bag — Dosya 3)

NOT: RPLIDAR C1'in gerçek seri port sürücüsü (rplidar_ros, /scan yayınlayan)
ayrıca kurulmalıdır (bkz. kurulum.md); cloud_preprocessor_node /scan bekler.
Odometri kaynağı MAVROS'tur (/mavros/local_position/odom); gps_imu_odom
düğümü YALNIZCA simülasyona aittir ve gerçek araçta çalıştırılmaz.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
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

    urdf_path = os.path.join(pkg_bringup, 'urdf', 'mavi_inci.urdf.xacro')
    robot_desc = xacro.process_file(urdf_path).toxml()

    nav2_params   = os.path.join(pkg_navigation, 'config', 'nav2_params.yaml')
    perc_params   = os.path.join(pkg_perception, 'config', 'perception_params.yaml')
    mission_cfg   = os.path.join(pkg_mission, 'config', 'mission_params.yaml')
    bridge_cfg    = os.path.join(pkg_bridge, 'config', 'mavros_bridge_params.yaml')
    logger_cfg    = os.path.join(pkg_logger, 'config', 'logger_params.yaml')
    camera_cfg    = os.path.join(pkg_camera, 'config', 'camera_params.yaml')
    # apm.launch, mavros'un ROS 2 XML launch dosyasıdır — PythonLaunchDescriptionSource
    # ile dahil edilirse "invalid syntax line 1" hatası verir (bkz. master_hw.launch.py).
    mavros_launch = os.path.join(
        get_package_share_directory('mavros'), 'launch', 'apm.launch'
    )
    nav2_launch   = os.path.join(
        get_package_share_directory('nav2_bringup'), 'launch', 'navigation_launch.py'
    )

    return LaunchDescription([
        # Pixhawk, Jetson 40-pin UART (pin 8 TXD / pin 10 RXD → /dev/ttyTHS1) ile
        # bağlı (USB değil). USB kullanılırsa fcu_url:=serial:///dev/ttyACM0:921600.
        DeclareLaunchArgument('fcu_url',  default_value='serial:///dev/ttyTHS1:921600'),
        DeclareLaunchArgument('target',   default_value='yellow'),

        # ── TF / Robot Description ────────────────────────────────────────
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{'robot_description': robot_desc, 'use_sim_time': False}],
        ),

        # ── MAVROS ───────────────────────────────────────────────────────
        IncludeLaunchDescription(
            XMLLaunchDescriptionSource(mavros_launch),
            launch_arguments={
                'fcu_url': LaunchConfiguration('fcu_url'),
                'gcs_url': '',
            }.items(),
        ),

        # ── Kamera (ham yakalama) ─────────────────────────────────────────
        # 1920x1080: ida_camera kalibrasyon şablonu (c920_calibration.yaml) ve
        # letterbox bütçesi bu çözünürlük için tasarlanmıştır.
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera',
            parameters=[{
                'video_device':  '/dev/video0',
                'image_width':   1920,
                'image_height':  1080,
                'pixel_format':  'YUYV',
                'camera_frame_id': 'camera_link',
            }],
        ),

        # ── Kamera Ön İşleme (ida_camera) ─────────────────────────────────
        # undistort/CLAHE/letterbox → /camera/image_ml (yolo girişi) +
        # /camera/image_processed (BGR, video yedeği)
        Node(
            package='ida_camera',
            executable='camera_processor_node',
            name='camera_processor',
            parameters=[camera_cfg],
        ),

        # ── LiDAR Pipeline (RPLIDAR C1 → /scan → LaserScan) ───────────────
        Node(
            package='ida_lidar',
            executable='cloud_preprocessor',
            name='cloud_preprocessor',
            parameters=[{
                'lidar_topic': '/scan',
                'input_type':  'laserscan',
                'use_sim_time': False,
            }],
        ),

        # ── Algı ─────────────────────────────────────────────────────────
        Node(package='ida_perception', executable='hdbscan_node',
             name='hdbscan_node', parameters=[perc_params]),
        Node(package='ida_perception', executable='yolo_node',
             name='yolo_node', parameters=[perc_params]),
        Node(package='ida_perception', executable='fusion_node',
             name='fusion_node', parameters=[perc_params]),

        # ── Karar / Kontrol Köprüsü ───────────────────────────────────────
        # guidance_governor: /cmd_vel_nav → (şekillendirme) → /cmd_vel
        Node(package='ida_mavros_bridge', executable='guidance_governor',
             name='guidance_governor', parameters=[bridge_cfg]),
        # cmd_vel_relay: /cmd_vel → MAVROS GUIDED setpoint
        Node(package='ida_mavros_bridge', executable='cmd_vel_relay',
             name='cmd_vel_relay', parameters=[bridge_cfg]),
        Node(package='ida_mavros_bridge', executable='failsafe_node',
             name='failsafe_node', parameters=[bridge_cfg]),

        # ── Uzaktan Güç Kesme (kill-switch) — safety-critical ─────────────
        Node(package='ida_mavros_bridge', executable='estop_node',
             name='estop_node', parameters=[bridge_cfg]),

        # ── Güvenlik/FDIR (mission INIT sağlık kapısı bunu bekler) ────────
        Node(package='ida_safety', executable='fdir_node', name='fdir_node',
             parameters=[os.path.join(
                 get_package_share_directory('ida_safety'), 'config', 'safety_params.yaml')]),

        # ── Otomatik eğim kalibrasyonu ────────────────────────────────────
        Node(package='ida_mavros_bridge', executable='calibration_node',
             name='calibration_node', parameters=[bridge_cfg]),

        # ── YKİ MAVLink komut köprüsü (/mavlink/from → ROS) ───────────────
        Node(package='ida_mavros_bridge', executable='mavlink_command_bridge',
             name='mavlink_command_bridge', parameters=[bridge_cfg]),

        # ── Nav2 ─────────────────────────────────────────────────────────
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_launch),
            launch_arguments={
                'params_file': nav2_params,
                'use_sim_time': 'false',
            }.items(),
        ),

        # ── Görev ────────────────────────────────────────────────────────
        Node(
            package='ida_mission',
            executable='mission_node',
            name='mission_node',
            parameters=[
                mission_cfg,
                {'target_color': LaunchConfiguration('target')},
            ],
        ),

        # ── Veri Kaydı (harici SD kart) ───────────────────────────────────
        Node(package='ida_data_logger', executable='video_logger',
             name='video_logger', parameters=[logger_cfg]),
        Node(package='ida_data_logger', executable='lidar_video_logger',
             name='lidar_video_logger', parameters=[logger_cfg]),
        Node(package='ida_data_logger', executable='telemetry_logger',
             name='telemetry_logger', parameters=[logger_cfg]),
        Node(package='ida_data_logger', executable='costmap_logger',
             name='costmap_logger', parameters=[logger_cfg]),
    ])
