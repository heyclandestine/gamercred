// Session Tracker Module
window.sessionTrackerModule = {
  timerInterval: null,
  sessionStartTime: null,
  isPaused: false,
  pausedTime: 0,

  async load() {
    try {
      this.setupEventListeners();
      await this.loadCurrentSession();
      this.loadSettings();
    } catch (error) {
      console.error('Failed to load session tracker:', error);
      if (window.app) {
        window.app.showNotification('Failed to load session tracker', 'error');
      }
    }
  },

  setupEventListeners() {
    // Tracker controls
    const startBtn = document.getElementById('tracker-start-btn');
    const stopBtn = document.getElementById('tracker-stop-btn');
    const pauseBtn = document.getElementById('pause-session-btn');
    const resumeBtn = document.getElementById('resume-session-btn');
    const logBtn = document.getElementById('log-current-session-btn');

    if (startBtn) {
      startBtn.addEventListener('click', () => {
        this.startTracking();
      });
    }

    if (stopBtn) {
      stopBtn.addEventListener('click', () => {
        this.stopTracking();
      });
    }

    if (pauseBtn) {
      pauseBtn.addEventListener('click', () => {
        this.pauseSession();
      });
    }

    if (resumeBtn) {
      resumeBtn.addEventListener('click', () => {
        this.resumeSession();
      });
    }

    if (logBtn) {
      logBtn.addEventListener('click', () => {
        this.logCurrentSession();
      });
    }

    // Settings checkboxes
    const autoTrackCheckbox = document.getElementById('auto-track-checkbox');
    const notificationsCheckbox = document.getElementById('notifications-checkbox');

    if (autoTrackCheckbox) {
      autoTrackCheckbox.addEventListener('change', (e) => {
        this.updateSetting('autoTrack', e.target.checked);
      });
    }

    if (notificationsCheckbox) {
      notificationsCheckbox.addEventListener('change', (e) => {
        this.updateSetting('notifications', e.target.checked);
      });
    }
  },

  async loadCurrentSession() {
    try {
      const session = await window.electronAPI.getCurrentSession();
      if (session) {
        this.sessionStartTime = session.startTime;
        this.currentGame = session.game;
        this.updateTrackerDisplay();
        this.startTimer();
      } else {
        this.showNoSession();
      }
    } catch (error) {
      console.error('Failed to load current session:', error);
      this.showNoSession();
    }
  },

  loadSettings() {
    const autoTrackCheckbox = document.getElementById('auto-track-checkbox');
    const notificationsCheckbox = document.getElementById('notifications-checkbox');

    if (autoTrackCheckbox && window.app.settings) {
      autoTrackCheckbox.checked = window.app.settings.autoTrack || false;
    }

    if (notificationsCheckbox && window.app.settings) {
      notificationsCheckbox.checked = window.app.settings.notifications !== false;
    }
  },

  async startTracking() {
    try {
      await window.electronAPI.startTracking();
      this.sessionStartTime = Date.now();
      this.isPaused = false;
      this.pausedTime = 0;
      this.updateTrackerDisplay();
      this.startTimer();
      
      if (window.app) {
        window.app.showNotification('Game tracking started', 'success');
      }
    } catch (error) {
      console.error('Failed to start tracking:', error);
      if (window.app) {
        window.app.showNotification('Failed to start tracking', 'error');
      }
    }
  },

  async stopTracking() {
    try {
      await window.electronAPI.stopTracking();
      this.sessionStartTime = null;
      this.currentGame = null;
      this.isPaused = false;
      this.pausedTime = 0;
      this.stopTimer();
      this.showNoSession();
      
      if (window.app) {
        window.app.showNotification('Game tracking stopped', 'success');
      }
    } catch (error) {
      console.error('Failed to stop tracking:', error);
      if (window.app) {
        window.app.showNotification('Failed to stop tracking', 'error');
      }
    }
  },

  pauseSession() {
    if (!this.sessionStartTime || this.isPaused) return;
    
    this.isPaused = true;
    this.pausedTime = Date.now();
    this.updateTrackerDisplay();
    
    if (window.app) {
      window.app.showNotification('Session paused', 'warning');
    }
  },

  resumeSession() {
    if (!this.sessionStartTime || !this.isPaused) return;
    
    const pauseDuration = Date.now() - this.pausedTime;
    this.sessionStartTime += pauseDuration;
    this.isPaused = false;
    this.pausedTime = 0;
    this.updateTrackerDisplay();
    
    if (window.app) {
      window.app.showNotification('Session resumed', 'success');
    }
  },

  async logCurrentSession() {
    if (!this.sessionStartTime) {
      if (window.app) {
        window.app.showNotification('No active session to log', 'error');
      }
      return;
    }

    const duration = this.getSessionDuration();
    const hours = Math.round(duration * 10) / 10; // Round to 1 decimal place

    if (hours < 0.1) {
      if (window.app) {
        window.app.showNotification('Session too short to log (minimum 0.1 hours)', 'error');
      }
      return;
    }

    try {
      const response = await window.app.apiCall('/api/log-game', {
        method: 'POST',
        body: JSON.stringify({ 
          game: this.currentGame || 'Unknown Game', 
          hours: hours 
        })
      });

      if (response.success) {
        if (window.app) {
          window.app.showNotification('Session logged successfully!', 'success');
        }
        await this.stopTracking();
      } else {
        if (window.app) {
          window.app.showNotification(response.error || 'Failed to log session', 'error');
        }
      }
    } catch (error) {
      console.error('Failed to log session:', error);
      if (window.app) {
        window.app.showNotification('Failed to log session', 'error');
      }
    }
  },

  updateTrackerDisplay() {
    const trackerDisplay = document.getElementById('tracker-display');
    const startBtn = document.getElementById('tracker-start-btn');
    const stopBtn = document.getElementById('tracker-stop-btn');

    if (this.sessionStartTime) {
      // Show tracker display
      if (trackerDisplay) {
        trackerDisplay.style.display = 'block';
      }
      if (startBtn) startBtn.style.display = 'none';
      if (stopBtn) stopBtn.style.display = 'inline-flex';

      // Update game info
      this.updateGameInfo();
      
      // Update timer
      this.updateTimer();
      
      // Update action buttons
      this.updateActionButtons();
    } else {
      // Hide tracker display
      if (trackerDisplay) {
        trackerDisplay.style.display = 'none';
      }
      if (startBtn) startBtn.style.display = 'inline-flex';
      if (stopBtn) stopBtn.style.display = 'none';
    }
  },

  updateGameInfo() {
    const gameName = document.getElementById('current-game-name');
    const gameStatus = document.getElementById('current-game-status');

    if (gameName) {
      gameName.textContent = this.currentGame || 'No game detected';
    }

    if (gameStatus) {
      if (this.isPaused) {
        gameStatus.textContent = 'Session paused';
      } else if (this.currentGame) {
        gameStatus.textContent = 'Session active';
      } else {
        gameStatus.textContent = 'Waiting for game detection...';
      }
    }
  },

  updateTimer() {
    const hoursElement = document.getElementById('timer-hours');
    const minutesElement = document.getElementById('timer-minutes');
    const secondsElement = document.getElementById('timer-seconds');

    if (!hoursElement || !minutesElement || !secondsElement) return;

    const duration = this.getSessionDuration();
    const totalSeconds = Math.floor(duration * 3600);
    
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    hoursElement.textContent = hours.toString().padStart(2, '0');
    minutesElement.textContent = minutes.toString().padStart(2, '0');
    secondsElement.textContent = seconds.toString().padStart(2, '0');
  },

  updateActionButtons() {
    const pauseBtn = document.getElementById('pause-session-btn');
    const resumeBtn = document.getElementById('resume-session-btn');
    const logBtn = document.getElementById('log-current-session-btn');

    if (pauseBtn) {
      pauseBtn.style.display = this.isPaused ? 'none' : 'inline-flex';
    }

    if (resumeBtn) {
      resumeBtn.style.display = this.isPaused ? 'inline-flex' : 'none';
    }

    if (logBtn) {
      logBtn.disabled = !this.currentGame || this.getSessionDuration() < 0.1;
    }
  },

  startTimer() {
    if (this.timerInterval) return;
    
    this.timerInterval = setInterval(() => {
      if (!this.isPaused) {
        this.updateTimer();
      }
    }, 1000);
  },

  stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  },

  getSessionDuration() {
    if (!this.sessionStartTime) return 0;
    
    const now = this.isPaused ? this.pausedTime : Date.now();
    return (now - this.sessionStartTime) / (1000 * 60 * 60); // hours
  },

  showNoSession() {
    const trackerDisplay = document.getElementById('tracker-display');
    if (trackerDisplay) {
      trackerDisplay.style.display = 'none';
    }

    const startBtn = document.getElementById('tracker-start-btn');
    const stopBtn = document.getElementById('tracker-stop-btn');
    
    if (startBtn) startBtn.style.display = 'inline-flex';
    if (stopBtn) stopBtn.style.display = 'none';
  },

  async updateSetting(key, value) {
    try {
      if (window.app && window.app.settings) {
        window.app.settings[key] = value;
        await window.electronAPI.saveSettings(window.app.settings);
      }
    } catch (error) {
      console.error('Failed to update setting:', error);
    }
  },

  // Handle game detection events from main process
  onGameDetected(gameData) {
    this.currentGame = gameData.game;
    this.updateGameInfo();
    this.updateActionButtons();
  },

  onGameStopped() {
    this.currentGame = null;
    this.updateGameInfo();
    this.updateActionButtons();
  }
}; 