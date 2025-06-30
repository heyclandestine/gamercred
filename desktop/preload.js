const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Settings
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
  
  // Session tracking
  getCurrentSession: () => ipcRenderer.invoke('get-current-session'),
  startTracking: () => ipcRenderer.invoke('start-tracking'),
  stopTracking: () => ipcRenderer.invoke('stop-tracking'),
  logSession: (sessionData) => ipcRenderer.invoke('log-session', sessionData),
  
  // Event listeners
  onGameDetected: (callback) => ipcRenderer.on('game-detected', callback),
  onGameStopped: (callback) => ipcRenderer.on('game-stopped', callback),
  onTrackingStarted: (callback) => ipcRenderer.on('tracking-started', callback),
  onTrackingStopped: (callback) => ipcRenderer.on('tracking-stopped', callback),
  onLogSession: (callback) => ipcRenderer.on('log-session', callback),
  onNavigate: (callback) => ipcRenderer.on('navigate', callback),
  onLoginSuccessful: (callback) => ipcRenderer.on('login-successful', callback),
  onLoginFailed: (callback) => ipcRenderer.on('login-failed', callback),
  
  // Remove event listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
  
  // System info
  getPlatform: () => process.platform,
  getVersion: () => process.versions.electron,
  
  // OAuth authentication
  startOAuthLogin: () => ipcRenderer.invoke('start-oauth-login'),
  getStoredToken: () => ipcRenderer.invoke('get-stored-token'),
  logout: () => ipcRenderer.invoke('logout'),
  checkLoginStatus: () => ipcRenderer.invoke('check-login-status'),
  
  // Game data API
  getUserStats: () => ipcRenderer.invoke('get-user-stats'),
  getUserGameSummaries: () => ipcRenderer.invoke('get-user-game-summaries'),
  getLeaderboard: () => ipcRenderer.invoke('get-leaderboard'),
  getRecentActivity: () => ipcRenderer.invoke('get-recent-activity'),
  
  // Settings
  updateSetting: (key, value) => ipcRenderer.invoke('update-setting', key, value)
}); 