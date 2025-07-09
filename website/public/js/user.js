// User Profile Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
  // Function to get user ID or username from URL
  function getUserIdentifierFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const identifier = params.get('user'); // Get the raw identifier from URL
    return identifier; // Return as is, no conversion needed
  }

  // Helper function to format numbers with commas
  function formatNumberWithCommas(number) {
    if (typeof number === 'number') {
      return number.toLocaleString();
    }
    if (!isNaN(Number(number))) {
      return Number(number).toLocaleString();
    }
    return number;
  }

  // Helper function to format hours for display
  function formatHours(hours) {
    const wholeHours = Math.floor(hours);
    const minutes = Math.round((hours - wholeHours) * 60);
    let timeDisplay = '';
    if (wholeHours > 0) {
      timeDisplay += `${wholeHours}h `;
    }
    if (minutes > 0 || wholeHours === 0) { // Show minutes if there are any, or if hours are 0
      timeDisplay += `${minutes}m`;
    }
    return timeDisplay.trim();
  }

  // Helper function to format time ago
  function formatTimeAgo(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    return date.toLocaleDateString();
  }

  // Helper function to capitalize words
  function capitalizeWords(str) {
    if (!str) return '';
    return str.replace(/\b\w/g, char => char.toUpperCase());
  }

  // Function to get ordinal suffix
  function getOrdinalSuffix(num) {
    const j = num % 10;
    const k = num % 100;
    if (j == 1 && k != 11) return 'st';
    if (j == 2 && k != 12) return 'nd';
    if (j == 3 && k != 13) return 'rd';
    return 'th';
  }

  // Function to get placement icon
  function getPlacementIcon(placement) {
    if (placement === 1) return '🥇';
    if (placement === 2) return '🥈';
    if (placement === 3) return '🥉';
    return '';
  }

  // Function to format period
  function formatPeriod(start, end) {
    const startDate = new Date(start);
    const endDate = new Date(end);
    return `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`;
  }

  // Function to fetch and display user profile data
  async function fetchUserProfile(userIdentifier, timeframe = 'alltime') {
    if (!userIdentifier) {
      console.error('User identifier not found in URL.');
      document.querySelector('.profile-header h1').textContent = 'User Not Found';
      document.querySelector('.profile-avatar').src = 'https://www.gravatar.com/avatar/?d=mp&s=50'; // Default avatar
      document.getElementById('totalCredits').textContent = '';
      document.getElementById('userRank').textContent = '';
      document.getElementById('totalHours').textContent = '';
      document.getElementById('gamesPlayed').textContent = '';
      document.getElementById('totalSessions').textContent = '';
      // Hide or clear most played section if user not found
      document.querySelector('.most-played .most-played-carousel .activity-carousel').innerHTML = '<p>User not found or has no stats.</p>';
      return;
    }

    try {
      // Include timeframe in the API call
      const response = await fetch(`/api/user-stats/${userIdentifier}?timeframe=${timeframe}`);
      
      if (response.status === 404) {
        console.warn(`User stats not found for ${userIdentifier}. Displaying basic info.`);
        // Display basic Discord info if available, but no stats
        const discordInfoResponse = await fetch(`/api/user-stats/${userIdentifier}`); // Fetch without timeframe for basic info
        if(discordInfoResponse.ok) {
          const basicInfo = await discordInfoResponse.json();
          document.querySelector('.profile-header h1').textContent = basicInfo.username;
          document.querySelector('.profile-avatar').src = basicInfo.avatar_url;
          document.getElementById('totalCredits').textContent = '0 pts';
          document.getElementById('userRank').textContent = 'Rank N/A';
          document.getElementById('totalHours').textContent = '0 hrs';
          document.getElementById('gamesPlayed').textContent = '0 games';
          document.getElementById('totalSessions').textContent = '0 sessions';
          document.querySelector('.most-played .most-played-carousel .activity-carousel').innerHTML = '<p>No gaming activity recorded for this timeframe.</p>';
        } else {
          // Fallback if even basic info fails
          document.querySelector('.profile-header h1').textContent = 'User Not Found';
          document.querySelector('.profile-avatar').src = 'https://www.gravatar.com/avatar/?d=mp&s=50'; // Default avatar
          document.getElementById('totalCredits').textContent = '';
          document.getElementById('userRank').textContent = '';
          document.getElementById('totalHours').textContent = '';
          document.getElementById('gamesPlayed').textContent = '';
          document.getElementById('totalSessions').textContent = '';
          document.querySelector('.most-played .most-played-carousel .activity-carousel').innerHTML = '<p>User not found.</p>';
        }
        return; // Exit the function as user stats were not found
      } else if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const userData = await response.json();
      console.log('User Data:', userData); // Debugging: Log the fetched user data

      // Update profile header with fetched data
      document.querySelector('.profile-header h1').textContent = userData.username;
      document.querySelector('.profile-avatar').src = userData.avatar_url;
      document.getElementById('totalCredits').textContent = `${formatNumberWithCommas(userData.total_credits)} pts`;
      document.getElementById('userRank').textContent = userData.rank !== null ? `Rank #${userData.rank}` : 'Rank N/A';
      
      // Update secondary stats
      document.getElementById('totalHours').textContent = `${formatNumberWithCommas(userData.total_hours || 0)} hrs`;
      document.getElementById('gamesPlayed').textContent = `${formatNumberWithCommas(userData.games_played || 0)} games`;
      document.getElementById('totalSessions').textContent = `${formatNumberWithCommas(userData.total_sessions || 0)} sessions`;

      // Update stats button URL
      const statsBtn = document.getElementById('viewStatsBtn');
      if (statsBtn) {
        statsBtn.href = `/user_stats.html?user=${encodeURIComponent(userIdentifier)}`;
      }

      // Update Most Played section
      const mostPlayedCarousel = document.querySelector('#played-' + timeframe + ' .activity-carousel');
      if (!mostPlayedCarousel) {
        console.error(`Most played carousel element not found for timeframe: ${timeframe}`);
        return;
      }
      mostPlayedCarousel.innerHTML = ''; // Clear previous content

      const mostPlayedData = userData.most_played; // This is now a list of games
      console.log('Most played data:', mostPlayedData); // Debug log
      if (mostPlayedData && mostPlayedData.length > 0) {
        mostPlayedData.forEach(game => {
          console.log('Processing game:', game); // Debug log
          const hoursPlayed = game.total_hours;
          const timePlayedDisplay = hoursPlayed >= 1 ? `${hoursPlayed.toFixed(1)} hrs` : `${(hoursPlayed * 60).toFixed(0)} mins`;

          const cardWrap = document.createElement('div');
          cardWrap.className = 'activity-card-wrap';
          
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
          mediaElement.className = 'game-cover-carousel';
          mediaElement.alt = game.game_name;

          cardWrap.innerHTML = `
            <div class="activity-card">
              <a href="/pages/game.html?game=${encodeURIComponent(game.game_name)}">
              </a>
              <div class="activity-overlay">
                <div class="activity-userblock">
                  <span class="activity-sessions">${game.game_name}</span>
                  <span class="activity-time">${timePlayedDisplay}</span>
                </div>
              </div>
            </div>
          `;
          
          const link = cardWrap.querySelector('a');
          link.insertBefore(mediaElement, link.firstChild);
          mostPlayedCarousel.appendChild(cardWrap);
        });
      } else {
        mostPlayedCarousel.innerHTML = '<p>No gaming activity recorded for this timeframe.</p>';
      }

    } catch (error) {
      console.error('Error fetching user profile data:', error);
      // Display an error message on the page
      document.querySelector('.profile-header h1').textContent = 'Error loading profile';
      document.querySelector('.profile-avatar').src = 'https://www.gravatar.com/avatar/?d=mp&s=50'; // Default avatar
      document.getElementById('totalCredits').textContent = '';
      document.getElementById('userRank').textContent = '';
      document.getElementById('totalHours').textContent = '';
      document.getElementById('gamesPlayed').textContent = '';
      document.getElementById('totalSessions').textContent = '';
      document.querySelector('.most-played .most-played-carousel .activity-carousel').innerHTML = '<p>Error loading profile data.</p>';
    }
  }

  // Function to handle tab switching
  function handleTabSwitching() {
    // Handle most played tabs
    const mostPlayedTabButtons = document.querySelectorAll('.most-played-tabs .tab-btn');
    const mostPlayedTabContents = document.querySelectorAll('.most-played .tab-content');

    mostPlayedTabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const targetTabId = button.dataset.tab;
        const targetContent = document.getElementById(targetTabId);

        if (!targetContent) {
          console.error(`Tab content with ID ${targetTabId} not found.`);
          return;
        }

        // Remove active class from all buttons and contents
        mostPlayedTabButtons.forEach(btn => btn.classList.remove('active'));
        mostPlayedTabContents.forEach(content => content.classList.remove('active'));

        // Add active class to the clicked button and target content
        button.classList.add('active');
        targetContent.classList.add('active');
      });
    });
  }

  // Function to show/hide loading state
  function setLoadingState(element, isLoading) {
    if (isLoading) {
      element.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
    }
  }

  // Function to fetch and display recent activity
  async function fetchRecentActivity(userIdentifier) {
    const activityList = document.querySelector('.profile-activity ul');
    if (!activityList) {
      console.error('Recent activity list element not found.');
      return;
    }

    setLoadingState(activityList, true);
    
    try {
      const response = await fetch(`/api/user-stats/${userIdentifier}/history`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const activityData = await response.json();

      activityList.innerHTML = ''; // Clear loading state

      if (!activityData || activityData.length === 0) {
        activityList.innerHTML = '<li>No recent activity found.</li>';
        return;
      }

      // Show first 5 items initially
      const initialItems = activityData.slice(0, 5);
      initialItems.forEach(activity => {
        const hours = activity.hours;
        const timeDisplay = hours >= 1 ? `${hours.toFixed(1)}h` : `${(hours * 60).toFixed(0)}m`;
        const date = new Date(activity.timestamp).toLocaleDateString();
        const listItem = document.createElement('li');
        
        let mediaElement;
        if (activity.box_art_url && activity.box_art_url.endsWith('.webm')) {
          mediaElement = document.createElement('video');
          mediaElement.src = activity.box_art_url;
          mediaElement.autoplay = true;
          mediaElement.loop = true;
          mediaElement.muted = true;
          mediaElement.playsInline = true;
        } else {
          mediaElement = document.createElement('img');
          mediaElement.src = activity.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
          mediaElement.onerror = function() {
            this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
          };
        }
        mediaElement.className = 'game-cover-activity';
        mediaElement.alt = activity.game_name;

        listItem.innerHTML = `
          ${mediaElement.outerHTML}
          <div class="activity-details">
            <div class="game-name">${activity.game_name}${activity.players > 1 ? ` <span class="coop-indicator"><span class="player-count">${activity.players}</span><i class="fas fa-users"></i></span>` : ''}</div>
            <div class="activity-time">${timeDisplay}</div>
            <div class="activity-credits">${formatNumberWithCommas(activity.credits_earned)} credits</div>
            <div class="activity-date">${date}</div>
          </div>
        `;
        
        activityList.appendChild(listItem);
      });

      // Add "Show More" functionality if there are more items
      if (activityData.length > 5) {
        const hiddenContainer = document.createElement('div');
        hiddenContainer.dataset.remainingItems = JSON.stringify(activityData.slice(5));
        hiddenContainer.dataset.currentIndex = '0';
        hiddenContainer.style.display = 'none';
        activityList.appendChild(hiddenContainer);

        const buttonContainer = document.createElement('div');
        buttonContainer.style.display = 'flex';
        buttonContainer.style.gap = '0.5rem';
        buttonContainer.style.justifyContent = 'center';
        buttonContainer.style.marginTop = '1rem';

        const moreButton = document.createElement('button');
        moreButton.className = 'more-button';
        moreButton.textContent = 'Show More';
        moreButton.onclick = () => {
          const items = JSON.parse(hiddenContainer.dataset.remainingItems);
          const currentIndex = parseInt(hiddenContainer.dataset.currentIndex);
          const remainingItems = items.slice(currentIndex, currentIndex + 5);
          
          remainingItems.forEach(activity => {
            const hours = activity.hours;
            const timeDisplay = hours >= 1 ? `${hours.toFixed(1)}h` : `${(hours * 60).toFixed(0)}m`;
            const date = new Date(activity.timestamp).toLocaleDateString();
            const listItem = document.createElement('li');
            
            let mediaElement;
            if (activity.box_art_url && activity.box_art_url.endsWith('.webm')) {
              mediaElement = document.createElement('video');
              mediaElement.src = activity.box_art_url;
              mediaElement.autoplay = true;
              mediaElement.loop = true;
              mediaElement.muted = true;
              mediaElement.playsInline = true;
            } else {
              mediaElement = document.createElement('img');
              mediaElement.src = activity.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
              mediaElement.onerror = function() {
                this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
              };
            }
            mediaElement.className = 'game-cover-activity';
            mediaElement.alt = activity.game_name;

            listItem.innerHTML = `
              ${mediaElement.outerHTML}
              <div class="activity-details">
                <div class="game-name">${activity.game_name}${activity.players > 1 ? ` <span class="coop-indicator"><span class="player-count">${activity.players}</span><i class="fas fa-users"></i></span>` : ''}</div>
                <div class="activity-time">${timeDisplay}</div>
                <div class="activity-credits">${formatNumberWithCommas(activity.credits_earned)} credits</div>
                <div class="activity-date">${date}</div>
              </div>
            `;
            
            activityList.insertBefore(listItem, buttonContainer);
          });

          // Update the current index
          hiddenContainer.dataset.currentIndex = currentIndex + 5;

          // Hide the buttons if we've shown all items
          if (currentIndex + 5 >= items.length) {
            buttonContainer.style.display = 'none';
          }
        };

        const showAllButton = document.createElement('button');
        showAllButton.className = 'more-button';
        showAllButton.textContent = 'Show All';
        showAllButton.onclick = () => {
          const items = JSON.parse(hiddenContainer.dataset.remainingItems);
          const currentIndex = parseInt(hiddenContainer.dataset.currentIndex);
          const remainingItems = items.slice(currentIndex);
          
          remainingItems.forEach(activity => {
            const hours = activity.hours;
            const timeDisplay = hours >= 1 ? `${hours.toFixed(1)}h` : `${(hours * 60).toFixed(0)}m`;
            const date = new Date(activity.timestamp).toLocaleDateString();
            const listItem = document.createElement('li');
            
            let mediaElement;
            if (activity.box_art_url && activity.box_art_url.endsWith('.webm')) {
              mediaElement = document.createElement('video');
              mediaElement.src = activity.box_art_url;
              mediaElement.autoplay = true;
              mediaElement.loop = true;
              mediaElement.muted = true;
              mediaElement.playsInline = true;
            } else {
              mediaElement = document.createElement('img');
              mediaElement.src = activity.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
              mediaElement.onerror = function() {
                this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
              };
            }
            mediaElement.className = 'game-cover-activity';
            mediaElement.alt = activity.game_name;

            listItem.innerHTML = `
              ${mediaElement.outerHTML}
              <div class="activity-details">
                <div class="game-name">${activity.game_name}${activity.players > 1 ? ` <span class="coop-indicator"><span class="player-count">${activity.players}</span><i class="fas fa-users"></i></span>` : ''}</div>
                <div class="activity-time">${timeDisplay}</div>
                <div class="activity-credits">${formatNumberWithCommas(activity.credits_earned)} credits</div>
                <div class="activity-date">${date}</div>
              </div>
            `;
            
            activityList.insertBefore(listItem, buttonContainer);
          });

          // Hide the buttons after showing all items
          buttonContainer.style.display = 'none';
        };

        buttonContainer.appendChild(moreButton);
        buttonContainer.appendChild(showAllButton);
        activityList.appendChild(buttonContainer);
      }

    } catch (error) {
      console.error('Error fetching recent activity:', error);
      activityList.innerHTML = '<li>Error loading recent activity.</li>';
    }
  }

  // Function to fetch and display leaderboard history
  async function fetchLeaderboardHistory(userIdentifier, type) {
    try {
      const response = await fetch(`/api/user-stats/${userIdentifier}/leaderboard-history?type=${type}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const historyData = await response.json();

      const historyList = document.querySelector(`.leaderboard-history-list.${type}`);
      if (!historyList) {
        console.error(`Leaderboard history list element not found for type: ${type}`);
        return;
      }

      if (!historyData || historyData.length === 0) {
        historyList.innerHTML = `<li>No ${type} placements found.</li>`;
        return;
      }

      // Clear existing content
      historyList.innerHTML = '';

      // Show first 5 items initially
      const initialItems = historyData.slice(0, 5);
      initialItems.forEach(entry => {
        const startDate = entry.start_date ? new Date(entry.start_date) : null;
        const endDate = entry.end_date ? new Date(entry.end_date) : null;
        
        const periodDisplay = startDate && endDate 
          ? `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`
          : 'Period not available';

        const placement = entry.placement;
        let placementDisplay = `${placement}${getOrdinalSuffix(placement)}`;
        
        if (placement === 1) {
          placementDisplay = `🥇 ${placementDisplay}`;
        } else if (placement === 2) {
          placementDisplay = `🥈 ${placementDisplay}`;
        } else if (placement === 3) {
          placementDisplay = `🥉 ${placementDisplay}`;
        }

        const li = document.createElement('li');
        li.innerHTML = `
          <div class="period">${periodDisplay}</div>
          <div>
            <span class="placement">${placementDisplay}</span>
          </div>
          <div class="credits">${formatNumberWithCommas(entry.credits)} credits earned</div>
          <div class="most-played">Most played: ${entry.most_played_game} (${entry.most_played_hours.toFixed(1)}h)</div>
        `;
        
        historyList.appendChild(li);
      });

      // Add "Show More" functionality if there are more items
      if (historyData.length > 5) {
        const hiddenContainer = document.createElement('div');
        hiddenContainer.dataset.remainingItems = JSON.stringify(historyData.slice(5));
        hiddenContainer.dataset.currentIndex = '0';
        hiddenContainer.style.display = 'none';
        historyList.appendChild(hiddenContainer);

        const buttonContainer = document.createElement('div');
        buttonContainer.style.display = 'flex';
        buttonContainer.style.gap = '0.5rem';
        buttonContainer.style.justifyContent = 'center';
        buttonContainer.style.marginTop = '1rem';

        const moreButton = document.createElement('button');
        moreButton.className = 'more-button';
        moreButton.textContent = 'Show More';
        moreButton.onclick = () => {
          const items = JSON.parse(hiddenContainer.dataset.remainingItems);
          const currentIndex = parseInt(hiddenContainer.dataset.currentIndex);
          const remainingItems = items.slice(currentIndex, currentIndex + 5);
          
          remainingItems.forEach(entry => {
            const startDate = entry.start_date ? new Date(entry.start_date) : null;
            const endDate = entry.end_date ? new Date(entry.end_date) : null;
            
            const periodDisplay = startDate && endDate 
              ? `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`
              : 'Period not available';

            const placement = entry.placement;
            let placementDisplay = `${placement}${getOrdinalSuffix(placement)}`;
            
            if (placement === 1) {
              placementDisplay = `🥇 ${placementDisplay}`;
            } else if (placement === 2) {
              placementDisplay = `🥈 ${placementDisplay}`;
            } else if (placement === 3) {
              placementDisplay = `🥉 ${placementDisplay}`;
            }

            const li = document.createElement('li');
            li.innerHTML = `
              <div class="period">${periodDisplay}</div>
              <div>
                <span class="placement">${placementDisplay}</span>
              </div>
              <div class="credits">${formatNumberWithCommas(entry.credits)} credits earned</div>
              <div class="most-played">Most played: ${entry.most_played_game} (${entry.most_played_hours.toFixed(1)}h)</div>
            `;
            
            historyList.insertBefore(li, buttonContainer);
          });

          // Update the current index
          hiddenContainer.dataset.currentIndex = currentIndex + 5;

          // Hide the buttons if we've shown all items
          if (currentIndex + 5 >= items.length) {
            buttonContainer.style.display = 'none';
          }
        };

        const showAllButton = document.createElement('button');
        showAllButton.className = 'more-button';
        showAllButton.textContent = 'Show All';
        showAllButton.onclick = () => {
          const items = JSON.parse(hiddenContainer.dataset.remainingItems);
          const currentIndex = parseInt(hiddenContainer.dataset.currentIndex);
          const remainingItems = items.slice(currentIndex);
          
          remainingItems.forEach(entry => {
            const startDate = entry.start_date ? new Date(entry.start_date) : null;
            const endDate = entry.end_date ? new Date(entry.end_date) : null;
            
            const periodDisplay = startDate && endDate 
              ? `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`
              : 'Period not available';

            const placement = entry.placement;
            let placementDisplay = `${placement}${getOrdinalSuffix(placement)}`;
            
            if (placement === 1) {
              placementDisplay = `🥇 ${placementDisplay}`;
            } else if (placement === 2) {
              placementDisplay = `🥈 ${placementDisplay}`;
            } else if (placement === 3) {
              placementDisplay = `🥉 ${placementDisplay}`;
            }

            const li = document.createElement('li');
            li.innerHTML = `
              <div class="period">${periodDisplay}</div>
              <div>
                <span class="placement">${placementDisplay}</span>
              </div>
              <div class="credits">${formatNumberWithCommas(entry.credits)} credits earned</div>
              <div class="most-played">Most played: ${entry.most_played_game} (${entry.most_played_hours.toFixed(1)}h)</div>
            `;
            
            historyList.insertBefore(li, buttonContainer);
          });

          // Hide the buttons after showing all items
          buttonContainer.style.display = 'none';
        };

        buttonContainer.appendChild(moreButton);
        buttonContainer.appendChild(showAllButton);
        historyList.appendChild(buttonContainer);
      }
    } catch (error) {
      console.error('Error fetching leaderboard history:', error);
      const historyList = document.querySelector(`.leaderboard-history-list.${type}`);
      if (historyList) {
        historyList.innerHTML = '<li>Error loading leaderboard history.</li>';
      }
    }
  }

  // Function to setup leaderboard tabs
  function setupLeaderboardTabs() {
    const tabContainer = document.querySelector('.leaderboard-tabs');
    if (!tabContainer) return;
    const tabButtons = tabContainer.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
      button.addEventListener('click', function() {
        const tabId = this.getAttribute('data-tab');
        tabContainer.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        this.classList.add('active');
        const parentSection = this.closest('section');
        parentSection.querySelectorAll('.tab-content').forEach(content => {
          content.style.display = 'none';
        });
        const tabContent = document.getElementById('tab-' + tabId);
        if (tabContent) tabContent.style.display = 'block';
      });
    });
    // Initial display: show the active tab's content
    const initialActive = tabContainer.querySelector('.tab-btn.active');
    if (initialActive) {
      const tabId = initialActive.getAttribute('data-tab');
      const tabContent = document.getElementById('tab-' + tabId);
      if (tabContent) tabContent.style.display = 'block';
    }
    // Hide all other tab contents
    tabButtons.forEach(btn => {
      if (!btn.classList.contains('active')) {
        const tabId = btn.getAttribute('data-tab');
        const tabContent = document.getElementById('tab-' + tabId);
        if (tabContent) tabContent.style.display = 'none';
      }
    });
  }

  // Initial calls to fetch data when the page loads
  const userIdentifier = getUserIdentifierFromUrl();
  if (userIdentifier) {
    // Fetch data for all timeframes to populate the most played tabs
    fetchUserProfile(userIdentifier, 'weekly');
    fetchUserProfile(userIdentifier, 'monthly');
    fetchUserProfile(userIdentifier, 'alltime');
    fetchRecentActivity(userIdentifier);
    fetchLeaderboardHistory(userIdentifier, 'weekly');
    fetchLeaderboardHistory(userIdentifier, 'monthly');
  }

  // Initialize tab switching logic
  handleTabSwitching();
  setupLeaderboardTabs();

  // Tab switching logic for most played tabs
  document.querySelectorAll('.most-played-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.most-played-tabs .tab-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      document.querySelectorAll('.most-played .tab-content').forEach(tc => tc.classList.remove('active'));
      const tab = this.getAttribute('data-tab');
      document.getElementById(tab).classList.add('active');
    });
  });

  // Dedicated tab logic for user page leaderboard placements
  const tabContainer = document.querySelector('.previous-leaderboard-placements .leaderboard-tabs');
  if (tabContainer) {
    const tabButtons = tabContainer.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
      button.addEventListener('click', function() {
        const tabId = this.getAttribute('data-tab');
        tabContainer.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        this.classList.add('active');
        const parentSection = this.closest('.previous-leaderboard-placements');
        parentSection.querySelectorAll('.tab-content').forEach(content => {
          content.style.display = 'none';
        });
        const tabContent = parentSection.querySelector('#tab-' + tabId);
        if (tabContent) tabContent.style.display = 'block';
      });
    });
    // Initial display: show the active tab's content
    const initialActive = tabContainer.querySelector('.tab-btn.active');
    if (initialActive) {
      const tabId = initialActive.getAttribute('data-tab');
      const tabContent = document.getElementById('tab-' + tabId);
      if (tabContent) tabContent.style.display = 'block';
    }
    // Hide all other tab contents
    tabButtons.forEach(btn => {
      if (!btn.classList.contains('active')) {
        const tabId = btn.getAttribute('data-tab');
        const tabContent = document.getElementById('tab-' + tabId);
        if (tabContent) tabContent.style.display = 'none';
      }
    });
  }

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
}); 