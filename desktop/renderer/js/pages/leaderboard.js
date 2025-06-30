// Leaderboard Module
window.leaderboardModule = {
  currentPeriod: 'weekly',

  async load() {
    try {
      this.setupEventListeners();
      await this.loadLeaderboard();
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
      if (window.app) {
        window.app.showNotification('Failed to load leaderboard', 'error');
      }
    }
  },

  setupEventListeners() {
    const tabButtons = document.querySelectorAll('.leaderboard-tabs .tab-btn');
    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const period = btn.dataset.period;
        this.switchPeriod(period);
      });
    });
  },

  async switchPeriod(period) {
    this.currentPeriod = period;
    
    // Update active tab
    document.querySelectorAll('.leaderboard-tabs .tab-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    document.querySelector(`[data-period="${period}"]`)?.classList.add('active');
    
    // Reload leaderboard data
    await this.loadLeaderboard();
  },

  async loadLeaderboard() {
    try {
      const leaderboardList = document.getElementById('leaderboard-list');
      const loadingElement = document.getElementById('leaderboard-loading');
      
      if (loadingElement) loadingElement.style.display = 'flex';
      if (leaderboardList) leaderboardList.style.display = 'none';

      const response = await window.app.apiCall(`/api/leaderboard?period=${this.currentPeriod}`);
      
      if (response.success && response.leaderboard) {
        this.renderLeaderboard(response.leaderboard);
      } else {
        this.showNoData();
      }
    } catch (error) {
      console.error('Failed to load leaderboard data:', error);
      this.showNoData();
    }
  },

  renderLeaderboard(leaderboard) {
    const leaderboardList = document.getElementById('leaderboard-list');
    const loadingElement = document.getElementById('leaderboard-loading');
    
    if (!leaderboardList) return;

    if (loadingElement) loadingElement.style.display = 'none';
    leaderboardList.style.display = 'block';

    if (!leaderboard || leaderboard.length === 0) {
      this.showNoData();
      return;
    }

    const leaderboardHTML = leaderboard.map((entry, index) => {
      const rank = index + 1;
      const rankClass = this.getRankClass(rank);
      
      return `
        <div class="leaderboard-item">
          <div class="leaderboard-rank ${rankClass}">${rank}</div>
          <div class="leaderboard-user">
            <div class="user-avatar-small">
              <i class="fas fa-user"></i>
            </div>
            <div class="user-name">${entry.username || `User ${entry.user_id}`}</div>
          </div>
          <div class="leaderboard-score">${entry.credits.toLocaleString()} cred</div>
        </div>
      `;
    }).join('');

    leaderboardList.innerHTML = leaderboardHTML;
  },

  getRankClass(rank) {
    if (rank === 1) return 'gold';
    if (rank === 2) return 'silver';
    if (rank === 3) return 'bronze';
    return '';
  },

  showNoData() {
    const leaderboardList = document.getElementById('leaderboard-list');
    const loadingElement = document.getElementById('leaderboard-loading');
    
    if (loadingElement) loadingElement.style.display = 'none';
    if (leaderboardList) {
      leaderboardList.style.display = 'block';
      leaderboardList.innerHTML = `
        <div class="no-data">
          <i class="fas fa-trophy"></i>
          <p>No leaderboard data available</p>
        </div>
      `;
    }
  }
}; 