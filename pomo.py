import time
import tkinter as tk

# set the time interval for work and break periods
work_time = 25 * 60  # 25 minutes
break_time = 2.5 * 60  # 2.5 minutes

# function to lock the screen
def lock_screen():
    # create a new window and make it full screen
    root = tk.Tk()
    root.attributes('-topmost', True, )
    root.attributes('-fullscreen', True,)
    root.configure(bg='black')

    # add a label to display the lock screen message
    label = tk.Label(root, text="Time for a break!", font=("Helvetica", 36),fg="red",bg="black")
    label.pack(expand=True)

    # update the window and wait for the break period to end
    root.update()
    time.sleep(break_time -10)
    label = tk.Label(root, text="Get back to work!", font=("Helvetica", 36) ,fg="green",bg="black")
    label.pack(expand=True)
    
    # destroy the window and unlock the screen
    root.destroy()

# function to unlock the screen
# start the Pomodoro timer
a = 0
while a < 6:
    # start a work period
    print("Starting work period...")
    time.sleep(work_time)

    # start a break period
    print("Starting break period...")
    lock_screen()
    #
    a += 1
# lock_screen()

