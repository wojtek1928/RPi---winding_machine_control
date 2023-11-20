#!/bin/bash

# Start pigpiod as a background process with sudo
sudo pigpiod

# Wait for pigpiod to initialize (you can adjust the sleep time as needed)
sleep 1

# Define the duration for attempting to mount (in seconds)
mount_timeout=10

# Attempt to mount for the specified duration
start_time=$(date +%s)
while true; do
    sudo mount /home/admin/Dokumenty/project/windows_SHARED
    if [ $? -eq 0 ]; then
        break  # Break the loop if the mount was successful
    fi

    # Check if the timeout has been reached
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    if [ $elapsed_time -ge $mount_timeout ]; then
        echo "Mount operation timed out after $mount_timeout seconds."
        break  # Break the loop if the timeout is reached
    fi

    sleep 1
done

# Continue with the rest of the script

# Navigate to the directory containing main.py (replace /path/to/your/directory)
cd /home/admin/Dokumenty

# Run main.py (replace python3 with the appropriate command if needed)
python project/main.py

# Optionally, stop pigpiod when main.py exits (uncomment the line below)
sudo killall pigpiod