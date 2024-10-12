from pomo import lock_screen
import time
# set the time interval for work and break periods
work_time =40 * 60  # 40 minutes
break_time = 4 * 60  # 4 minutes
for i in range(3):

    # start a work period
    print(f"hold push your limit {i+1}")
    time.sleep(work_time)


    # start a break period
    print("get some rest ")
    lock_screen(break_time)
