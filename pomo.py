import time
import tkinter as tk
import playsound

# set the time interval for work and break periods
work_time =40 * 60  # 25 minutes
break_time = 4 * 60  # 2.5 minutes

# function to lock the screen
def lock_screen(lock):
    # create a new window and make it full screen5
    root = tk.Tk()
    root.attributes('-topmost', True, )
    root.attributes('-fullscreen', True,)
    root.configure(bg='black')

    # add a label to display the lock screen message
    label = tk.Label(root, text=f"Time for a break! {lock} \n\n just go away turn of display \n\n break is more important ", font=("Helvetica", 36),fg="red",bg="black")
    label.pack(expand=True)

    # update the window and wait for the break period to end
    root.update()
    playsound.playsound("redy.mp3")
    
    time.sleep(break_time -40)
    label = tk.Label(root, text="Get back to work! \n\n very important", font=("Helvetica", 36) ,fg="green",bg="black")
    time.sleep(10)
   
    label.pack(expand=True)
    root.update()
    playsound.playsound("god.mp3")
    # destroy the window and unlock the screen
    root.destroy()

# function to unlock the screen
# start the Pomodoro timer

for i in range(2):
    for i in range(3):
        # start a work period
        print(f"focus as you can {a+1}")
        time.sleep(work_time)
    
    
        # start a break period
        print("get some rest ")
        lock_screen(a)
        # playsound.playsound("god.mp3")
    time.sleep(600)
        #
    
# lock_screen()

