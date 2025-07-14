// Home Page JavaScript

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
        <a href="/pages/preferences.html" class="preferences-button" title="Preferences">
          <i class="fas fa-cog"></i>
        </a>
        <a href="/logout" class="logout-button" title="Logout">
          <i class="fas fa-sign-out-alt"></i>
        </a>
      `;
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

  // Existing tab switching logic
  const tabContainers = document.querySelectorAll('.leaderboard-tabs, .popular-tabs');

  tabContainers.forEach(container => {
      const tabButtons = container.querySelectorAll('.tab-btn');
      // Find the content container for this set of tabs
      const contentContainer = container.nextElementSibling; // Assuming content immediately follows the buttons

      tabButtons.forEach(button => {
          button.addEventListener('click', function() {
              const tabId = this.getAttribute('data-tab');
              const parentSection = this.closest('section'); // Get the parent section

              // Determine which section this tab belongs to and fetch data accordingly
              if (parentSection.classList.contains('leaderboard')) {
                  // Leaderboard tabs
                  const timeframe = tabId; // Tab ID is the timeframe directly (weekly, monthly, alltime)
                   // Deactivate all buttons in this container
                  container.querySelectorAll('.tab-btn').forEach(btn => {
                      btn.classList.remove('active');
                  });
                   // Activate the clicked button
                  this.classList.add('active');

                   // Hide all content divs in this section and show the selected one
                   parentSection.querySelectorAll('.tab-content').forEach(content => {
                       content.style.display = 'none';
                   });
                   document.getElementById(tabId).style.display = 'block';

                   fetchLeaderboardData(timeframe); // Fetch data on click

              } else if (parentSection.classList.contains('most-popular')) {
                  // Most Popular tabs
                  // Extract timeframe from tab ID (e.g., 'popular-weekly' -> 'weekly')
                  const timeframe = tabId.replace('popular-', '');

                   // Deactivate all buttons in this container
                  container.querySelectorAll('.tab-btn').forEach(btn => {
                      btn.classList.remove('active');
                  });
                   // Activate the clicked button
                  this.classList.add('active');

                   // Hide all content divs in this section and show the selected one
                   parentSection.querySelectorAll('.tab-content').forEach(content => {
                       content.style.display = 'none';
                   });
                   document.getElementById(tabId).style.display = 'block';

                   fetchPopularGames(timeframe); // Fetch data on click
              }
          });
      });
  });

  // Initial display of active tabs
   document.querySelectorAll('.tab-content').forEach(content => {
       content.style.display = 'none';
   });
  document.querySelectorAll('.tab-btn.active').forEach(activeButton => {
      const tabId = activeButton.getAttribute('data-tab');
      const tabContent = document.getElementById(tabId);
      if (tabContent) {
          tabContent.style.display = 'block';
          // Trigger initial fetch for the active tabs
          if (activeButton.closest('.leaderboard-tabs')) {
              fetchLeaderboardData(tabId);
          } else if (activeButton.closest('.popular-tabs')) {
              // Extract timeframe from popular tab ID (e.g., 'popular-weekly' -> 'weekly')
              const timeframe = tabId.replace('popular-', '');
              fetchPopularGames(timeframe);
          }
      }
  });

  // Function to fetch and display leaderboard data for a specific timeframe
  // Helper function to format numbers with commas
  function formatNumberWithCommas(number) {
     return number.toLocaleString();
  }

  // Function to show loading state
  function setLoadingState(element, isLoading) {
    if (isLoading) {
      element.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
    }
  }

  // Function to create loading placeholders
  function createLoadingPlaceholders(count) {
    const placeholders = [];
    for (let i = 0; i < count; i++) {
      const placeholder = document.createElement('li');
      placeholder.className = 'loading-placeholder';
      placeholder.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Loading...`;
      placeholders.push(placeholder);
    }
    return placeholders;
  }

  function fetchPopularGames(timeframe) {
    const popularList = document.querySelector(`#popular-${timeframe} ol`);
    if (!popularList) return;

    // Try to show cached data instantly
    const cacheKey = `popular_${timeframe}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        const data = JSON.parse(cached);
        popularList.innerHTML = '';
        if (data && data.length > 0) {
          data.forEach((game, index) => {
            const listItem = document.createElement('li');
            
            let mediaElement;
            if (game.box_art_url && game.box_art_url.endsWith('.webm')) {
                mediaElement = document.createElement('video');
                mediaElement.src = game.box_art_url;
                mediaElement.autoplay = true;
                mediaElement.loop = true;
                mediaElement.muted = true;
                mediaElement.playsInline = true;
            } else {
                mediaElement = document.createElement('img');
                mediaElement.src = game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
                mediaElement.onerror = function() {
                    this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
                };
            }
            mediaElement.className = 'game-cover-sm';
            mediaElement.alt = game.name;

            listItem.innerHTML = `
              <span class="rank">${index + 1}</span>
              <div class="popular-game-row">
                <a class="game-link" href="/pages/game.html?game=${encodeURIComponent(game.name)}">${game.name}</a>
                <span class="hours">${formatNumberWithCommas(game.total_hours || 0)} hrs</span>
              </div>
            `;
            
            listItem.insertBefore(mediaElement, listItem.firstChild);
            popularList.appendChild(listItem);
          });
        } else {
          popularList.innerHTML = '<li>No game data available.</li>';
        }
      } catch (e) {}
    } else {
      // Show loading state if no cache
      popularList.innerHTML = '';
      const loadingPlaceholders = createLoadingPlaceholders(5);
      loadingPlaceholders.forEach(placeholder => popularList.appendChild(placeholder));
    }

    // Always fetch fresh data in the background
    fetch(`/api/popular-games?timeframe=${timeframe}`)
      .then(response => response.json())
      .then(data => {
        popularList.innerHTML = '';
        if (data && data.length > 0) {
          data.forEach((game, index) => {
            const listItem = document.createElement('li');
            
            let mediaElement;
            if (game.box_art_url && game.box_art_url.endsWith('.webm')) {
                mediaElement = document.createElement('video');
                mediaElement.src = game.box_art_url;
                mediaElement.autoplay = true;
                mediaElement.loop = true;
                mediaElement.muted = true;
                mediaElement.playsInline = true;
            } else {
                mediaElement = document.createElement('img');
                mediaElement.src = game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
                mediaElement.onerror = function() {
                    this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
                };
            }
            mediaElement.className = 'game-cover-sm';
            mediaElement.alt = game.name;

            listItem.innerHTML = `
              <span class="rank">${index + 1}</span>
              <div class="popular-game-row">
                <a class="game-link" href="/pages/game.html?game=${encodeURIComponent(game.name)}">${game.name}</a>
                <span class="hours">${formatNumberWithCommas(game.total_hours || 0)} hrs</span>
              </div>
            `;
            
            listItem.insertBefore(mediaElement, listItem.firstChild);
            popularList.appendChild(listItem);
          });
          localStorage.setItem(cacheKey, JSON.stringify(data));
        } else {
          popularList.innerHTML = '<li>No game data available.</li>';
          localStorage.removeItem(cacheKey);
        }
      })
      .catch(error => {
        console.error(`Error fetching ${timeframe} popular games data:`, error);
        popularList.innerHTML = '<li>Error loading game data.</li>';
      });
  }

  function fetchLeaderboardData(timeframe) {
    const leaderboardList = document.querySelector(`#${timeframe} ol`);
    if (!leaderboardList) return;

    // Try to show cached data instantly
    const cacheKey = `leaderboard_${timeframe}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        const data = JSON.parse(cached);
        leaderboardList.innerHTML = '';
        if (data && data.length > 0) {
          data.forEach((player, index) => {
            const listItem = document.createElement('li');
            listItem.innerHTML = `
              <span class="rank">${index + 1}</span>
              <img class="avatar" src="${player.avatar_url || 'https://www.gravatar.com/avatar/?d=mp&s=50'}" alt="${player.username}">
              <a class="user-link" href="/pages/user.html?user=${player.user_id}">${player.username}</a>
              <span class="score">${formatNumberWithCommas(player.total_credits || 0)} cred</span>
            `;
            leaderboardList.appendChild(listItem);
          });
        } else {
          leaderboardList.innerHTML = '<li>No leaderboard data available.</li>';
        }
      } catch (e) {}
    } else {
      // Show loading state if no cache
      leaderboardList.innerHTML = '';
      const loadingPlaceholders = createLoadingPlaceholders(5);
      loadingPlaceholders.forEach(placeholder => leaderboardList.appendChild(placeholder));
    }

    // Always fetch fresh data in the background
    fetch(`/api/leaderboard?timeframe=${timeframe}`)
      .then(response => response.json())
      .then(data => {
        leaderboardList.innerHTML = '';
        if (data && data.length > 0) {
          data.forEach((player, index) => {
            const listItem = document.createElement('li');
            listItem.innerHTML = `
              <span class="rank">${index + 1}</span>
              <img class="avatar" src="${player.avatar_url || 'https://www.gravatar.com/avatar/?d=mp&s=50'}" alt="${player.username}">
              <a class="user-link" href="/pages/user.html?user=${player.user_id}">${player.username}</a>
              <span class="score">${formatNumberWithCommas(player.total_credits || 0)} cred</span>
            `;
            leaderboardList.appendChild(listItem);
          });
          localStorage.setItem(cacheKey, JSON.stringify(data));
        } else {
          leaderboardList.innerHTML = '<li>No leaderboard data available.</li>';
          localStorage.removeItem(cacheKey);
        }
      })
      .catch(error => {
        console.error(`Error fetching ${timeframe} leaderboard data:`, error);
        leaderboardList.innerHTML = '<li>Error loading leaderboard data.</li>';
      });
  }

  // Fetch data for all timeframes on page load
  fetchLeaderboardData('weekly');
  fetchLeaderboardData('monthly');
  fetchLeaderboardData('alltime');
  fetchPopularGames('weekly');
  fetchPopularGames('monthly');
  fetchPopularGames('alltime');

  // Setup champions tabs
  const championsTabs = document.querySelectorAll('.champions-tabs .tab-btn');
  championsTabs.forEach(tab => {
    tab.addEventListener('click', function() {
      // Remove active class from all tabs
      championsTabs.forEach(t => t.classList.remove('active'));
      // Add active class to clicked tab
      this.classList.add('active');
      
      // Hide all content
      document.querySelectorAll('.champions-content').forEach(content => {
        content.classList.remove('active');
      });
      
      // Show selected content
      const tabName = this.getAttribute('data-tab');
      const selectedContent = document.getElementById(`${tabName}-champions`);
      if (selectedContent) {
        selectedContent.classList.add('active');
      }
    });
  });

  // Fetch current champions
  fetchCurrentChampions();

  // Function to fetch and display current champions
  async function fetchCurrentChampions() {
    try {
      const response = await fetch('/api/current-champions');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const champions = await response.json();
      renderCurrentChampions(champions);
    } catch (error) {
      console.error('Error fetching current champions:', error);
      const weeklyContainer = document.getElementById('weekly-champions');
      const monthlyContainer = document.getElementById('monthly-champions');
      if (weeklyContainer) {
        weeklyContainer.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Error loading champions</div>';
      }
      if (monthlyContainer) {
        monthlyContainer.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Error loading champions</div>';
      }
    }
  }

  function renderCurrentChampions(champions) {
    const weeklyContainer = document.getElementById('weekly-champions');
    const monthlyContainer = document.getElementById('monthly-champions');

    // Render weekly champions
    if (weeklyContainer) {
      if (champions.weekly && champions.weekly.length > 0) {
        weeklyContainer.innerHTML = createPodiumDisplay(champions.weekly);
      } else {
        weeklyContainer.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> No weekly champions found</div>';
      }
    }

    // Render monthly champions
    if (monthlyContainer) {
      if (champions.monthly && champions.monthly.length > 0) {
        monthlyContainer.innerHTML = createPodiumDisplay(champions.monthly);
      } else {
        monthlyContainer.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> No monthly champions found</div>';
      }
    }
  }

  function createPodiumDisplay(champions) {
    if (champions.length === 0) {
      return '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> No champions found</div>';
    }

    // Sort champions by placement
    const sortedChampions = champions.sort((a, b) => a.placement - b.placement);
    
    // Get period info from first champion
    const startDate = new Date(sortedChampions[0].period_start);
    const endDate = new Date(sortedChampions[0].period_end);
    const periodText = `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`;

    let podiumHTML = '<div class="champions-podium">';
    
    // Create podium places
    sortedChampions.forEach(champion => {
      const placementClass = champion.placement === 1 ? 'first' : champion.placement === 2 ? 'second' : 'third';
      const medal = champion.placement === 1 ? '🥇' : champion.placement === 2 ? '🥈' : '🥉';
      
      podiumHTML += `
        <div class="podium-place ${placementClass}">
          <div class="podium-stand ${placementClass}">
            <img class="podium-avatar" src="${champion.avatar_url}" alt="${champion.username}">
            <a href="/pages/user.html?user=${champion.user_id}" class="podium-username">${champion.username}</a>
            <div class="podium-credits">${formatNumberWithCommas(champion.credits)} credits</div>
          </div>
        </div>
      `;
    });
    
    podiumHTML += '</div>';
    podiumHTML += `<div class="champions-period">Period: ${periodText}</div>`;
    
    return podiumHTML;
  }

  function getOrdinalSuffix(num) {
    const j = num % 10;
    const k = num % 100;
    if (j == 1 && k != 11) {
      return "st";
    }
    if (j == 2 && k != 12) {
      return "nd";
    }
    if (j == 3 && k != 13) {
      return "rd";
    }
    return "th";
  }

});

// --- Recent Activity with localStorage cache ---
async function fetchRecentActivity() {
  const activityCarousel = document.querySelector('.activity-carousel');
  if (!activityCarousel) return;

  // Try to show cached data instantly
  const cacheKey = 'recent_activity';
  const cached = localStorage.getItem(cacheKey);
  if (cached) {
    try {
      const recentActivity = JSON.parse(cached);
      renderRecentActivity(recentActivity);
    } catch (e) {}
  } else {
    // Show loading state if no cache
    activityCarousel.innerHTML = '';
    for (let i = 0; i < 5; i++) {
      const loadingCard = document.createElement('div');
      loadingCard.className = 'activity-card-wrap';
      loadingCard.innerHTML = `
        <div class="activity-card loading">
          <div class="activity-overlay loading">
            <div class="activity-userblock">
              <span class="activity-sessions">Loading...</span>
              <span class="activity-time">Loading...</span>
            </div>
          </div>
        </div>
      `;
      activityCarousel.appendChild(loadingCard);
    }
  }

  // Always fetch fresh data in the background
  try {
    const response = await fetch('/api/recent-activity');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const recentActivity = await response.json();
    renderRecentActivity(recentActivity);
    localStorage.setItem(cacheKey, JSON.stringify(recentActivity));
  } catch (error) {
    console.error('Error fetching recent activity:', error);
    activityCarousel.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Error loading activity</div>';
  }
}

function renderRecentActivity(recentActivity) {
  const activityCarousel = document.querySelector('.activity-carousel');
  if (!activityCarousel) return;
  activityCarousel.innerHTML = '';
  if (!recentActivity || recentActivity.length === 0) {
    activityCarousel.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> No recent activity found</div>';
    return;
  }
  recentActivity.forEach(session => {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'activity-card-wrap';
    const timestamp = new Date(session.timestamp);
    
    let mediaElement;
    if (session.box_art_url && session.box_art_url.endsWith('.webm')) {
        mediaElement = document.createElement('video');
        mediaElement.src = session.box_art_url;
        mediaElement.autoplay = true;
        mediaElement.loop = true;
        mediaElement.muted = true;
        mediaElement.playsInline = true;
    } else {
        mediaElement = document.createElement('img');
        mediaElement.src = session.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
        mediaElement.onerror = function() {
            this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
        };
    }
    mediaElement.className = 'game-cover-carousel';
    mediaElement.alt = session.game_name;

    cardWrap.innerHTML = `
      <div class="activity-card">
        <a href="/pages/game.html?game=${encodeURIComponent(session.game_name)}">
        </a>
        <div class="activity-date">${timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</div>
        ${session.players > 1 ? `<div class="coop-icon"><span class="player-count">${session.players}</span><i class="fas fa-users"></i></div>` : ''}
        <div class="activity-overlay">
          <img class="activity-avatar" src="${session.avatar_url}" alt="${session.username}">
          <div class="activity-userblock">
            <span class="activity-player"><a class="user-link" href="/pages/user.html?user=${session.user_id}">${session.username}</a></span>
            <span class="activity-hours">${formatHours(session.hours)}</span>
          </div>
        </div>
      </div>
    `;
    
    const link = cardWrap.querySelector('a');
    link.insertBefore(mediaElement, link.firstChild);
    activityCarousel.appendChild(cardWrap);
  });
}

// Function to detect if user is on mobile
function isMobileDevice() {
  return (
    /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
    (window.innerWidth <= 768 && window.innerHeight <= 1024)
  );
}

// Function to handle mobile-specific elements
function handleMobileElements() {
  const mobileElements = document.querySelectorAll('.mobile-only');
  const desktopElements = document.querySelectorAll('.desktop-only');
  
  if (isMobileDevice()) {
    mobileElements.forEach(el => el.style.display = 'block');
    desktopElements.forEach(el => el.style.display = 'none');
  } else {
    mobileElements.forEach(el => el.style.display = 'none');
    desktopElements.forEach(el => el.style.display = 'block');
  }
}

// Run on page load
handleMobileElements();

// Run on window resize
window.addEventListener('resize', handleMobileElements);

// Mobile menu toggle
const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
const navCenter = document.querySelector('.nav-center');
let isMenuOpen = false;

mobileMenuToggle.addEventListener('click', function(e) {
  e.stopPropagation();
  isMenuOpen = !isMenuOpen;
  navCenter.classList.toggle('active');
  
  // Update hamburger icon
  const icon = this.querySelector('i');
  if (isMenuOpen) {
    icon.classList.remove('fa-bars');
    icon.classList.add('fa-times');
  } else {
    icon.classList.remove('fa-times');
    icon.classList.add('fa-bars');
  }
});

// Close mobile menu when clicking outside
document.addEventListener('click', function(event) {
  if (isMenuOpen && !navCenter.contains(event.target) && !mobileMenuToggle.contains(event.target)) {
    isMenuOpen = false;
    navCenter.classList.remove('active');
    const icon = mobileMenuToggle.querySelector('i');
    icon.classList.remove('fa-times');
    icon.classList.add('fa-bars');
  }
});

// Prevent clicks inside the menu from closing it
navCenter.addEventListener('click', function(event) {
  event.stopPropagation();
});

// Add this helper function near the other formatting functions
function formatHours(hours) {
  const wholeHours = Math.floor(hours);
  const minutes = Math.round((hours - wholeHours) * 60);
  let timeDisplay = '';
  if (wholeHours > 0) {
    timeDisplay += `${wholeHours}h `;
  }
  if (minutes > 0 || wholeHours === 0) {
    timeDisplay += `${minutes}m`;
  }
  return timeDisplay;
}

// Function to set up the activity carousel scrolling
function setupActivityCarousel() {
  const activityCarousel = document.querySelector('.activity-carousel');
  const leftArrow = document.querySelector('.activity-wide .carousel-arrow.left');
  const rightArrow = document.querySelector('.activity-wide .carousel-arrow.right');

  if (!activityCarousel || !leftArrow || !rightArrow) {
    console.error('Activity carousel elements not found for scrolling setup.');
    return;
  }

  const scrollAmount = 300; // Adjust scroll amount as needed

  leftArrow.addEventListener('click', () => {
    activityCarousel.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
  });

  rightArrow.addEventListener('click', () => {
    activityCarousel.scrollBy({ left: scrollAmount, behavior: 'smooth' });
  });
}

// On page load, show alltime activity by default
fetchRecentActivity().then(() => setupActivityCarousel()); 