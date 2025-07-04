// Game Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // Check authentication status
  fetch('/api/user')
    .then(response => {
      if (response.ok) {
        return response.json();
      }
      throw new Error('Not authenticated');
    })
    .then(user => {
      const authContainer = document.getElementById('auth-container');
      authContainer.innerHTML = `
        <a href="/pages/user.html?user=${user.id}" class="user-profile">
          <img src="${user.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : 'https://cdn.discordapp.com/embed/avatars/0.png'}" 
               alt="${user.username}" 
               class="user-avatar">
          <span class="user-name">${user.username}</span>
        </a>
        <a href="/logout" class="logout-button" title="Logout">
          <i class="fas fa-sign-out-alt"></i>
        </a>
      `;

      // Show user stats section and fetch user's game stats
      const userStatsSection = document.getElementById('userGameStats');
      userStatsSection.style.display = 'block';
      
      // Get game name from URL
      const urlParams = new URLSearchParams(window.location.search);
      const gameName = urlParams.get('game');
      
      // Fetch user's stats for this game
      fetch(`/api/user-stats/${user.id}/game?name=${encodeURIComponent(gameName)}`)
        .then(response => response.json())
        .then(data => {
          const loadingSpinner = userStatsSection.querySelector('.loading-spinner');
          const statsContainer = userStatsSection.querySelector('.user-stats-grid');
          
          if (data.error) {
            loadingSpinner.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.error}`;
            return;
          }
          
          // Update stats
          document.getElementById('userHours').textContent = formatNumber(data.total_hours || 0);
          document.getElementById('userCredits').textContent = formatNumber(data.total_credits || 0);
          document.getElementById('userSessions').textContent = formatNumber(data.total_sessions || 0);
          document.getElementById('firstPlayed').textContent = data.first_played ? new Date(data.first_played).toLocaleDateString() : 'Never';
          document.getElementById('lastPlayed').textContent = data.last_played ? new Date(data.last_played).toLocaleDateString() : 'Never';
          
          // Show stats container and hide loading spinner
          loadingSpinner.style.display = 'none';
          statsContainer.style.display = 'flex';
          userStatsSection.querySelector('.user-stats-header').style.display = 'flex';
        })
        .catch(error => {
          console.error('Error fetching user game stats:', error);
          const loadingSpinner = userStatsSection.querySelector('.loading-spinner');
          loadingSpinner.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading your stats';
        });
    })
    .catch(() => {
      // User is not authenticated, keep the login button
      const authContainer = document.getElementById('auth-container');
      authContainer.innerHTML = `
        <a href="/login" class="auth-button login-button">
          <i class="fab fa-discord"></i>
          Login with Discord
        </a>
      `;
    });

  // Get game name from URL
  const urlParams = new URLSearchParams(window.location.search);
  const gameName = urlParams.get('game');
  if (!gameName) {
    showError('No game specified');
    return;
  }

  // Update page title
  document.title = `${gameName} - Gamer Cred`;

  // Fetch game data
  fetch(`/api/game?name=${encodeURIComponent(gameName)}`)
    .then(response => {
      return response.json();
    })
    .then(data => {
      if (data.error) {
        showError(data.error);
        return;
      }
      updateGameInfo(data);
    })
    .catch(error => {
      console.error('Error fetching game data:', error);
      showError('Failed to load game information');
    });

  // Fetch current players
  fetch(`/api/game/players?name=${encodeURIComponent(gameName)}`)
    .then(response => response.json())
    .then(data => {
      const playersList = document.querySelector('.players-list');
      const loadingSpinner = document.querySelector('.game-playing .loading-spinner');
      
      if (data.error) {
        playersList.innerHTML = `<li>Error loading players: ${data.error}</li>`;
      } else if (data.length === 0) {
        playersList.innerHTML = '<li>No one is currently playing this game</li>';
      } else {
        playersList.innerHTML = data.map(player => `
          <li>
            <img class="avatar-sm" src="${player.avatar_url}" alt="${player.username}">
            <a class="user-link" href="/pages/user.html?user=${player.user_id}">${player.username}</a>
          </li>
        `).join('');
      }
      
      loadingSpinner.style.display = 'none';
      playersList.style.display = 'flex';
    })
    .catch(error => {
      console.error('Error fetching players:', error);
      document.querySelector('.game-playing .loading-spinner').style.display = 'none';
      document.querySelector('.players-list').innerHTML = '<li>Error loading players</li>';
      document.querySelector('.players-list').style.display = 'flex';
    });

  // Fetch recent activity
  fetch(`/api/game/activity?name=${encodeURIComponent(gameName)}&limit=15`)
    .then(response => response.json())
    .then(data => {
      const activityList = document.querySelector('.activity-list');
      const loadingSpinner = document.querySelector('.game-activity .loading-spinner');
      
      if (data.error) {
        activityList.innerHTML = `<li>Error loading activity: ${data.error}</li>`;
      } else if (data.length === 0) {
        activityList.innerHTML = '<li>No recent activity</li>';
      } else {
        activityList.innerHTML = data.map(activity => `
          <li>
            <img class="avatar-sm" src="${activity.avatar_url}" alt="${activity.username}">
            <div class="activity-details">
              <a class="user-link" href="/pages/user.html?user=${String(activity.user_id)}">${activity.username}</a>
              <span class="activity-text">played for ${formatHours(activity.hours)}</span>
            </div>
            <span class="activity-time">${formatTimeAgo(activity.timestamp)}</span>
          </li>
        `).join('');
      }
      
      loadingSpinner.style.display = 'none';
      activityList.style.display = 'grid';
    })
    .catch(error => {
      console.error('Error fetching activity:', error);
      document.querySelector('.game-activity .loading-spinner').style.display = 'none';
      document.querySelector('.activity-list').innerHTML = '<li>Error loading activity</li>';
      document.querySelector('.activity-list').style.display = 'grid';
    });
});

function updateGameInfo(game) {
  // Update page title with game name
  document.title = `${game.name} - Gamer Cred`;

  // Update game title
  document.getElementById('gameTitle').textContent = game.name;

  // Update game description
  const descriptionElement = document.getElementById('gameDescription');
  const moreButton = document.querySelector('.more-button');
  const lessButton = document.querySelector('.less-button');
  
  if (game.description) {
    descriptionElement.textContent = game.description;
    
    // Check if description is truncated and show/hide buttons accordingly
    setTimeout(() => {
      const isTruncated = descriptionElement.scrollHeight > descriptionElement.clientHeight;
      
      if (isTruncated) {
        moreButton.style.display = 'inline-block';
        lessButton.style.display = 'none';
      } else {
        moreButton.style.display = 'none';
        lessButton.style.display = 'none';
      }
    }, 100); // Small delay to ensure content is rendered
  } else {
    descriptionElement.textContent = 'No description available.';
    moreButton.style.display = 'none';
    lessButton.style.display = 'none';
  }

  // Update game stats
  document.getElementById('totalHours').textContent = formatNumber(game.total_hours || 0);
  document.getElementById('uniquePlayers').textContent = formatNumber(game.unique_players || 0);
  document.getElementById('creditsPerHour').textContent = formatNumber(game.credits_per_hour || 0);
  document.getElementById('releaseDate').textContent = game.release_date ? new Date(game.release_date).toLocaleDateString() : 'N/A';

  // Update half-life information if available
  const halfLifeElement = document.getElementById('halfLife');
  if (halfLifeElement) {
    if (game.half_life_hours) {
      halfLifeElement.textContent = `${game.half_life_hours}h`;
      halfLifeElement.style.display = 'block';
    } else {
      halfLifeElement.textContent = 'None';
      halfLifeElement.style.display = 'block';
    }
  }

  // Update game cover
  const coverElement = document.getElementById('gameCover');
  if (game.box_art_url) {
    if (game.box_art_url.endsWith('.webm')) {
      // Create video element for webm files
      const video = document.createElement('video');
      video.src = game.box_art_url;
      video.autoplay = true;
      video.loop = true;
      video.muted = true;
      video.playsInline = true;
      video.className = 'game-cover';
      video.alt = game.name;
      coverElement.parentNode.replaceChild(video, coverElement);
    } else {
      // Use image for non-webm files
      if (coverElement.tagName === 'VIDEO') {
        const img = document.createElement('img');
        img.id = 'gameCover';
        img.className = 'game-cover';
        img.alt = game.name;
        coverElement.parentNode.replaceChild(img, coverElement);
      }
      coverElement.src = game.box_art_url;
      coverElement.onerror = function() {
        this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
      };
    }
  } else {
    coverElement.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
  }
  coverElement.alt = game.name;

  // Update Backloggd link
  const backloggdLink = document.getElementById('backloggdLink');
  if (game.backloggd_url) {
    backloggdLink.href = game.backloggd_url;
    backloggdLink.style.display = 'inline-block';
  } else {
    backloggdLink.style.display = 'none';
  }
}

function formatNumber(num) {
  return num.toLocaleString();
}

function formatHours(hours) {
  return hours.toFixed(1) + 'h';
}

function formatTimeAgo(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (minutes < 60) {
    return `${minutes}m ago`;
  } else if (hours < 24) {
    return `${hours}h ago`;
  } else {
    return `${days}d ago`;
  }
}

function showError(message) {
  const main = document.querySelector('main');
  main.innerHTML = `
    <div class="error-message">
      <h2>Error</h2>
      <p>${message}</p>
      <a href="/" class="back-link">&larr; Back to Home</a>
    </div>
  `;
}

// Add event listeners for More/Less buttons
document.addEventListener('DOMContentLoaded', function() {
  const moreButton = document.querySelector('.more-button');
  const lessButton = document.querySelector('.less-button');
  const descriptionElement = document.getElementById('gameDescription');

  if (moreButton && lessButton && descriptionElement) {
    moreButton.addEventListener('click', function() {
      descriptionElement.style.maxHeight = 'none';
      descriptionElement.style.overflow = 'visible';
      moreButton.style.display = 'none';
      lessButton.style.display = 'inline-block';
    });

    lessButton.addEventListener('click', function() {
      descriptionElement.style.maxHeight = '200px';
      descriptionElement.style.overflow = 'hidden';
      moreButton.style.display = 'inline-block';
      lessButton.style.display = 'none';
    });
  }
}); 