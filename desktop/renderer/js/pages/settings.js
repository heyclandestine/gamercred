// Settings Module
window.settingsModule = {
  async load() {
    try {
      this.setupEventListeners();
      this.loadSettings();
      this.loadSystemInfo();
    } catch (error) {
      console.error('Failed to load settings:', error);
      if (window.app) {
        window.app.showNotification('Failed to load settings', 'error');
      }
    }
  },

  setupEventListeners() {
    // Settings checkboxes
    const startWithWindows = document.getElementById('start-with-windows');
    const minimizeToTray = document.getElementById('minimize-to-tray');
    const autoTrackSetting = document.getElementById('auto-track-setting');
    const notificationsSetting = document.getElementById('notifications-setting');

    if (startWithWindows) {
      startWithWindows.addEventListener('change', (e) => {
        this.updateSetting('startWithWindows', e.target.checked);
      });
    }

    if (minimizeToTray) {
      minimizeToTray.addEventListener('change', (e) => {
        this.updateSetting('minimizeToTray', e.target.checked);
      });
    }

    if (autoTrackSetting) {
      autoTrackSetting.addEventListener('change', (e) => {
        this.updateSetting('autoTrack', e.target.checked);
      });
    }

    if (notificationsSetting) {
      notificationsSetting.addEventListener('change', (e) => {
        this.updateSetting('notifications', e.target.checked);
      });
    }

    // API URL input
    const apiUrl = document.getElementById('api-url');
    if (apiUrl) {
      apiUrl.addEventListener('blur', (e) => {
        this.updateSetting('apiUrl', e.target.value);
      });
    }

    // Note: Login/Logout buttons are handled in app.js to avoid duplicate event listeners
  },

  loadSettings() {
    if (!window.app || !window.app.settings) return;

    const settings = window.app.settings;

    // Update checkboxes
    const startWithWindows = document.getElementById('start-with-windows');
    const minimizeToTray = document.getElementById('minimize-to-tray');
    const autoTrackSetting = document.getElementById('auto-track-setting');
    const notificationsSetting = document.getElementById('notifications-setting');
    const apiUrl = document.getElementById('api-url');

    if (startWithWindows) startWithWindows.checked = settings.startWithWindows || false;
    if (minimizeToTray) minimizeToTray.checked = settings.minimizeToTray || false;
    if (autoTrackSetting) autoTrackSetting.checked = settings.autoTrack || false;
    if (notificationsSetting) notificationsSetting.checked = settings.notifications !== false;
    if (apiUrl) apiUrl.value = settings.apiUrl || 'https://gamercred.onrender.com';

    // Update login/logout buttons
    this.updateAuthButtons();
  },

  updateAuthButtons() {
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const token = localStorage.getItem('discord_token');

    if (loginBtn) {
      loginBtn.style.display = token ? 'none' : 'inline-flex';
    }
    if (logoutBtn) {
      logoutBtn.style.display = token ? 'inline-flex' : 'none';
    }
  },

  async loadSystemInfo() {
    try {
      const platform = await window.electronAPI.getPlatform();
      const version = await window.electronAPI.getVersion();

      const platformInfo = document.getElementById('platform-info');
      const electronVersion = document.getElementById('electron-version');
      const appVersion = document.getElementById('app-version');

      if (platformInfo) {
        platformInfo.textContent = this.formatPlatform(platform);
      }
      if (electronVersion) {
        electronVersion.textContent = version;
      }
      if (appVersion) {
        appVersion.textContent = '1.0.0'; // This should come from package.json
      }
    } catch (error) {
      console.error('Failed to load system info:', error);
    }
  },

  formatPlatform(platform) {
    const platforms = {
      'win32': 'Windows',
      'darwin': 'macOS',
      'linux': 'Linux'
    };
    return platforms[platform] || platform;
  },

  async updateSetting(key, value) {
    try {
      if (window.app && window.app.settings) {
        window.app.settings[key] = value;
        await window.electronAPI.saveSettings(window.app.settings);
        
        if (window.app) {
          window.app.showNotification('Setting updated', 'success');
        }
      }
    } catch (error) {
      console.error('Failed to update setting:', error);
      if (window.app) {
        window.app.showNotification('Failed to update setting', 'error');
      }
    }
  }
}; 