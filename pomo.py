import time
import tkinter as tk

# function to lock the screen
def lock_screen(break_time):
    # create a new window and make it full screen5
    root = tk.Tk()
    root.attributes('-topmost', True, )
    root.attributes('-fullscreen', True,)
    root.configure(bg='black')

    # add a label to display the lock screen message
    label = tk.Label(root, text=f"Time for a break!  \n\n just go away turn of display \n\n break is more important ", font=("Helvetica", 36),fg="red",bg="black")
    label.pack(expand=True)

    # update the window and wait for the break period to end
    root.update()

    
    time.sleep(break_time -10)
    label = tk.Label(root, text="Get back to work! \n\n very important", font=("Helvetica", 36) ,fg="green",bg="black")
   
   
    label.pack(expand=True)
    root.update()
    time.sleep(10)

    # destroy the window and unlock the screen
    root.destroy()


