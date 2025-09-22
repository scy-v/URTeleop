import importlib
import threading
import time
from typing import Any, Dict, Optional

import numpy as np
from omegaconf import OmegaConf


class SimpleLaunchManager:
    """Simplified launch manager for robot systems."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.cfg = self._load_config()
        self.robot = None
        self.agent = None
        self.env = None
        self.server_thread = None

    def _load_config(self) -> Dict[str, Any]:
        """Load and resolve configuration."""
        cfg = OmegaConf.to_container(OmegaConf.load(self.config_path), resolve=True)

        # Handle robot config
        robot_cfg = cfg["robot"]
        if isinstance(robot_cfg.get("config"), str):
            robot_cfg["config"] = OmegaConf.to_container(
                OmegaConf.load(robot_cfg["config"]), resolve=True
            )

        return cfg

    def setup_robot(self):
        """Setup the robot with proper error handling."""
        print("Setting up robot...")

        # Check if it's a Dynamixel robot
        robot_cfg = self.cfg["robot"]
        if "DynamixelRobot" in str(robot_cfg.get("_target_", "")):
            print("Detected Dynamixel robot, using enhanced initialization...")
            # Extract Dynamixel configuration
            dynamixel_config = robot_cfg.get("config", {})
            ids = dynamixel_config.get("ids", [1])
            port = dynamixel_config.get("port", "/dev/ttyUSB0")
            baudrate = dynamixel_config.get("baudrate", 57600)
            max_retries = dynamixel_config.get("max_retries", 3)
            use_fake_fallback = dynamixel_config.get("use_fake_fallback", True)

            # Use enhanced driver with retry logic and fallback
            from gello.dynamixel.driver import DynamixelDriver
            from gello.robots.dynamixel import DynamixelRobot

            driver = DynamixelDriver(
                ids=ids,
                port=port,
                baudrate=baudrate,
                max_retries=max_retries,
                use_fake_fallback=use_fake_fallback,
            )
            self.robot = DynamixelRobot(driver)
        else:
            # Use standard instantiation for other robot types
            self.robot = instantiate_from_dict(robot_cfg)

    def setup_communication(self):
        """Setup ZMQ communication for the robot."""
        from gello.env import RobotEnv
        from gello.zmq_core.robot_node import ZMQClientRobot, ZMQServerRobot

        robot_cfg = self.cfg["robot"]

        if hasattr(self.robot, "serve"):  # MujocoRobotServer or ZMQServerRobot
            print("Starting robot server...")
            # Start server in background
            self.server_thread = threading.Thread(target=self.robot.serve, daemon=True)
            self.server_thread.start()
            time.sleep(2)  # Give server time to start

            # Create client to communicate with server
            robot_client = ZMQClientRobot(
                port=robot_cfg.get("port", 5556),
                host=robot_cfg.get("host", "127.0.0.1"),
            )
        else:  # Direct robot (hardware)
            # Create ZMQ server for the hardware robot
            server = ZMQServerRobot(self.robot, port=6001, host="127.0.0.1")
            self.server_thread = threading.Thread(target=server.serve, daemon=True)
            self.server_thread.start()
            time.sleep(1)

            # Create client to communicate with hardware
            robot_client = ZMQClientRobot(port=6001, host="127.0.0.1")

        self.env = RobotEnv(robot_client, control_rate_hz=self.cfg.get("hz", 30))

    def setup_agent(self):
        """Setup the agent."""
        print("Setting up agent...")
        self.agent = instantiate_from_dict(self.cfg["agent"])

    def move_to_joints(self, joints: np.ndarray):
        """Move robot to specified joints."""
        for jnt in np.linspace(self.env.get_obs()["joint_positions"], joints, 100):
            self.env.step(jnt)
            time.sleep(0.001)

    def validate_agent_output(self):
        """Validate that agent output matches environment dimensions."""
        start_pos = self.agent.act(self.env.get_obs())
        obs = self.env.get_obs()
        joints = obs["joint_positions"]

        print(f"Start pos: {len(start_pos)}", f"Joints: {len(joints)}")
        assert len(start_pos) == len(
            joints
        ), f"agent output dim = {len(start_pos)}, but env dim = {len(joints)}"

        return start_pos

    def run_control_loop(self):
        """Run the main control loop."""
        print(
            f"Launching robot: {self.robot.__class__.__name__}, agent: {self.agent.__class__.__name__}"
        )
        print(
            f"Control loop: {self.cfg.get('hz', 30)} Hz, max_steps: {self.cfg.get('max_steps', 1000)}"
        )

        # Initial positioning
        start_pos = self.validate_agent_output()
        obs = self.env.get_obs()
        joints = obs["joint_positions"]

        abs_deltas = np.abs(start_pos - joints)
        id_max_joint_delta = np.argmax(abs_deltas)

        max_joint_delta = 1.0
        if abs_deltas[id_max_joint_delta] > max_joint_delta:
            id_mask = abs_deltas > max_joint_delta
            print()
            ids = np.arange(len(id_mask))[id_mask]
            for i, delta, joint, current_j in zip(
                ids,
                abs_deltas[id_mask],
                start_pos[id_mask],
                joints[id_mask],
            ):
                print(
                    f"joint[{i}]: \t delta: {delta:4.3f} , leader: \t{joint:4.3f} , follower: \t{current_j:4.3f}"
                )
            return

        # Smooth initial movement
        max_delta = 1.0
        for _ in range(25):
            obs = self.env.get_obs()
            command_joints = self.agent.act(obs)
            current_joints = obs["joint_positions"]
            delta = command_joints - current_joints
            max_joint_delta = np.abs(delta).max()
            if max_joint_delta > max_delta:
                delta = delta / max_joint_delta * max_delta
            self.env.step(current_joints + delta)

        # Main control loop
        print("Starting main control loop...")
        while True:
            obs = self.env.get_obs()
            action = self.agent.act(obs)
            self.env.step(action)

    def launch(self):
        """Main launch method that orchestrates everything."""
        try:
            self.setup_robot()
            self.setup_communication()
            self.setup_agent()
            move_to_start_position(self.env, left_cfg=self.cfg)
            self.run_control_loop()
        except KeyboardInterrupt:
            print("\nShutting down gracefully...")
        except Exception as e:
            print(f"Error during launch: {e}")
            raise
        finally:
            if hasattr(self.robot, "close"):
                self.robot.close()


def simple_launch(config_path: str):
    """Simple function to launch a robot system."""
    manager = SimpleLaunchManager(config_path)
    manager.launch()


def move_to_start_position(
    env,
    robot,
    bimanual: bool = False,
    left_cfg: Optional[Dict[str, Any]] = None,
    right_cfg: Optional[Dict[str, Any]] = None,
):
    """Move robot to start position if specified."""
    if bimanual:
        if right_cfg is None:
            return
        left_start = left_cfg["agent"].get("start_joints")
        right_start = right_cfg["agent"].get("start_joints")
        if left_start is None or right_start is None:
            return
        reset_joints = np.concatenate([np.array(left_start), np.array(right_start)])
    else:
        if (
            "start_joints" not in left_cfg["agent"]
            or left_cfg["agent"]["start_joints"] is None
        ):
            return
        reset_joints = np.array(left_cfg["agent"]["start_joints"])
    curr_joints = env.get_obs()["joint_positions"]
    
    if not robot._use_gripper:
        reset_joints = reset_joints[:6]
    
    if reset_joints.shape != curr_joints.shape:
        print("Warning: Mismatch in joint shapes, skipping move_to_start_position.")
        return

    max_delta = (np.abs(curr_joints - reset_joints)).max()
    steps = min(int(max_delta / 0.01), 100)

    print(f"Moving robot to start position: {reset_joints}")
    for jnt in np.linspace(curr_joints, reset_joints, steps):
        env.step(jnt)
        time.sleep(0.001)


def instantiate_from_dict(cfg):
    """Instantiate objects from configuration."""
    if isinstance(cfg, dict) and "_target_" in cfg:
        module_path, class_name = cfg["_target_"].rsplit(".", 1)
        cls = getattr(importlib.import_module(module_path), class_name)
        kwargs = {k: v for k, v in cfg.items() if k != "_target_"}
        return cls(**{k: instantiate_from_dict(v) for k, v in kwargs.items()})
    elif isinstance(cfg, dict):
        return {k: instantiate_from_dict(v) for k, v in cfg.items()}
    elif isinstance(cfg, list):
        return [instantiate_from_dict(v) for v in cfg]
    else:
        return cfg


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config-path", type=str, required=True)
    args = parser.parse_args()

    simple_launch(args.config_path)
