from pyDHgripper import PGE    
import time
gripper = PGE(port="/dev/ttyUSB0")
# for i in range(1000):
#     gripper.set_pos(val=i, is_read=False, blocking=False)
#     print("set:",i,"---",i+100)
#     print("pos:", gripper.read_pos(is_read=True))
s = time.time()
for i in range(1000, 0, -20):
    s1 = time.time()
    gripper.set_pos(val=i, is_read=False, blocking=False)
    gripper.set_force(val=80)
    gripper.set_vel(val=100)
    print(1/(time.time()-s1), print(i))
    
print(time.time()-s)
# gripper.set_pos(val=1000, is_read=False, blocking=False)