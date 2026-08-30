cmake_minimum_required(VERSION 3.8)
project(ida_vehicle_bringup)

find_package(ament_cmake REQUIRED)

# Only real-hardware launch + URDF are installed.
install(DIRECTORY launch/ DESTINATION share/${PROJECT_NAME}/launch)
install(DIRECTORY urdf/   DESTINATION share/${PROJECT_NAME}/urdf)

ament_package()
