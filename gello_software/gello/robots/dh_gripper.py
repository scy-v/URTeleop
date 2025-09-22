import time
import threading
from pyDHgripper import PGE    

class DhGripper:
    def __init__(self, port, binary_mode, threshold):
        """
            初始化夹爪驱动
        """
        self.position = None
        self._stop_flag = False
        self.binary_mode = binary_mode
        self.threshold = threshold
        self.alpha = 1
        self.last_pos = 0
        self._lock = threading.Lock()
        self.gripper = PGE(port=port)
        # 启动后台线程定期更新位置
        self._thread = threading.Thread(target=self._update_position, daemon=True)
        self._thread.start()
        time.sleep(0.5)
        
    def _update_position(self):
        """
            更新夹爪位置线程
        """
        while not self._stop_flag:
            with self._lock:
                pos = self.gripper.read_pos(is_read=True) 
            self._position = pos
            time.sleep(0.01)  
            
    def get_current_position(self):
        """
            获取当前夹爪位置
        """
        pos = self._position
        if pos is None:
            print("未收到位置数据")
        return pos

    def move(self, position: float, speed: float, force: float) -> None:
        """
        Move the gripper to target position with smoothing.

        Args:
            position (float): 输入位置 (0~1000)
            speed (float): 夹爪速度
            force (float): 夹爪力
        """

        if self.binary_mode: 
            target_pos = 0 if position < self.threshold else 1000

            if target_pos == self.position:
                return
            self.position = target_pos
        else:
            target_pos = position

        # target_pos = self._smooth(target_pos)

        try:
            with self._lock:
                self.gripper.set_force(val=force)
                self.gripper.set_vel(val=speed)
                self.gripper.set_pos(val=int(target_pos), is_read=False, blocking=False)
        except Exception as e:
            print(f"[Gripper Move Error] {e}")

        time.sleep(0.008)


    def _smooth(self, new_value: float) -> float:
        """一阶低通滤波"""
        smoothed = self.alpha * new_value + (1 - self.alpha) * self.last_pos
        self.last_pos = smoothed
        return smoothed
