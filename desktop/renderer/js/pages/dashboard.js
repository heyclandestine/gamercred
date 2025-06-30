// Dashboard Module
window.dashboardModule = {
  async load() {
    try {
      await this.loadQuickStats();
      await this.loadRecentActivity();
      this.setupEventListeners();
    } catch (error) {
      console.error('Failed to load dashboard:', error);
      if (window.app) {
        window.app.showNotification('Failed to load dashboard data', 'error');
      }
    }
  },

  setupEventListeners() {
    // Refresh button (if added later)
    const refreshBtn = document.getElementById('refresh-dashboard');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        this.load();
      });
    }
  },

  async loadQuickStats() {
    try {
      const statsContainer = document.getElementById('total-credits');
      if (!statsContainer) return;

      // Show loading state
      this.showStatsLoading();

      // Get user stats if logged in
      const token = localStorage.getItem('discord_token');
      if (!token) {
        this.showStatsPlaceholder();
        return;
      }

      const userData = await window.app.apiCall('/api/user');
      if (userData.success && userData.user) {
        const stats = await this.getUserStats(userData.user.id);
        this.updateQuickStats(stats);
      } else {
        this.showStatsPlaceholder();
      }
    } catch (error) {
      console.error('Failed to load quick stats:', error);
      this.showStatsPlaceholder();
    }
  },

  async getUserStats(userId) {
    try {
      const [overallStats, leaderboardData] = await Promise.all([
        window.app.apiCall(`/api/user-stats/${userId}`),
        window.app.apiCall('/api/leaderboard')
      ]);

      const stats = {
        totalCredits: 0,
        totalHours: 0,
        gamesPlayed: 0,
        currentRank: '-'
      };

      if (overallStats.success) {
        stats.totalCredits = overallStats.stats.total_credits || 0;
        stats.totalHours = overallStats.stats.total_hours || 0;
        stats.gamesPlayed = overallStats.stats.games_played || 0;
      }

      if (leaderboardData.success && leaderboardData.leaderboard) {
        const userRank = leaderboardData.leaderboard.findIndex(
          entry => entry.user_id === userId
        );
        if (userRank !== -1) {
          stats.currentRank = userRank + 1;
        }
      }

      return stats;
    } catch (error) {
      console.error('Failed to get user stats:', error);
      return {
        totalCredits: 0,
        totalHours: 0,
        gamesPlayed: 0,
        currentRank: '-'
      };
    }
  },

  showStatsLoading() {
    const statsElements = ['total-credits', 'total-hours', 'games-played', 'current-rank'];
    statsElements.forEach(id => {
      const element = document.getElementById(id);
      if (element) {
        element.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      }
    });
  },

  showStatsPlaceholder() {
    const statsElements = ['total-credits', 'total-hours', 'games-played', 'current-rank'];
    statsElements.forEach(id => {
      const element = document.getElementById(id);
      if (element) {
        element.textContent = '-';
      }
    });
  },

  updateQuickStats(stats) {
    const totalCredits = document.getElementById('total-credits');
    const totalHours = document.getElementById('total-hours');
    const gamesPlayed = document.getElementById('games-played');
    const currentRank = document.getElementById('current-rank');

    if (totalCredits) totalCredits.textContent = stats.totalCredits.toLocaleString();
    if (totalHours) totalHours.textContent = stats.totalHours.toLocaleString();
    if (gamesPlayed) totalGamesPlayed.textContent = stats.gamesPlayed.toLocaleString();
    if (currentRank) currentRank.textContent = stats.currentRank;
  },

  async loadRecentActivity() {
    try {
      const activityList = document.getElementById('recent-activity-list');
      if (!activityList) return;

      // Show loading state
      activityList.innerHTML = `
        <div class="loading">
          <i class="fas fa-spinner fa-spin"></i>
          Loading recent activity...
        </div>
      `;

      const activityData = await window.app.apiCall('/api/recent-activity');
      
      if (activityData.success && activityData.activity) {
        this.renderRecentActivity(activityData.activity);
      } else {
        this.showNoActivity();
      }
    } catch (error) {
      console.error('Failed to load recent activity:', error);
      this.showNoActivity();
    }
  },

  renderRecentActivity(activities) {
    const activityList = document.getElementById('recent-activity-list');
    if (!activityList) return;

    if (!activities || activities.length === 0) {
      this.showNoActivity();
      return;
    }

    const activityHTML = activities.slice(0, 5).map(activity => {
      const icon = this.getActivityIcon(activity.type);
      const title = this.getActivityTitle(activity);
      const time = this.formatTime(activity.timestamp);
      
      return `
        <div class="activity-item">
          <div class="activity-icon">
            <i class="${icon}"></i>
          </div>
          <div class="activity-content">
            <div class="activity-title">${title}</div>
            <div class="activity-time">${time}</div>
          </div>
        </div>
      `;
    }).join('');

    activityList.innerHTML = activityHTML;
  },

  getActivityIcon(type) {
    const icons = {
      'session': 'fas fa-gamepad',
      'bonus': 'fas fa-gift',
      'achievement': 'fas fa-trophy',
      'default': 'fas fa-circle'
    };
    return icons[type] || icons.default;
  },

  getActivityTitle(activity) {
    switch (activity.type) {
      case 'session':
        return `${activity.username} logged ${activity.hours}h of ${activity.game}`;
      case 'bonus':
        return `${activity.username} received ${activity.credits} bonus credits`;
      case 'achievement':
        return `${activity.username} unlocked ${activity.achievement}`;
      default:
        return activity.description || 'Activity';
    }
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

  showNoActivity() {
    const activityList = document.getElementById('recent-activity-list');
    if (activityList) {
      activityList.innerHTML = `
        <div class="no-activity">
          <i class="fas fa-inbox"></i>
          <p>No recent activity</p>
        </div>
      `;
    }
  }
}; 