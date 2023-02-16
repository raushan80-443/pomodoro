import time
import tkinter as tk
import pygame
#play song game over
pygame.mixer.init()
pygame.mixer.music.load("gameover.mp3")
pygame.mixer.music.play()   

# set the time interval for work and break periods
work_time = 20 * 60  # 20 minutes
break_time = 2 * 60  # 2 minutes

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
    unlock_screen()


    # destroy the window and unlock the screen
    root.destroy()

# function to unlock the screen
def unlock_screen():
    # create a new window and make it full screen
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.attributes('-fullscreen', True)
    root.configure(bg='black')


    # add a label to display the unlock message
    label = tk.Label(root, text="Get back to work!", font=("Helvetica", 36) ,fg="green",bg="black")
    label.pack(expand=True)

    # update the window and wait for the work period to end
    root.update()
    time.sleep(3)

    # destroy the window and lock the screen
    root.destroy()
    # lock_screen()

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
    unlock_screen()
    a += 1
# lock_screen()

