// Recent Activity Module
window.recentActivityModule = {
  currentFilter: 'all',

  async load() {
    try {
      this.setupEventListeners();
      await this.loadActivity();
    } catch (error) {
      console.error('Failed to load recent activity:', error);
      if (window.app) {
        window.app.showNotification('Failed to load recent activity', 'error');
      }
    }
  },

  setupEventListeners() {
    const filterButtons = document.querySelectorAll('.activity-filters .filter-btn');
    filterButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;
        this.switchFilter(filter);
      });
    });
  },

  async switchFilter(filter) {
    this.currentFilter = filter;
    
    // Update active filter
    document.querySelectorAll('.activity-filters .filter-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    document.querySelector(`[data-filter="${filter}"]`)?.classList.add('active');
    
    // Reload activity data
    await this.loadActivity();
  },

  async loadActivity() {
    try {
      const activityList = document.getElementById('activity-list');
      const loadingElement = document.getElementById('activity-loading');
      
      if (loadingElement) loadingElement.style.display = 'flex';
      if (activityList) activityList.style.display = 'none';

      const response = await window.app.apiCall('/api/recent-activity');
      
      if (response.success && response.activity) {
        this.renderActivity(response.activity);
      } else {
        this.showNoActivity();
      }
    } catch (error) {
      console.error('Failed to load activity data:', error);
      this.showNoActivity();
    }
  },

  renderActivity(activities) {
    const activityList = document.getElementById('activity-list');
    const loadingElement = document.getElementById('activity-loading');
    
    if (!activityList) return;

    if (loadingElement) loadingElement.style.display = 'none';
    activityList.style.display = 'block';

    if (!activities || activities.length === 0) {
      this.showNoActivity();
      return;
    }

    // Filter activities based on current filter
    let filteredActivities = activities;
    if (this.currentFilter !== 'all') {
      filteredActivities = activities.filter(activity => activity.type === this.currentFilter);
    }

    const activityHTML = filteredActivities.map(activity => {
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
    const activityList = document.getElementById('activity-list');
    const loadingElement = document.getElementById('activity-loading');
    
    if (loadingElement) loadingElement.style.display = 'none';
    if (activityList) {
      activityList.style.display = 'block';
      activityList.innerHTML = `
        <div class="no-activity">
          <i class="fas fa-inbox"></i>
          <p>No recent activity</p>
        </div>
      `;
    }
  }
}; 