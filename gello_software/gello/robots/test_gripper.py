from pyDHgripper import PGE    
import time
gripper = PGE(port="/dev/ttyUSB1")
import time
import random
#5 10 30
# 自定义频率（Hz）
freq = 60
interval = 1.0 / freq  # 每次发送的时间间隔

current_val = 1000
step_num = 5000
while step_num > 0:
    start_time = time.time()

    # 计算随机步长，确保不会低于0
    step = random.randint(1, 6)  # 步长在10~50之间
    print("current_val:", current_val)
    current_val -= step
    step_num -= 1
    # 发送命令
    gripper.set_pos(val=current_val, is_read=False, blocking=False)

    # 保证频率
    elapsed = time.time() - start_time
    sleep_time = max(0, interval - elapsed)
    time.sleep(sleep_time)
    print("freq:",1/(time.time()-start_time))
