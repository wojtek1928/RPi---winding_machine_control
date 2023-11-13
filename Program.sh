#!/bin/bash

# Start pigpiod as a background process with sudo
sudo pigpiod

# Wait for pigpiod to initialize (you can adjust the sleep time as needed)
sleep 1

# Mount remote dir with sqlitedb with sudo
sudo mount /home/admin/Dokumenty/project/windows_SHARED
## Config file: /etc/fstab
## win-credentials: /etc/win-credentials

# Wait for mount
sleep 1

# Navigate to the directory containing main.py (replace /path/to/your/directory)
cd /home/admin/Dokumenty

# Run main.py (replace python3 with the appropriate command if needed)
python project/main.py

# Optionally, stop pigpiod when main.py exits (uncomment the line below)
sudo killall pigpiod
