
import os
import subprocess
import time

def kill_bot_processes():
    # Get all running python processes
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    processes = result.stdout.splitlines()
    
    # Find and kill python main.py processes
    killed = 0
    for process in processes:
        if 'python main.py' in process and 'grep' not in process:
            # Extract the PID (second column in ps output)
            pid = process.split()[1]
            print(f"Killing bot process with PID: {pid}")
            try:
                subprocess.run(['kill', pid])
                killed += 1
            except Exception as e:
                print(f"Failed to kill process {pid}: {e}")
    
    print(f"Killed {killed} bot processes")
    return killed

if __name__ == "__main__":
    print("Looking for running bot processes...")
    killed = kill_bot_processes()
    
    if killed > 0:
        print("Waiting for processes to terminate...")
        time.sleep(2)  # Give processes time to terminate
    
    print("Starting a single bot instance...")
    # Start a single new instance of the bot
    subprocess.Popen(['python', 'main.py'])
    print("Bot restarted successfully!")
