const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell, dialog } = require('electron');
const path = require('path');
const Store = require('electron-store');
const { spawn } = require('child_process');
const activeWin = require('active-win');
const http = require('http');
const url = require('url');

// Load environment variables from .env file in the root directory
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// Initialize store for settings
const store = new Store();

let mainWindow;
let tray;
let pythonProcess;
let gameTrackingInterval;
let currentGame = null;
let sessionStartTime = null;
let isTracking = false;

// Game detection settings
const GAME_PROCESSES = new Set([
  // Steam games
  'steam.exe', 'steamwebhelper.exe',
  // Epic Games
  'EpicGamesLauncher.exe', 'EpicWebHelper.exe',
  // Common game engines
  'Unity.exe', 'UnrealEditor.exe', 'Godot.exe',
  // Popular games (add more as needed)
  'cs2.exe', 'dota2.exe', 'league of legends.exe', 'valorant.exe',
  'minecraft.exe', 'javaw.exe', 'bedrock_server.exe',
  'eldenring.exe', 'dark souls iii.exe', 'sekiro.exe',
  'cyberpunk2077.exe', 'witcher3.exe', 'red dead redemption 2.exe',
  'gta5.exe', 'gta v.exe', 'rocket league.exe', 'fortnite.exe',
  'apex legends.exe', 'overwatch.exe', 'overwatch2.exe',
  'world of warcraft.exe', 'wow.exe', 'final fantasy xiv.exe',
  'ffxiv.exe', 'destiny2.exe', 'destiny 2.exe'
]);

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    titleBarStyle: 'default',
    show: false
  });

  // Load the app
  mainWindow.loadFile('renderer/index.html');

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Prevent window from being closed, just hide it
  mainWindow.on('close', (event) => {
    if (!app.isQuiting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'tray-icon.png');
  const icon = nativeImage.createFromPath(iconPath);
  
  tray = new Tray(icon);
  tray.setToolTip('Gamer Cred Desktop');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show App',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
      }
    },
    {
      label: 'Current Session',
      submenu: [
        {
          label: 'Start Tracking',
          click: () => startGameTracking(),
          enabled: !isTracking
        },
        {
          label: 'Stop Tracking',
          click: () => stopGameTracking(),
          enabled: isTracking
        },
        {
          label: 'Log Session',
          click: () => logCurrentSession(),
          enabled: isTracking && currentGame
        }
      ]
    },
    {
      label: 'Quick Actions',
      submenu: [
        {
          label: 'Check Balance',
          click: () => checkBalance()
        },
        {
          label: 'View Leaderboard',
          click: () => openLeaderboard()
        },
        {
          label: 'Recent Activity',
          click: () => openRecentActivity()
        }
      ]
    },
    { type: 'separator' },
    {
      label: 'Settings',
      click: () => openSettings()
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuiting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
  
  // Handle tray click
  tray.on('click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

async function startGameTracking() {
  if (isTracking) return;
  
  isTracking = true;
  sessionStartTime = Date.now();
  
  // Start monitoring active windows
  gameTrackingInterval = setInterval(async () => {
    try {
      const activeWindow = await activeWin();
      if (activeWindow && activeWindow.owner && activeWindow.owner.name) {
        const processName = activeWindow.owner.name.toLowerCase();
        
        // Check if it's a game process
        if (GAME_PROCESSES.has(processName) || isGameProcess(processName)) {
          if (currentGame !== activeWindow.owner.name) {
            currentGame = activeWindow.owner.name;
            updateTrayTooltip();
            mainWindow.webContents.send('game-detected', {
              game: currentGame,
              startTime: sessionStartTime
            });
          }
        } else {
          if (currentGame) {
            currentGame = null;
            updateTrayTooltip();
            mainWindow.webContents.send('game-stopped');
          }
        }
      }
    } catch (error) {
      console.error('Error tracking active window:', error);
    }
  }, 5000); // Check every 5 seconds
  
  updateTrayTooltip();
  mainWindow.webContents.send('tracking-started');
}

function stopGameTracking() {
  if (!isTracking) return;
  
  isTracking = false;
  if (gameTrackingInterval) {
    clearInterval(gameTrackingInterval);
    gameTrackingInterval = null;
  }
  
  currentGame = null;
  sessionStartTime = null;
  updateTrayTooltip();
  mainWindow.webContents.send('tracking-stopped');
}

function isGameProcess(processName) {
  // Additional game detection logic
  const gameKeywords = [
    'game', 'launcher', 'client', 'steam', 'epic', 'origin', 'uplay',
    'battle.net', 'riot', 'league', 'valorant', 'minecraft', 'java',
    'unity', 'unreal', 'godot', 'cryengine', 'source', 'id tech'
  ];
  
  return gameKeywords.some(keyword => processName.includes(keyword));
}

function updateTrayTooltip() {
  if (isTracking && currentGame) {
    const duration = Math.floor((Date.now() - sessionStartTime) / 1000);
    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    const seconds = duration % 60;
    
    tray.setToolTip(`Gamer Cred - ${currentGame}\nSession: ${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
  } else if (isTracking) {
    tray.setToolTip('Gamer Cred - Tracking (No game detected)');
  } else {
    tray.setToolTip('Gamer Cred Desktop');
  }
}

async function logCurrentSession() {
  if (!isTracking || !currentGame || !sessionStartTime) return;
  
  const duration = (Date.now() - sessionStartTime) / (1000 * 60 * 60); // hours
  const hours = Math.round(duration * 10) / 10; // Round to 1 decimal place
  
  try {
    // Send to renderer to handle API call
    mainWindow.webContents.send('log-session', {
      game: currentGame,
      hours: hours
    });
    
    // Stop tracking after logging
    stopGameTracking();
  } catch (error) {
    console.error('Error logging session:', error);
    dialog.showErrorBox('Error', 'Failed to log gaming session');
  }
}

function checkBalance() {
  mainWindow.show();
  mainWindow.focus();
  mainWindow.webContents.send('navigate', 'balance');
}

function openLeaderboard() {
  mainWindow.show();
  mainWindow.focus();
  mainWindow.webContents.send('navigate', 'leaderboard');
}

function openRecentActivity() {
  mainWindow.show();
  mainWindow.focus();
  mainWindow.webContents.send('navigate', 'activity');
}

function openSettings() {
  mainWindow.show();
  mainWindow.focus();
  mainWindow.webContents.send('navigate', 'settings');
}

// IPC Handlers
ipcMain.handle('get-settings', () => {
  return store.get('settings', {
    autoTrack: false,
    notifications: true,
    startWithWindows: false,
    apiUrl: 'https://gamercred.onrender.com'
  });
});

ipcMain.handle('save-settings', (event, settings) => {
  store.set('settings', settings);
  return true;
});

ipcMain.handle('get-current-session', () => {
  if (!isTracking) return null;
  
  return {
    game: currentGame,
    startTime: sessionStartTime,
    duration: sessionStartTime ? (Date.now() - sessionStartTime) / 1000 : 0
  };
});

ipcMain.handle('start-tracking', () => {
  startGameTracking();
  return true;
});

ipcMain.handle('stop-tracking', () => {
  stopGameTracking();
  return true;
});

ipcMain.handle('log-session', async (event, sessionData) => {
  // This will be handled by the renderer process
  return true;
});

ipcMain.handle('start-oauth-login', async () => {
  try {
    console.log('Starting OAuth login process...');
    
    // Create a hidden window to handle the OAuth flow
    const authWindow = new BrowserWindow({
      width: 800,
      height: 600,
      show: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true
      }
    });
    
    // Discord OAuth URL with a custom redirect URI that we'll handle locally
    const clientId = '1344451764530708571';
    const redirectUri = 'http://localhost:3001/callback';
    const scope = 'identify email guilds';
    
    const loginUrl = `https://discord.com/oauth2/authorize?client_id=${clientId}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${encodeURIComponent(scope)}`;
    
    console.log('Loading OAuth URL:', loginUrl);
    
    // Load the OAuth URL in the hidden window
    await authWindow.loadURL(loginUrl);
    authWindow.show();
    
    // Listen for the callback URL
    authWindow.webContents.on('will-navigate', async (event, url) => {
      if (url.startsWith(redirectUri)) {
        console.log('OAuth callback received:', url);
        
        // Parse the authorization code from the URL
        const urlObj = new URL(url);
        const code = urlObj.searchParams.get('code');
        const error = urlObj.searchParams.get('error');
        
        if (error) {
          console.error('OAuth error:', error);
          authWindow.close();
          mainWindow.webContents.send('login-failed', { error });
          return;
        }
        
        if (!code) {
          console.error('No authorization code received');
          authWindow.close();
          mainWindow.webContents.send('login-failed', { error: 'No authorization code received' });
          return;
        }
        
        try {
          // Exchange the authorization code for an access token
          const tokenData = await exchangeCodeForToken(code, redirectUri);
          console.log('Token exchange successful:', tokenData);
          
          // Get user info using the access token
          const userData = await getUserInfo(tokenData.access_token);
          console.log('User data received:', userData);
          
          // Store the token and user data locally
          store.set('discord_token', tokenData.access_token);
          store.set('discord_user_id', userData.id);
          store.set('discord_username', userData.username);
          store.set('discord_avatar', userData.avatar || '');
          
          // Close the auth window
          authWindow.close();
          
          // Notify the renderer process
          mainWindow.webContents.send('login-successful', userData);
          
        } catch (error) {
          console.error('Failed to exchange code for token:', error);
          authWindow.close();
          mainWindow.webContents.send('login-failed', { error: error.message });
        }
      }
    });
    
    return { success: true };
  } catch (error) {
    console.error('Failed to start OAuth login:', error);
    return { success: false, error: error.message };
  }
});

// Function to exchange authorization code for access token
async function exchangeCodeForToken(code, redirectUri) {
  const clientId = '1344451764530708571';
  const clientSecret = process.env.DISCORD_CLIENT_SECRET;
  
  if (!clientSecret) {
    throw new Error('DISCORD_CLIENT_SECRET not found in environment variables. Please check your .env file.');
  }
  
  const data = {
    client_id: clientId,
    client_secret: clientSecret,
    grant_type: 'authorization_code',
    code: code,
    redirect_uri: redirectUri
  };
  
  const response = await fetch('https://discord.com/api/oauth2/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams(data)
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Token exchange failed: ${response.status} ${errorText}`);
  }
  
  return await response.json();
}

// Function to get user info using access token
async function getUserInfo(accessToken) {
  const response = await fetch('https://discord.com/api/users/@me', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get user info: ${response.status} ${errorText}`);
  }
  
  return await response.json();
}

// Function to get user stats from the website API
async function getUserStats(userId) {
  try {
    const response = await fetch(`https://gamercred.onrender.com/api/user-stats/${userId}`);
    if (response.ok) {
      return await response.json();
    } else {
      console.log('Failed to get user stats:', response.status);
      return null;
    }
  } catch (error) {
    console.error('Error fetching user stats:', error);
    return null;
  }
}

// Function to get user game summaries
async function getUserGameSummaries(userId) {
  try {
    const response = await fetch(`https://gamercred.onrender.com/api/user-game-summaries/${userId}`);
    if (response.ok) {
      return await response.json();
    } else {
      console.log('Failed to get user game summaries:', response.status);
      return [];
    }
  } catch (error) {
    console.error('Error fetching user game summaries:', error);
    return [];
  }
}

// Function to get leaderboard data
async function getLeaderboard() {
  try {
    const response = await fetch('https://gamercred.onrender.com/api/leaderboard');
    if (response.ok) {
      return await response.json();
    } else {
      console.log('Failed to get leaderboard:', response.status);
      return [];
    }
  } catch (error) {
    console.error('Error fetching leaderboard:', error);
    return [];
  }
}

// Function to get recent activity
async function getRecentActivity() {
  try {
    const response = await fetch('https://gamercred.onrender.com/api/recent-activity');
    if (response.ok) {
      return await response.json();
    } else {
      console.log('Failed to get recent activity:', response.status);
      return [];
    }
  } catch (error) {
    console.error('Error fetching recent activity:', error);
    return [];
  }
}

ipcMain.handle('get-stored-token', () => {
  return store.get('discord_token');
});

ipcMain.handle('logout', () => {
  store.delete('discord_token');
  store.delete('discord_user_id');
  store.delete('discord_username');
  store.delete('discord_avatar');
  return { success: true };
});

// New IPC handlers for fetching game data
ipcMain.handle('get-user-stats', async () => {
  const userId = store.get('discord_user_id');
  if (!userId) {
    return { success: false, error: 'No user ID found' };
  }
  
  const stats = await getUserStats(userId);
  return { success: true, data: stats };
});

ipcMain.handle('get-user-game-summaries', async () => {
  const userId = store.get('discord_user_id');
  if (!userId) {
    return { success: false, error: 'No user ID found' };
  }
  
  const summaries = await getUserGameSummaries(userId);
  return { success: true, data: summaries };
});

ipcMain.handle('get-leaderboard', async () => {
  const leaderboard = await getLeaderboard();
  return { success: true, data: leaderboard };
});

ipcMain.handle('get-recent-activity', async () => {
  const activity = await getRecentActivity();
  return { success: true, data: activity };
});

ipcMain.handle('check-login-status', async () => {
  try {
    console.log('Checking login status...');
    
    // Get stored token
    const token = store.get('discord_token');
    if (!token) {
      console.log('No stored token found');
      return { success: false, error: 'No stored token' };
    }
    
    // Verify the token is still valid by getting user info
    try {
      const userData = await getUserInfo(token);
      console.log('Token is valid, user data:', userData);
      
      // Update stored user data
      store.set('discord_user_id', userData.id);
      store.set('discord_username', userData.username);
      store.set('discord_avatar', userData.avatar || '');
      
      return { success: true, user: userData };
    } catch (error) {
      console.log('Token is invalid, clearing stored data');
      // Clear invalid token
      store.delete('discord_token');
      store.delete('discord_user_id');
      store.delete('discord_username');
      store.delete('discord_avatar');
      
      return { success: false, error: 'Token is invalid or expired' };
    }
  } catch (error) {
    console.error('Failed to check login status:', error);
    return { success: false, error: error.message };
  }
});

// App lifecycle
app.whenReady().then(() => {
  createWindow();
  createTray();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuiting = true;
  if (pythonProcess) {
    pythonProcess.kill();
  }
}); 