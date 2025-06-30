#!/usr/bin/env python3
"""
Gamer Cred Desktop - Python Version
A simple desktop companion for the Gamer Cred Discord bot
"""

import customtkinter as ctk
import webbrowser
import threading
import time
import json
import os
import sys
from datetime import datetime
import requests
from tkinter import scrolledtext
import subprocess
import psutil

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class GamerCredApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gamer Cred Desktop")
        self.geometry("900x650")
        self.resizable(False, False)
        self.iconbitmap(default=None)

        # Configuration
        self.api_url = "https://gamercred.onrender.com"
        self.is_tracking = False
        self.current_game = None
        self.session_start = None
        self.tracking_thread = None
        
        # Game detection settings
        self.game_processes = {
            'steam.exe', 'EpicGamesLauncher.exe', 'cs2.exe', 'dota2.exe',
            'league of legends.exe', 'valorant.exe', 'minecraft.exe',
            'eldenring.exe', 'cyberpunk2077.exe', 'gta5.exe'
        }

        # Main layout
        self.tabview = ctk.CTkTabview(self, width=880, height=600)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        # Tabs
        self.home_tab = self.tabview.add("Home")
        self.leaderboard_tab = self.tabview.add("Leaderboard")
        self.log_tab = self.tabview.add("Log Session")
        self.activity_tab = self.tabview.add("Activity")
        self.bonuses_tab = self.tabview.add("Bonuses")

        self.create_home_tab()
        self.create_leaderboard_tab()
        self.create_log_tab()
        self.create_activity_tab()
        self.create_bonuses_tab()

        self.load_settings()
        
    def create_home_tab(self):
        frame = ctk.CTkFrame(self.home_tab, corner_radius=16)
        frame.pack(padx=30, pady=30, fill="both", expand=True)
        title = ctk.CTkLabel(frame, text="Gamer Cred Companion", font=("Inter", 32, "bold"), text_color="#ff6fae")
        title.pack(pady=(20, 10))
        subtitle = ctk.CTkLabel(frame, text="Track your gaming sessions, view leaderboards, and more!", font=("Inter", 18))
        subtitle.pack(pady=(0, 30))
        open_web_btn = ctk.CTkButton(frame, text="Open Website Homepage", fg_color="#5966f2", hover_color="#ff6fae", command=lambda: webbrowser.open_new_tab("https://your-website-homepage.com"))
        open_web_btn.pack(pady=10)
        info = ctk.CTkLabel(frame, text="All features are available in the app tabs above.", font=("Inter", 14))
        info.pack(pady=(30, 10))

    def create_leaderboard_tab(self):
        frame = ctk.CTkFrame(self.leaderboard_tab, corner_radius=16)
        frame.pack(padx=20, pady=20, fill="both", expand=True)
        label = ctk.CTkLabel(frame, text="Leaderboard (Coming Soon)", font=("Inter", 22, "bold"), text_color="#ff6fae")
        label.pack(pady=30)
        # TODO: Add leaderboard data and UI

    def create_log_tab(self):
        frame = ctk.CTkFrame(self.log_tab, corner_radius=16)
        frame.pack(padx=20, pady=20, fill="both", expand=True)
        label = ctk.CTkLabel(frame, text="Log Game Session (Coming Soon)", font=("Inter", 22, "bold"), text_color="#ff6fae")
        label.pack(pady=30)
        # TODO: Add log session form and timer

    def create_activity_tab(self):
        frame = ctk.CTkFrame(self.activity_tab, corner_radius=16)
        frame.pack(padx=20, pady=20, fill="both", expand=True)
        label = ctk.CTkLabel(frame, text="Recent Activity (Coming Soon)", font=("Inter", 22, "bold"), text_color="#ff6fae")
        label.pack(pady=30)
        # TODO: Add recent activity UI

    def create_bonuses_tab(self):
        frame = ctk.CTkFrame(self.bonuses_tab, corner_radius=16)
        frame.pack(padx=20, pady=20, fill="both", expand=True)
        label = ctk.CTkLabel(frame, text="Recent Bonuses (Coming Soon)", font=("Inter", 22, "bold"), text_color="#ff6fae")
        label.pack(pady=30)
        # TODO: Add bonuses UI

    def start_tracking(self):
        """Start game tracking"""
        if not self.is_tracking:
            self.is_tracking = True
            self.session_start = datetime.now()
            self.log_message("Game tracking started")
            
            # Start tracking thread
            self.tracking_thread = threading.Thread(target=self.track_games, daemon=True)
            self.tracking_thread.start()
            
    def stop_tracking(self):
        """Stop game tracking"""
        if self.is_tracking:
            self.is_tracking = False
            self.session_start = None
            self.current_game = None
            self.log_message("Game tracking stopped")
            
    def track_games(self):
        """Track active games in a separate thread"""
        while self.is_tracking:
            try:
                # Get active processes
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] and proc.info['name'].lower() in self.game_processes:
                        if self.current_game != proc.info['name']:
                            self.current_game = proc.info['name']
                            self.root.after(0, self.update_game_display)
                            self.log_message(f"Game detected: {self.current_game}")
                        break
                else:
                    if self.current_game:
                        self.current_game = None
                        self.root.after(0, self.update_game_display)
                        self.log_message("No game detected")
                        
                # Update timer
                if self.session_start:
                    self.root.after(0, self.update_timer)
                    
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.log_message(f"Error tracking games: {str(e)}")
                time.sleep(10)
                
    def update_game_display(self):
        """Update the game display"""
        if self.current_game:
            self.root.after(0, self.update_timer)
            
    def update_timer(self):
        """Update the session timer"""
        if self.session_start:
            elapsed = datetime.now() - self.session_start
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            seconds = int(elapsed.total_seconds() % 60)
            self.root.after(0, self.update_game_display)
            
    def log_session(self):
        """Log the current session"""
        if not self.current_game or not self.session_start:
            self.log_message("No active session to log")
            return
            
        # Calculate session duration
        elapsed = datetime.now() - self.session_start
        hours = elapsed.total_seconds() / 3600
        
        if hours < 0.1:
            self.log_message("Session too short (minimum 0.1 hours)")
            return
            
        # Show confirmation dialog
        result = ctk.CTk.askyesno(self, "Log Session", 
                                   f"Log {hours:.1f} hours of {self.current_game}?")
        if result:
            try:
                # Here you would make an API call to log the session
                # For now, just show a success message
                self.log_message(f"Session logged: {hours:.1f}h of {self.current_game}")
                self.stop_tracking()
            except Exception as e:
                self.log_message(f"Error logging session: {str(e)}")
                
    def log_message(self, message):
        """Add a message to the log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(ctk.END, log_entry)
        self.log_text.see(ctk.END)
        
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
                    self.api_url = settings.get('api_url', self.api_url)
        except Exception as e:
            self.log_message(f"Error loading settings: {str(e)}")
            
    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                'api_url': self.api_url
            }
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.log_message(f"Error saving settings: {str(e)}")
            
    def run(self):
        """Run the application"""
        self.mainloop()

def main():
    """Main function"""
    app = GamerCredApp()
    app.run()

if __name__ == "__main__":
    main() 