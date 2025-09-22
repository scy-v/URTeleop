import rospy
import rospkg
import roslaunch
from std_msgs.msg import Float32
from dh_gripper_msgs.msg import GripperCtrl
from dh_gripper_msgs.msg import GripperState
class DhGripper:
    def __init__(self, states_topic, ctrl_topic):
        """
        初始化夹爪驱动，相当于运行: roslaunch dh_gripper_driver dh_gripper.launch
        """

        # 启动 roslaunch（方式2: 内部启动）
        uuid = roslaunch.rlutil.get_or_generate_uuid(None, False)
        rospack = rospkg.RosPack()
        pkg_path = rospack.get_path("dh_gripper_driver")
        launch_file = pkg_path + "/launch/dh_gripper.launch"
        launch = roslaunch.parent.ROSLaunchParent(uuid, [launch_file])
        launch.start()
        rospy.init_node("dh_gripper_node", anonymous=True)
        rospy.sleep(1)
        # 订阅夹爪位置
        self._position = None
        rospy.Subscriber(states_topic, GripperState, self._position_callback)
        rospy.sleep(1)
        # 发布控制命令
        self.gripper_ctrl_pub = rospy.Publisher(ctrl_topic, GripperCtrl, queue_size=1)
    
    def _position_callback(self, msg):
        self._position = msg.position

    def get_current_position(self):
        """
        获取当前夹爪位置
        """
        if self._position is None:
            print("未收到位置数据")
            return None
        return self._position

    def move(self, position, speed, force):
        """
        控制夹爪运动
        :param position: 目标位置 (float)
        :param speed: 速度 (float)
        :param force: 夹持力 (float)
        """
        gripper_msg = GripperCtrl()
        gripper_msg.initialize = False 
        gripper_msg.position = position   
        gripper_msg.force = force    
        gripper_msg.speed = speed     

        # 发布消息
        self.gripper_ctrl_pub.publish(gripper_msg)

if __name__ == "__main__":
    gripper = DhGripper()
    rospy.sleep(1)  # 等待话题建立
    print("当前位置:", gripper.get_current_position())
    gripper.move(1000, 100, 20.0)
    rospy.spin()