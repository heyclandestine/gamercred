// My Stats Module
window.myStatsModule = {
  async load() {
    try {
      await this.loadUserProfile();
      await this.loadStats();
    } catch (error) {
      console.error('Failed to load my stats:', error);
      if (window.app) {
        window.app.showNotification('Failed to load user stats', 'error');
      }
    }
  },

  async loadUserProfile() {
    try {
      const token = localStorage.getItem('discord_token');
      if (!token) {
        this.showLoginPrompt();
        return;
      }

      const userData = await window.app.apiCall('/api/user');
      if (userData.success && userData.user) {
        this.renderUserProfile(userData.user);
      } else {
        this.showLoginPrompt();
      }
    } catch (error) {
      console.error('Failed to load user profile:', error);
      this.showLoginPrompt();
    }
  },

  renderUserProfile(user) {
    const userProfile = document.getElementById('user-profile');
    if (!userProfile) return;

    userProfile.innerHTML = `
      <div class="profile-info">
        <div class="profile-avatar">
          <img src="${user.avatar_url || '/assets/default-avatar.png'}" alt="${user.username}" onerror="this.src='/assets/default-avatar.png'">
        </div>
        <div class="profile-details">
          <h3>${user.username}</h3>
          <p>Discord ID: ${user.id}</p>
        </div>
      </div>
    `;
  },

  showLoginPrompt() {
    const userProfile = document.getElementById('user-profile');
    if (userProfile) {
      userProfile.innerHTML = `
        <div class="login-prompt">
          <i class="fas fa-user-circle"></i>
          <p>Please log in to view your stats</p>
          <button class="btn btn-primary" onclick="app.loginWithDiscord()">
            <i class="fab fa-discord"></i>
            Login with Discord
          </button>
        </div>
      `;
    }
  },

  async loadStats() {
    try {
      const token = localStorage.getItem('discord_token');
      if (!token) {
        this.showStatsPlaceholder();
        return;
      }

      const userData = await window.app.apiCall('/api/user');
      if (userData.success && userData.user) {
        await this.loadOverviewStats(userData.user.id);
        await this.loadTopGames(userData.user.id);
        await this.loadRecentSessions(userData.user.id);
      } else {
        this.showStatsPlaceholder();
      }
    } catch (error) {
      console.error('Failed to load stats:', error);
      this.showStatsPlaceholder();
    }
  },

  async loadOverviewStats(userId) {
    try {
      const stats = await window.app.apiCall(`/api/user-stats/${userId}`);
      if (stats.success) {
        this.renderOverviewStats(stats.stats);
      }
    } catch (error) {
      console.error('Failed to load overview stats:', error);
    }
  },

  renderOverviewStats(stats) {
    const overviewContainer = document.getElementById('stats-overview');
    if (!overviewContainer) return;

    overviewContainer.innerHTML = `
      <div class="stat-item">
        <div class="stat-value">${stats.total_credits?.toLocaleString() || '0'}</div>
        <div class="stat-label">Total Credits</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${stats.total_hours?.toLocaleString() || '0'}</div>
        <div class="stat-label">Total Hours</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${stats.games_played || '0'}</div>
        <div class="stat-label">Games Played</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${stats.current_rank || '-'}</div>
        <div class="stat-label">Current Rank</div>
      </div>
    `;
  },

  async loadTopGames(userId) {
    try {
      const games = await window.app.apiCall(`/api/user-game-summaries/${userId}`);
      if (games.success && games.games) {
        this.renderTopGames(games.games.slice(0, 5));
      }
    } catch (error) {
      console.error('Failed to load top games:', error);
    }
  },

  renderTopGames(games) {
    const topGamesContainer = document.getElementById('top-games');
    if (!topGamesContainer) return;

    if (!games || games.length === 0) {
      topGamesContainer.innerHTML = `
        <div class="no-data">
          <p>No games played yet</p>
        </div>
      `;
      return;
    }

    const gamesHTML = games.map(game => `
      <div class="game-stat-item">
        <div class="game-stat-icon">
          <i class="fas fa-gamepad"></i>
        </div>
        <div class="game-stat-info">
          <div class="game-stat-name">${game.game_name}</div>
          <div class="game-stat-hours">${game.total_hours?.toFixed(1) || '0'} hours</div>
        </div>
        <div class="game-stat-score">${game.total_credits?.toFixed(0) || '0'} cred</div>
      </div>
    `).join('');

    topGamesContainer.innerHTML = gamesHTML;
  },

  async loadRecentSessions(userId) {
    try {
      const sessions = await window.app.apiCall(`/api/user-stats/${userId}/history`);
      if (sessions.success && sessions.sessions) {
        this.renderRecentSessions(sessions.sessions.slice(0, 5));
      }
    } catch (error) {
      console.error('Failed to load recent sessions:', error);
    }
  },

  renderRecentSessions(sessions) {
    const sessionsContainer = document.getElementById('recent-sessions');
    if (!sessionsContainer) return;

    if (!sessions || sessions.length === 0) {
      sessionsContainer.innerHTML = `
        <div class="no-data">
          <p>No recent sessions</p>
        </div>
      `;
      return;
    }

    const sessionsHTML = sessions.map(session => `
      <div class="session-item">
        <div class="session-game">${session.game_name}</div>
        <div class="session-details">
          <div class="session-hours">${session.hours} hours</div>
          <div class="session-time">${this.formatTime(session.timestamp)}</div>
        </div>
        <div class="session-credits">+${session.credits_earned} cred</div>
      </div>
    `).join('');

    sessionsContainer.innerHTML = sessionsHTML;
  },

  formatTime(timestamp) {
    if (!timestamp) return 'Unknown time';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  },

  showStatsPlaceholder() {
    const containers = ['stats-overview', 'top-games', 'recent-sessions'];
    containers.forEach(id => {
      const container = document.getElementById(id);
      if (container) {
        container.innerHTML = `
          <div class="no-data">
            <p>Please log in to view stats</p>
          </div>
        `;
      }
    });
  }
}; 