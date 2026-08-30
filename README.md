# ida_vehicle_bringup — gerçek donanım başlatma / real-hardware bringup

**🇹🇷 [Türkçe](#türkçe) · 🇬🇧 [English](#english)**

---

## Türkçe

### Genel Bakış
Gerçek araç (Jetson + Pixhawk) tarafını bir arada başlatan bringup paketi:
`real_hw.launch.py` + URDF. Algoritma düğümleri ayrı repolardan gelir.

### Kurulum
> Önkoşullar: ROS 2 Humble, `colcon`, `rosdep`, `mavros`, `v4l2_camera`, Nav2 ve
> aşağıdaki bölünmüş algoritma paketleri (aynı workspace'te olmalı).

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone <REPO_URL> ida_vehicle_bringup
# + tüm bağımlı algoritma repolarını aynı src/ altına klonlayın (aşağıdaki tablo)
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build
source install/setup.bash
```

### Kullanım
```bash
ros2 launch ida_vehicle_bringup real_hw.launch.py
```
> URDF'teki gövde ölçüleri/mount konumları yer tutucudur; kendi araç
> geometrinizi girin.

### Entegrasyon eşlemesi (ÖNEMLİ)
Tekil paketler algoritma bazında bölündüğü için düğümlerin **paket adları
değişti**. `launch/real_hw.launch.py` hâlâ eski adlara referans verebilir;
çalıştırmadan önce şu eşlemeye göre güncelleyin:

| Eski (monolitik) | Yeni repo / paket |
|------------------|-------------------|
| `ida_perception hdbscan_node` | `ida_lidar_clustering hdbscan_node` |
| `ida_perception yolo_node` | `ida_yolo_detection yolo_node` |
| `ida_perception fusion_node` | `ida_camera_lidar_fusion fusion_node` |
| `ida_mavros_bridge cmd_vel_relay` | `ida_mavros_bridge_core cmd_vel_relay` |
| `ida_mavros_bridge failsafe_node` | `ida_mavros_bridge_core failsafe_node` |
| `ida_mavros_bridge guidance_governor` | `ida_guidance_governor guidance_governor` |
| `ida_mavros_bridge calibration_node` | `ida_guidance_governor calibration_node` |
| `ida_mavros_bridge estop_node` | `ida_estop_gpio estop_node` |
| `ida_mavros_bridge mavlink_command_bridge` | `ida_mavlink_bridge mavlink_command_bridge` |
| `ida_lidar`, `ida_camera`, `ida_mission`, `ida_navigation`, `ida_safety`, `ida_data_logger`, `ida_msgs` | *(aynı ad)* |

### Bağımlılıklar
`robot_state_publisher`, `mavros`, `v4l2_camera`, `nav2_bringup` + bölünmüş
algoritma paketleri (`package.xml`'de listelidir). Pip bağımlılığı yoktur.

### Lisans
**MIT.** Bringup paketinin kendi kodu MIT'tir; bulaşıcı bağımlılık içermez.

**Kullanım koşulları:** Özgürce kullanın/değiştirin/dağıtın; lisans bildirimini
koruyun. **Dikkat:** bu bringup `ida_yolo_detection` (AGPL-3.0) düğümünü de
başlatıyorsa, yayınlanan sistemin bütününde AGPL yükümlülükleri (kaynak açma)
doğar. Geliştirme yaparsanız bize **PR açmanız bizi mutlu eder** (zorunlu değil).

### Özel veri
`urdf/mavi_inci.urdf.xacro` içindeki **gövde ölçüleri, kütle/atalet ve sensör
montaj konumları kaldırılmış**, yer tutucularla değiştirilmiştir.

---

## English

### Overview
Bringup package that launches the real-vehicle (Jetson + Pixhawk) side together:
`real_hw.launch.py` + URDF. The algorithm nodes come from separate repos.

### Installation
> Prerequisites: ROS 2 Humble, `colcon`, `rosdep`, `mavros`, `v4l2_camera`, Nav2
> and the split algorithm packages below (all in the same workspace).

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone <REPO_URL> ida_vehicle_bringup
# + clone all dependent algorithm repos into the same src/ (see table)
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build
source install/setup.bash
```

### Usage
```bash
ros2 launch ida_vehicle_bringup real_hw.launch.py
```
> The hull dimensions / mount offsets in the URDF are placeholders; enter your
> own vehicle geometry.

### Integration mapping (IMPORTANT)
Because the monolithic packages were split by algorithm, **node package names
changed**. `launch/real_hw.launch.py` may still reference the old names; update
them before running:

| Old (monolithic) | New repo / package |
|------------------|--------------------|
| `ida_perception hdbscan_node` | `ida_lidar_clustering hdbscan_node` |
| `ida_perception yolo_node` | `ida_yolo_detection yolo_node` |
| `ida_perception fusion_node` | `ida_camera_lidar_fusion fusion_node` |
| `ida_mavros_bridge cmd_vel_relay` | `ida_mavros_bridge_core cmd_vel_relay` |
| `ida_mavros_bridge failsafe_node` | `ida_mavros_bridge_core failsafe_node` |
| `ida_mavros_bridge guidance_governor` | `ida_guidance_governor guidance_governor` |
| `ida_mavros_bridge calibration_node` | `ida_guidance_governor calibration_node` |
| `ida_mavros_bridge estop_node` | `ida_estop_gpio estop_node` |
| `ida_mavros_bridge mavlink_command_bridge` | `ida_mavlink_bridge mavlink_command_bridge` |
| `ida_lidar`, `ida_camera`, `ida_mission`, `ida_navigation`, `ida_safety`, `ida_data_logger`, `ida_msgs` | *(unchanged)* |

### Dependencies
`robot_state_publisher`, `mavros`, `v4l2_camera`, `nav2_bringup` + the split
algorithm packages (listed in `package.xml`). No pip dependencies.

### License
**MIT.** The bringup package's own code is MIT; it has no contagious dependency.

**Terms:** free to use/modify/distribute; preserve the license notice. **Note:**
if this bringup also launches the `ida_yolo_detection` (AGPL-3.0) node, AGPL
obligations (source disclosure) apply to the distributed system as a whole. If
you improve it, **a PR back to us would make us happy** (not required).

### Private data
The **hull dimensions, mass/inertia and sensor mounting offsets** in
`urdf/mavi_inci.urdf.xacro` were removed and replaced with placeholders.

---

<div align="center">

💙 **Bu Repo IEEE Ege Mavi İnci İnsansız Deniz Aracı Takımı Yazılım Ekibi Tarafından Oluşturulmuştur, Yazılım Ekibimize Sevgilerle**

[@NightKnight-nx2](https://github.com/NightKnight-nx2) · [@yalinoner](https://github.com/yalinoner) · [@nilayyldz](https://github.com/nilayyldz)

</div>
