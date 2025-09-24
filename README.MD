# 📦 [Gello](https://github.com/wuphilipp/gello_software) and [DHGripper](https://github.com/han-xudong/pyDHgripper): Setup and Usage


```bash
# 1. Create and activate environment
conda create -n teleop python=3.11 -y
conda activate teleop

# 2. Create folder and clone repo
mkdir teleop && cd teleop
git clone https://github.com/scy-v/URTeleop.git

# 3. Install packages
cd <gello_software folder>
pip install -r requirements.txt
pip install -e .
pip install -e third_party/DynamixelSDK/python

cd <pyDHgripper>
pip install -r requirements.txt
pip install -e .

# 4. Get master-slave arm offset
cd <gello_software folder>
# ===============================
# IMPORTANT:
# Ensure the master arm's joint angles match agent.start_joints in the YAML,
# and the slave arm is approximately the same (does not have to match exactly).
# ===============================
python scripts/gello_get_offset.py --config configs/ur5_teleop.yaml
# After running, copy the displayed best offsets into agent.dynamixel_config.joint_offsets in the YAML.

# 5. Run teleoperation
python experiments/launch_yaml.py --left-config-path configs/ur5_teleop.yaml

# 6. Teleoperation with gravity compensation (optional)
python gello/factr/gravity_compensation.py --config configs/ur5_teleop_grav.yaml
```
# 📝 YAML Parameters Instruction for UR5

```bash
robot:
  _target_: gello.robots.ur.URRobot # Robot Type
  robot_ip: 192.168.60.1            # Robot IP address
  no_gripper: False                 # Whether to control gripper
  gripper_port: /dev/ttyUSB0        # Gripper serial port
  gripper_binary_mode: True         # Use discrete (binary) gripper control
  reverse_gripper: False            # Reverse gripper open/close direction
  gripper_thresh: 700               # Threshold for binary mode gripper closure

agent:
  _target_: gello.agents.gello_agent.GelloAgent
  port: "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A50285BI-if00-port0"  # Master arm port
  dynamixel_config:
    _target_: gello.agents.gello_agent.DynamixelRobotConfig
    joint_ids: [1, 2, 3, 4, 5, 6]                        # Dynamixel joint IDs
    joint_offsets: [4.712, 4.712, 4.712, 4.712, 4.712, 3.142]  # Offsets after gello_get_offset.py
    joint_signs: [1, 1, -1, 1, 1, 1]                    # Joint direction signs
    gripper_config: [7, 2.51572849, 3.47906843]         # Gripper ID, min, max values
  start_joints: [1.5707963267948966, -1.5707963267948966, 1.5707963267948966, -1.5707963267948966, -1.5707963267948966, 0]  # Initial joint positions

hz: 30          # Control loop frequency
max_steps: 1000 # Maximum number of steps
```

