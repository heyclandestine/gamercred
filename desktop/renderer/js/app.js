// Main App Controller
class GamerCredDesktop {
  constructor() {
    this.currentPage = 'dashboard';
    this.settings = {};
    this.user = null;
    this.isTracking = false;
    this.currentSession = null;
    this.timerInterval = null;
    
    this.init();
  }

  async init() {
    try {
      // Load settings
      this.settings = await window.electronAPI.getSettings();
      
      // Initialize UI
      this.initNavigation();
      this.initEventListeners();
      this.initNotifications();
      
      // Load current session state
      await this.loadCurrentSession();
      
      // Load user data if logged in
      await this.loadUserData();
      
      // Load initial page
      this.loadPage(this.currentPage);
      
      // Set up electron event listeners
      this.setupElectronListeners();
      
      console.log('Gamer Cred Desktop initialized successfully');
    } catch (error) {
      console.error('Failed to initialize app:', error);
      this.showNotification('Failed to initialize app', 'error');
    }
  }

  initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        const page = item.dataset.page;
        this.navigateToPage(page);
      });
    });
  }

  initEventListeners() {
    // Header buttons
    document.getElementById('start-tracking-btn')?.addEventListener('click', () => {
      this.startTracking();
    });

    document.getElementById('log-session-btn')?.addEventListener('click', () => {
      this.showLogSessionModal();
    });

    document.getElementById('view-leaderboard-btn')?.addEventListener('click', () => {
      this.navigateToPage('leaderboard');
    });

    document.getElementById('check-balance-btn')?.addEventListener('click', () => {
      this.navigateToPage('my-stats');
    });

    // Modal events
    document.getElementById('log-session-modal-close')?.addEventListener('click', () => {
      this.hideLogSessionModal();
    });

    document.getElementById('log-session-cancel')?.addEventListener('click', () => {
      this.hideLogSessionModal();
    });

    document.getElementById('log-session-submit')?.addEventListener('click', () => {
      this.submitLogSession();
    });

    // Settings events
    document.getElementById('login-btn')?.addEventListener('click', () => {
      this.loginWithDiscord();
    });

    document.getElementById('logout-btn')?.addEventListener('click', () => {
      this.logout();
    });

    document.getElementById('check-login-btn')?.addEventListener('click', () => {
      this.checkLoginStatus();
    });

    // Form events
    document.getElementById('log-session-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submitLogSession();
    });
  }

  initNotifications() {
    this.notificationContainer = document.getElementById('notification-container');
  }

  setupElectronListeners() {
    // Game detection events
    window.electronAPI.onGameDetected((event, data) => {
      this.onGameDetected(data);
    });

    window.electronAPI.onGameStopped(() => {
      this.onGameStopped();
    });

    // Tracking events
    window.electronAPI.onTrackingStarted(() => {
      this.onTrackingStarted();
    });

    window.electronAPI.onTrackingStopped(() => {
      this.onTrackingStopped();
    });

    // Session logging
    window.electronAPI.onLogSession((event, data) => {
      this.showLogSessionModal(data);
    });

    // Navigation events
    window.electronAPI.onNavigate((event, page) => {
      this.navigateToPage(page);
    });

    // Login events
    window.electronAPI.onLoginSuccessful((event, userData) => {
      this.user = userData;
      this.updateUserDisplay();
      this.showNotification(`Welcome, ${userData.username}!`, 'success');
      
      // Load user game data after successful login
      this.loadUserGameData();
    });

    window.electronAPI.onLoginFailed((event, data) => {
      this.showNotification(`Login failed: ${data.error}`, 'error');
    });
  }

  async loadCurrentSession() {
    try {
      this.currentSession = await window.electronAPI.getCurrentSession();
      this.updateSessionDisplay();
    } catch (error) {
      console.error('Failed to load current session:', error);
    }
  }

  async loadUserData() {
    try {
      // First check if we have a stored token
      const token = await window.electronAPI.getStoredToken();
      if (token) {
        const result = await window.electronAPI.checkLoginStatus();
        if (result.success && result.user) {
          this.user = result.user;
          this.updateUserDisplay();
          
          // Load user game data
          await this.loadUserGameData();
          return;
        }
      }
      
      // If no stored token, check if user is logged in on the website
      await this.checkLoginStatus();
    } catch (error) {
      console.error('Failed to load user data:', error);
    }
  }

  async loadUserGameData() {
    try {
      console.log('Loading user game data...');
      
      // Load user stats
      console.log('Fetching user stats...');
      const statsResult = await window.electronAPI.getUserStats();
      console.log('User stats result:', statsResult);
      
      if (statsResult.success) {
        this.userStats = statsResult.data;
        console.log('User stats loaded:', this.userStats);
      } else {
        console.error('Failed to load user stats:', statsResult.error);
      }
      
      // Load user game summaries
      console.log('Fetching user game summaries...');
      const summariesResult = await window.electronAPI.getUserGameSummaries();
      console.log('User game summaries result:', summariesResult);
      
      if (summariesResult.success) {
        this.userGameSummaries = summariesResult.data;
        console.log('User game summaries loaded:', this.userGameSummaries);
      } else {
        console.error('Failed to load user game summaries:', summariesResult.error);
      }
      
      // Update UI with loaded data
      this.updateGameDataDisplay();
      
    } catch (error) {
      console.error('Failed to load user game data:', error);
    }
  }

  updateGameDataDisplay() {
    // Update dashboard with user stats
    if (this.userStats) {
      this.updateDashboardStats();
    }
    
    // Update my-stats page with game summaries
    if (this.userGameSummaries) {
      this.updateMyStatsDisplay();
    }
  }

  updateDashboardStats() {
    // Update dashboard with user stats
    if (this.userStats) {
      // Update the stat values in the dashboard
      const totalCreditsEl = document.getElementById('total-credits');
      const totalHoursEl = document.getElementById('total-hours');
      const gamesPlayedEl = document.getElementById('games-played');
      const currentRankEl = document.getElementById('current-rank');
      
      if (totalCreditsEl) totalCreditsEl.textContent = this.userStats.total_credits || 0;
      if (totalHoursEl) totalHoursEl.textContent = this.userStats.total_hours || 0;
      if (gamesPlayedEl) gamesPlayedEl.textContent = this.userStats.games_played || 0;
      if (currentRankEl) currentRankEl.textContent = this.userStats.rank || '-';
      
      console.log('Dashboard stats updated:', this.userStats);
    }
  }

  updateMyStatsDisplay() {
    // Update my-stats page with game summaries
    if (this.userGameSummaries) {
      // Update stats overview
      const statsOverviewEl = document.getElementById('stats-overview');
      if (statsOverviewEl && this.userStats) {
        statsOverviewEl.innerHTML = `
          <div class="stat-row">
            <span class="stat-label">Total Credits:</span>
            <span class="stat-value">${this.userStats.total_credits || 0}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Total Hours:</span>
            <span class="stat-value">${this.userStats.total_hours || 0}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Games Played:</span>
            <span class="stat-value">${this.userStats.games_played || 0}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Current Rank:</span>
            <span class="stat-value">${this.userStats.rank || 'Unranked'}</span>
          </div>
        `;
      }
      
      // Update top games
      const topGamesEl = document.getElementById('top-games');
      if (topGamesEl) {
        const topGames = this.userGameSummaries
          .sort((a, b) => b.total_hours - a.total_hours)
          .slice(0, 5);
        
        const gamesHtml = topGames.map(game => `
          <div class="game-item">
            <div class="game-name">${game.game_name}</div>
            <div class="game-stats">
              <span class="hours">${game.total_hours} hours</span>
              <span class="credits">${game.total_credits} credits</span>
            </div>
          </div>
        `).join('');
        
        topGamesEl.innerHTML = gamesHtml || '<p>No games played yet.</p>';
      }
      
      console.log('My stats updated:', this.userGameSummaries);
    }
  }

  async checkLoginStatus() {
    try {
      console.log('Checking login status...');
      
      // Show a loading notification
      this.showNotification('Checking login status...', 'info');
      
      const result = await window.electronAPI.checkLoginStatus();
      console.log('Login status result:', result);
      
      if (result.success && result.user) {
        this.user = result.user;
        this.updateUserDisplay();
        this.showNotification(`Welcome back, ${result.user.username}!`, 'success');
        return true;
      } else {
        console.log('Not logged in:', result.error);
        this.showNotification('Not logged in. Please login first.', 'info');
        return false;
      }
    } catch (error) {
      console.error('Failed to check login status:', error);
      this.showNotification('Failed to check login status. Please try again.', 'error');
      return false;
    }
  }

  navigateToPage(page) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.remove('active');
    });
    document.querySelector(`[data-page="${page}"]`)?.classList.add('active');

    // Update page title
    const pageTitle = document.getElementById('page-title');
    if (pageTitle) {
      pageTitle.textContent = this.getPageTitle(page);
    }

    // Load page content
    this.loadPage(page);
    this.currentPage = page;
  }

  getPageTitle(page) {
    const titles = {
      dashboard: 'Dashboard',
      'session-tracker': 'Session Tracker',
      leaderboard: 'Leaderboard',
      'my-stats': 'My Stats',
      'recent-activity': 'Recent Activity',
      games: 'Games',
      settings: 'Settings'
    };
    return titles[page] || 'Dashboard';
  }

  loadPage(page) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => {
      p.classList.remove('active');
    });

    // Show target page
    const targetPage = document.getElementById(`${page}-page`);
    if (targetPage) {
      targetPage.classList.add('active');
    }

    // Load page-specific content
    switch (page) {
      case 'dashboard':
        this.loadDashboard();
        break;
      case 'session-tracker':
        this.loadSessionTracker();
        break;
      case 'leaderboard':
        this.loadLeaderboard();
        break;
      case 'my-stats':
        this.loadMyStats();
        break;
      case 'recent-activity':
        this.loadRecentActivity();
        break;
      case 'games':
        this.loadGames();
        break;
      case 'settings':
        this.loadSettings();
        break;
    }
  }

  async startTracking() {
    try {
      await window.electronAPI.startTracking();
      this.isTracking = true;
      this.updateTrackingStatus();
      this.showNotification('Game tracking started', 'success');
    } catch (error) {
      console.error('Failed to start tracking:', error);
      this.showNotification('Failed to start tracking', 'error');
    }
  }

  async stopTracking() {
    try {
      await window.electronAPI.stopTracking();
      this.isTracking = false;
      this.currentSession = null;
      this.updateTrackingStatus();
      this.updateSessionDisplay();
      this.showNotification('Game tracking stopped', 'success');
    } catch (error) {
      console.error('Failed to stop tracking:', error);
      this.showNotification('Failed to stop tracking', 'error');
    }
  }

  onGameDetected(data) {
    this.currentSession = data;
    this.updateSessionDisplay();
    this.showNotification(`Game detected: ${data.game}`, 'success');
  }

  onGameStopped() {
    this.currentSession = null;
    this.updateSessionDisplay();
    this.showNotification('Game stopped', 'warning');
  }

  onTrackingStarted() {
    this.isTracking = true;
    this.updateTrackingStatus();
  }

  onTrackingStopped() {
    this.isTracking = false;
    this.currentSession = null;
    this.updateTrackingStatus();
    this.updateSessionDisplay();
  }

  updateTrackingStatus() {
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.tracking-status span');
    
    if (this.isTracking) {
      statusIndicator?.classList.add('tracking');
      statusText.textContent = 'Tracking';
    } else {
      statusIndicator?.classList.remove('tracking');
      statusText.textContent = 'Not tracking';
    }
  }

  updateSessionDisplay() {
    const sessionInfo = document.getElementById('session-info');
    if (!sessionInfo) return;

    if (this.currentSession && this.isTracking) {
      sessionInfo.innerHTML = `
        <div class="current-session">
          <div class="session-game">
            <i class="fas fa-gamepad"></i>
            <span>${this.currentSession.game}</span>
          </div>
          <div class="session-timer" id="session-timer">
            <span id="timer-display">00:00:00</span>
          </div>
          <button class="btn btn-success" onclick="app.logCurrentSession()">
            <i class="fas fa-save"></i>
            Log Session
          </button>
        </div>
      `;
      this.startSessionTimer();
    } else {
      sessionInfo.innerHTML = `
        <div class="no-session">
          <i class="fas fa-play-circle"></i>
          <p>No active session</p>
          <button class="btn btn-primary" onclick="app.startTracking()">
            Start Tracking
          </button>
        </div>
      `;
      this.stopSessionTimer();
    }
  }

  startSessionTimer() {
    if (this.timerInterval) return;
    
    this.timerInterval = setInterval(() => {
      if (this.currentSession && this.currentSession.startTime) {
        const duration = Math.floor((Date.now() - this.currentSession.startTime) / 1000);
        const hours = Math.floor(duration / 3600);
        const minutes = Math.floor((duration % 3600) / 60);
        const seconds = duration % 60;
        
        const timerDisplay = document.getElementById('timer-display');
        if (timerDisplay) {
          timerDisplay.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
      }
    }, 1000);
  }

  stopSessionTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  showLogSessionModal(data = null) {
    const modal = document.getElementById('log-session-modal');
    if (modal) {
      modal.classList.add('active');
      
      // Pre-fill form if data provided
      if (data) {
        document.getElementById('session-game').value = data.game || '';
        document.getElementById('session-hours').value = data.hours || '';
      }
    }
  }

  hideLogSessionModal() {
    const modal = document.getElementById('log-session-modal');
    if (modal) {
      modal.classList.remove('active');
      document.getElementById('log-session-form').reset();
    }
  }

  async submitLogSession() {
    const game = document.getElementById('session-game').value;
    const hours = parseFloat(document.getElementById('session-hours').value);

    if (!game || !hours || hours <= 0) {
      this.showNotification('Please enter valid game name and hours', 'error');
      return;
    }

    try {
      const response = await this.apiCall('/api/log-game', {
        method: 'POST',
        body: JSON.stringify({ game, hours })
      });

      if (response.success) {
        this.showNotification('Session logged successfully!', 'success');
        this.hideLogSessionModal();
        
        // Refresh dashboard
        if (this.currentPage === 'dashboard') {
          this.loadDashboard();
        }
      } else {
        this.showNotification(response.error || 'Failed to log session', 'error');
      }
    } catch (error) {
      console.error('Failed to log session:', error);
      this.showNotification('Failed to log session', 'error');
    }
  }

  async logCurrentSession() {
    if (!this.currentSession || !this.currentSession.startTime) {
      this.showNotification('No active session to log', 'error');
      return;
    }

    const duration = (Date.now() - this.currentSession.startTime) / (1000 * 60 * 60); // hours
    const hours = Math.round(duration * 10) / 10; // Round to 1 decimal place

    try {
      const response = await this.apiCall('/api/log-game', {
        method: 'POST',
        body: JSON.stringify({ 
          game: this.currentSession.game, 
          hours: hours 
        })
      });

      if (response.success) {
        this.showNotification('Session logged successfully!', 'success');
        await this.stopTracking();
        
        // Refresh dashboard
        if (this.currentPage === 'dashboard') {
          this.loadDashboard();
        }
      } else {
        this.showNotification(response.error || 'Failed to log session', 'error');
      }
    } catch (error) {
      console.error('Failed to log session:', error);
      this.showNotification('Failed to log session', 'error');
    }
  }

  async loginWithDiscord() {
    try {
      // Use IPC to start OAuth login
      const result = await window.electronAPI.startOAuthLogin();
      
      if (result.success) {
        this.showNotification('Please complete login in your browser', 'success');
      } else {
        this.showNotification('Failed to start login', 'error');
      }
    } catch (error) {
      console.error('Failed to initiate login:', error);
      this.showNotification('Failed to initiate login', 'error');
    }
  }

  async logout() {
    try {
      await window.electronAPI.logout();
      this.user = null;
      this.updateUserDisplay();
      this.showNotification('Logged out successfully', 'success');
    } catch (error) {
      console.error('Failed to logout:', error);
      this.showNotification('Failed to logout', 'error');
    }
  }

  updateUserDisplay() {
    const username = document.querySelector('.username');
    const userStatus = document.querySelector('.user-status');
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');

    if (this.user) {
      username.textContent = this.user.username;
      userStatus.textContent = 'Logged in';
      loginBtn.style.display = 'none';
      logoutBtn.style.display = 'inline-flex';
    } else {
      username.textContent = 'Not logged in';
      userStatus.textContent = 'Click to login';
      loginBtn.style.display = 'inline-flex';
      logoutBtn.style.display = 'none';
    }
  }

  showNotification(message, type = 'info') {
    if (!this.notificationContainer) return;

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    this.notificationContainer.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 5000);
  }

  async apiCall(endpoint, options = {}) {
    const baseUrl = this.settings.apiUrl || 'https://gamercred.onrender.com';
    const token = await window.electronAPI.getStoredToken();
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      }
    };

    try {
      const response = await fetch(`${baseUrl}${endpoint}`, {
        ...defaultOptions,
        ...options
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API call failed:', error);
      throw error;
    }
  }

  // Page loading methods (to be implemented in separate files)
  loadDashboard() {
    // Will be implemented in dashboard.js
    if (window.dashboardModule) {
      window.dashboardModule.load();
    }
  }

  loadSessionTracker() {
    // Will be implemented in session-tracker.js
    if (window.sessionTrackerModule) {
      window.sessionTrackerModule.load();
    }
  }

  loadLeaderboard() {
    // Will be implemented in leaderboard.js
    if (window.leaderboardModule) {
      window.leaderboardModule.load();
    }
  }

  loadMyStats() {
    // Will be implemented in my-stats.js
    if (window.myStatsModule) {
      window.myStatsModule.load();
    }
  }

  loadRecentActivity() {
    // Will be implemented in recent-activity.js
    if (window.recentActivityModule) {
      window.recentActivityModule.load();
    }
  }

  loadGames() {
    // Will be implemented in games.js
    if (window.gamesModule) {
      window.gamesModule.load();
    }
  }

  loadSettings() {
    // Will be implemented in settings.js
    if (window.settingsModule) {
      window.settingsModule.load();
    }
  }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.app = new GamerCredDesktop();
}); 