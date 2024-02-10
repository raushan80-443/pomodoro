# pomodoro
Pomodoro Timer

The Pomodoro Timer is a simple application that helps you manage your time using the Pomodoro Technique. 
Pomodoro Timer
How to Use

    Clone the repository to your local machine:

    bash

git clone https://github.com/raushan102189/pomodoro.git

Navigate to the cloned directory:

bash

cd pomodoro

Install the required dependencies:

pip install -r requirements.txt

Run the Pomodoro timer:

    python pomo.py

    The timer will start running with 40 minutes of work time followed by a 4-minute break. After every 3rd work session, there will be a longer break of 16 minutes.

    To stop the timer, click the "Window" button, right-click on the terminal window running the Pomodoro timer, and select "Close" or "Quit" from the context menu.

Setting Up as a systemd Service (Linux)

    Clone the repository to your local machine:

    bash

git clone https://github.com/raushan102189/pomodoro.git

Copy the files to the appropriate location:

bash

sudo cp -r pomodoro /usr/share/

Create a systemd service unit file:

bash

sudo nano /etc/systemd/system/lockscreen.service

Paste the following content into the lockscreen.service file:

makefile

[Unit]
Description=Lock Screen Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/share/pomodoro/pomo.py
WorkingDirectory=/usr/share/pomodoro
Restart=always

[Install]
WantedBy=multi-user.target

Save and close the file by pressing Ctrl + O, followed by Ctrl + X.

Enable and start the service:

bash

    sudo systemctl enable lockscreen.service
    sudo systemctl start lockscreen.service

Contributions

Contributions to the Pomodoro Timer are welcome! If you find any bugs or have suggestions for improvements, please open an issue or submit a pull request.
License

This project is licensed under the MIT License. See the LICENSE file for details.

Feel free to customize the content further based on your specific needs.

