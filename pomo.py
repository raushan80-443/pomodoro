import time
import tkinter as tk
import playsound

# set the time interval for work and break periods
work_time = 40 * 60  # 25 minutes
break_time = 4 * 60  # 2.5 minutes

# function to lock the screen
def lock_screen(lock):
    # create a new window and make it full screen
    root = tk.Tk()
    root.attributes('-topmost', True, )
    root.attributes('-fullscreen', True,)
    root.configure(bg='black')

    # add a label to display the lock screen message
    label = tk.Label(root, text=f"Time for a break!{lock} \n just go away turn of display \n\n break is more important ", font=("Helvetica", 36),fg="red",bg="black")
    label.pack(expand=True)

    # update the window and wait for the break period to end
    root.update()
    playsound.playsound("redy.mp3")
    time.sleep(break_time -10)
    label = tk.Label(root, text="Get back to work! very important", font=("Helvetica", 36) ,fg="green",bg="black")
    time.sleep(10)
    playsound.playsound("god.mp3")
    label.pack(expand=True)
    
    # destroy the window and unlock the screen
    root.destroy()

# function to unlock the screen
# start the Pomodoro timer
a = 0
while a < 5:
    # start a work period
    print(f"focus as you can {a+1}")
 

    # start a break period
    print("get some rest ")
    lock_screen()
    #
    a += 1
# lock_screen()

