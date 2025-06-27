// User Stats Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
  // Global variables
  let userIdentifier = null;
  let userData = null;
  let gamesData = [];
  let currentPage = 1;
  let itemsPerPage = 20;
  let sortField = 'hours';
  let sortDirection = 'desc';
  let searchTerm = '';
  let charts = {};
  let sessionData = [];

  // Initialize the page
  function init() {
    console.log('Initializing user stats page...');
    console.log('Current URL:', window.location.href);
    
    userIdentifier = getUserIdentifierFromUrl();
    console.log('User identifier:', userIdentifier);
    
    if (!userIdentifier) {
      console.error('No user identifier found in URL');
      showError('User identifier not found in URL. Please make sure you are accessing this page from a user profile.');
      return;
    }

    // Update navigation links
    document.getElementById('backToProfile').href = `/user.html?user=${encodeURIComponent(userIdentifier)}`;
    
    // Load user data
    loadUserData();
    
    // Setup event listeners
    setupEventListeners();
    loadSessionData();
  }

  // Get user identifier from URL
  function getUserIdentifierFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const userParam = params.get('user');
    console.log('URL search params:', window.location.search);
    console.log('User parameter found:', userParam);
    return userParam;
  }

  // Format numbers with commas
  function formatNumberWithCommas(number) {
    if (typeof number === 'number') {
      return number.toLocaleString();
    }
    if (!isNaN(Number(number))) {
      return Number(number).toLocaleString();
    }
    return number;
  }

  // Format hours for display
  function formatHours(hours) {
    if (!hours || hours === 0) return '0h';
    const wholeHours = Math.floor(hours);
    const minutes = Math.round((hours - wholeHours) * 60);
    let timeDisplay = '';
    if (wholeHours > 0) {
      timeDisplay += `${wholeHours}h `;
    }
    if (minutes > 0 || wholeHours === 0) {
      timeDisplay += `${minutes}m`;
    }
    return timeDisplay.trim();
  }

  // Format date
  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  }

  // Load user data
  async function loadUserData() {
    try {
      const response = await fetch(`/api/user-stats/${encodeURIComponent(userIdentifier)}?timeframe=alltime`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      userData = await response.json();
      updateUserHeader();
      loadGamesData();
      loadAchievements();
    } catch (error) {
      console.error('Error loading user data:', error);
      showError('Failed to load user data.');
    }
  }

  // Update user header
  function updateUserHeader() {
    if (!userData) return;

    document.getElementById('userName').textContent = userData.username;
    document.getElementById('userAvatar').src = userData.avatar_url;
    document.getElementById('totalCredits').textContent = `${formatNumberWithCommas(userData.total_credits)} pts`;
    document.getElementById('totalHours').textContent = `${formatNumberWithCommas(userData.total_hours || 0)} hrs`;
    document.getElementById('gamesPlayed').textContent = `${formatNumberWithCommas(userData.games_played || 0)} games`;
    document.getElementById('userRank').textContent = userData.rank !== null ? `#${userData.rank}` : 'N/A';

    // Update page title
    document.title = `${userData.username} - Stats - Gamer Cred`;
  }

  // Load games data
  async function loadGamesData() {
    try {
      const response = await fetch(`/api/user-game-summaries/${encodeURIComponent(userIdentifier)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      gamesData = await response.json();
      updateStatsOverview();
      renderGamesTable();
      createCharts();
    } catch (error) {
      console.error('Error loading games data:', error);
      showError('Failed to load games data.');
    }
  }

  // Update stats overview
  function updateStatsOverview() {
    if (!gamesData || gamesData.length === 0) return;

    // Calculate average hours per session
    const totalSessions = gamesData.reduce((sum, game) => sum + game.total_sessions, 0);
    const avgHoursPerSession = totalSessions > 0 ? (userData.total_hours / totalSessions).toFixed(1) : 0;
    document.getElementById('avgHoursPerSession').textContent = `${avgHoursPerSession}h`;

    // Calculate days active (unique days with sessions)
    const uniqueDays = new Set();
    gamesData.forEach(game => {
      if (game.first_played) {
        uniqueDays.add(game.first_played.split('T')[0]);
      }
      if (game.last_played) {
        uniqueDays.add(game.last_played.split('T')[0]);
      }
    });
    document.getElementById('daysActive').textContent = uniqueDays.size;

    // Calculate average credits per hour
    const avgCreditsPerHour = userData.total_hours > 0 ? (userData.total_credits / userData.total_hours).toFixed(1) : 0;
    document.getElementById('avgCreditsPerHour').textContent = `${avgCreditsPerHour} CPH`;

    // Find best game by CPH
    const bestGame = gamesData.reduce((best, game) => {
      const gameCph = game.total_hours > 0 ? (game.total_credits / game.total_hours) : 0;
      const bestCph = best.total_hours > 0 ? (best.total_credits / best.total_hours) : 0;
      return gameCph > bestCph ? game : best;
    });
    
    if (bestGame && bestGame.total_hours > 0) {
      const bestCph = (bestGame.total_credits / bestGame.total_hours).toFixed(1);
      const shortName = bestGame.game_name.length > 20 ? 
        bestGame.game_name.substring(0, 17) + '...' : bestGame.game_name;
      document.getElementById('bestGame').textContent = `${shortName} (${bestCph})`;
    } else {
      document.getElementById('bestGame').textContent = 'N/A';
    }

    // Additional stats for the page
    const totalGames = gamesData.length;
    const avgHoursPerGame = totalGames > 0 ? (userData.total_hours / totalGames).toFixed(1) : 0;
    const mostPlayedGame = gamesData.reduce((most, game) => 
      game.total_hours > most.total_hours ? game : most
    );
    
    // Update page title with additional context
    if (userData.username) {
      document.title = `${userData.username} - ${totalGames} Games, ${userData.total_hours.toFixed(0)}h - Stats - Gamer Cred`;
    }
  }

  // Render games table
  function renderGamesTable() {
    const tbody = document.getElementById('gamesTableBody');
    
    // Filter and sort games
    let filteredGames = gamesData.filter(game => 
      game.game_name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Sort games
    filteredGames.sort((a, b) => {
      let aValue, bValue;
      switch (sortField) {
        case 'hours':
          aValue = a.total_hours || 0;
          bValue = b.total_hours || 0;
          break;
        case 'credits':
          aValue = a.total_credits || 0;
          bValue = b.total_credits || 0;
          break;
        case 'sessions':
          aValue = a.total_sessions || 0;
          bValue = b.total_sessions || 0;
          break;
        case 'name':
          aValue = a.game_name.toLowerCase();
          bValue = b.game_name.toLowerCase();
          break;
        case 'cph':
          aValue = a.total_hours > 0 ? (a.total_credits / a.total_hours) : 0;
          bValue = b.total_hours > 0 ? (b.total_credits / b.total_hours) : 0;
          break;
        default:
          aValue = a.total_hours || 0;
          bValue = b.total_hours || 0;
      }
      if (sortDirection === 'desc') {
        return bValue - aValue;
      } else {
        return aValue - bValue;
      }
    });

    // Pagination
    const totalPages = Math.ceil(filteredGames.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageGames = filteredGames.slice(startIndex, endIndex);

    // Update pagination controls
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prevPage').disabled = currentPage <= 1;
    document.getElementById('nextPage').disabled = currentPage >= totalPages;

    // Clear table
    tbody.innerHTML = '';

    if (pageGames.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="loading-row">
            ${searchTerm ? 'No games found matching your search.' : 'No games found.'}
          </td>
        </tr>
      `;
      return;
    }

    // Add games to table
    pageGames.forEach(game => {
      const cph = game.total_hours > 0 ? (game.total_credits / game.total_hours).toFixed(1) : '0.0';
      const gameUrl = `/pages/game.html?game=${encodeURIComponent(game.game_name)}`;
      let mediaElement = '';
      if (game.box_art_url && game.box_art_url.endsWith('.webm')) {
        mediaElement = `<video src="${game.box_art_url}" class="game-cover-sm" autoplay loop muted playsinline style="width: 48px; height: 64px; border-radius: 8px; object-fit: cover;"></video>`;
      } else {
        mediaElement = `<img src="${game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'}" 
          alt="${game.game_name}" class="game-cover-sm" 
          onerror="this.src='https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'">`;
      }
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>
          <a href="${gameUrl}" class="game-cell-link">
            <div class="game-cell">
              ${mediaElement}
              <span class="game-name">${game.game_name}</span>
            </div>
          </a>
        </td>
        <td>${formatHours(game.total_hours)}</td>
        <td>${formatNumberWithCommas(game.total_credits)} pts</td>
        <td>${game.total_sessions}</td>
        <td>${cph} CPH</td>
        <td>${formatDate(game.first_played)}</td>
        <td>${formatDate(game.last_played)}</td>
      `;
      tbody.appendChild(row);
    });
  }

  // Create charts
  function createCharts() {
    if (!gamesData || gamesData.length === 0) return;

    // Sort games by hours for top 10
    const topGamesByHours = [...gamesData]
      .sort((a, b) => (b.total_hours || 0) - (a.total_hours || 0))
      .slice(0, 10);

    const topGamesByCredits = [...gamesData]
      .sort((a, b) => (b.total_credits || 0) - (a.total_credits || 0))
      .slice(0, 10);

    // Create shortened labels for better chart display
    const createShortLabels = (games) => {
      return games.map((game, index) => {
        const name = game.game_name;
        if (name.length <= 15) return name;
        
        // Try to use first word if it's short enough
        const firstWord = name.split(' ')[0];
        if (firstWord.length <= 12) return firstWord;
        
        // Use abbreviation or truncate
        if (name.includes(' ')) {
          const words = name.split(' ');
          if (words.length >= 2) {
            const abbreviation = words.map(word => word[0]).join('');
            if (abbreviation.length <= 8) return abbreviation;
          }
        }
        
        // Fallback to truncated name
        return name.substring(0, 12) + '...';
      });
    };

    // Hours Chart
    createBarChart('hoursChart', 'Hours by Game (Top 10)', 
      createShortLabels(topGamesByHours),
      topGamesByHours.map(g => g.total_hours || 0),
      '#ffb86c'
    );

    // Credits Chart
    createBarChart('creditsChart', 'Credits by Game (Top 10)',
      createShortLabels(topGamesByCredits),
      topGamesByCredits.map(g => g.total_credits || 0),
      '#50fa7b'
    );

    // Timeline Chart (activity over time)
    createTimelineChart();

    // Distribution Chart (pie chart of game types)
    createDistributionChart();
  }

  // Create bar chart
  function createBarChart(canvasId, title, labels, data, color) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    // Destroy existing chart if it exists
    if (charts[canvasId]) {
      charts[canvasId].destroy();
    }

    // Get full game names for tooltips
    const fullNames = data.map((_, index) => {
      if (canvasId === 'hoursChart') {
        const topGamesByHours = [...gamesData]
          .sort((a, b) => (b.total_hours || 0) - (a.total_hours || 0))
          .slice(0, 10);
        return topGamesByHours[index]?.game_name || '';
      } else {
        const topGamesByCredits = [...gamesData]
          .sort((a, b) => (b.total_credits || 0) - (a.total_credits || 0))
          .slice(0, 10);
        return topGamesByCredits[index]?.game_name || '';
      }
    });

    console.log('Heatmap data:', data);

    charts[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: title,
          data: data,
          backgroundColor: color,
          borderColor: color,
          borderWidth: 1,
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              title: function(context) {
                return fullNames[context[0].dataIndex] || context[0].label;
              },
              label: function(context) {
                const value = context.parsed.y;
                if (canvasId === 'hoursChart') {
                  return `Hours: ${value.toFixed(1)}`;
                } else {
                  return `Credits: ${value.toLocaleString()}`;
                }
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: '#44475a'
            },
            ticks: {
              color: '#f8f8f2',
              font: {
                size: 12
              }
            }
          },
          x: {
            grid: {
              color: '#44475a'
            },
            ticks: {
              color: '#f8f8f2',
              maxRotation: 45,
              minRotation: 0,
              font: {
                size: 11
              }
            }
          }
        },
        layout: {
          padding: {
            top: 20,
            bottom: 20
          }
        }
      }
    });
  }

  // Create timeline chart
  function createTimelineChart() {
    const ctx = document.getElementById('timelineChart');
    if (!ctx) return;

    // Group sessions by month
    const monthlyData = {};
    gamesData.forEach(game => {
      if (game.first_played) {
        const month = game.first_played.substring(0, 7); // YYYY-MM
        monthlyData[month] = (monthlyData[month] || 0) + game.total_sessions;
      }
    });

    const months = Object.keys(monthlyData).sort();
    const sessionCounts = months.map(month => monthlyData[month]);

    // Destroy existing chart if it exists
    if (charts['timelineChart']) {
      charts['timelineChart'].destroy();
    }

    charts['timelineChart'] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: months.map(month => {
          const [year, monthNum] = month.split('-');
          return `${monthNum}/${year.slice(2)}`;
        }),
        datasets: [{
          label: 'Sessions',
          data: sessionCounts,
          borderColor: '#8be9fd',
          backgroundColor: 'rgba(139, 233, 253, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#8be9fd',
          pointBorderColor: '#282a36',
          pointBorderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8,
          pointHoverBackgroundColor: '#50fa7b',
          pointHoverBorderColor: '#282a36'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              title: function(context) {
                const monthIndex = context[0].dataIndex;
                const fullMonth = months[monthIndex];
                const [year, month] = fullMonth.split('-');
                const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                return `${monthNames[parseInt(month) - 1]} ${year}`;
              },
              label: function(context) {
                return `Sessions: ${context.parsed.y}`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: '#44475a'
            },
            ticks: {
              color: '#f8f8f2',
              font: {
                size: 12
              }
            }
          },
          x: {
            grid: {
              color: '#44475a'
            },
            ticks: {
              color: '#f8f8f2',
              font: {
                size: 11
              }
            }
          }
        },
        layout: {
          padding: {
            top: 20,
            bottom: 20
          }
        }
      }
    });
  }

  // Create distribution chart
  function createDistributionChart() {
    const ctx = document.getElementById('distributionChart');
    if (!ctx) return;

    // Group games by hours played ranges
    const distribution = {
      '0-1h': 0,
      '1-5h': 0,
      '5-10h': 0,
      '10-25h': 0,
      '25-50h': 0,
      '50h+': 0
    };

    gamesData.forEach(game => {
      const hours = game.total_hours || 0;
      if (hours <= 1) distribution['0-1h']++;
      else if (hours <= 5) distribution['1-5h']++;
      else if (hours <= 10) distribution['5-10h']++;
      else if (hours <= 25) distribution['10-25h']++;
      else if (hours <= 50) distribution['25-50h']++;
      else distribution['50h+']++;
    });

    const labels = Object.keys(distribution);
    const data = Object.values(distribution);
    const colors = ['#ff79c6', '#bd93f9', '#8be9fd', '#50fa7b', '#ffb86c', '#ff5555'];

    // Destroy existing chart if it exists
    if (charts['distributionChart']) {
      charts['distributionChart'].destroy();
    }

    charts['distributionChart'] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors,
          borderWidth: 3,
          borderColor: '#282a36',
          hoverBorderWidth: 4,
          hoverBorderColor: '#8be9fd'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#f8f8f2',
              padding: 20,
              font: {
                size: 12
              },
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((context.parsed / total) * 100).toFixed(1);
                return `${context.label}: ${context.parsed} games (${percentage}%)`;
              }
            }
          }
        },
        layout: {
          padding: {
            top: 20,
            bottom: 20
          }
        }
      }
    });
  }

  // Load achievements
  function loadAchievements() {
    const achievementsGrid = document.getElementById('achievementsGrid');
    
    // Define achievements
    const achievements = [
      {
        id: 'first_game',
        title: 'First Steps',
        description: 'Play your first game',
        icon: 'fas fa-gamepad',
        condition: () => gamesData.length > 0,
        progress: () => gamesData.length > 0 ? 1 : 0,
        goal: 1
      },
      {
        id: '10_games',
        title: 'Game Collector',
        description: 'Play 10 different games',
        icon: 'fas fa-trophy',
        condition: () => gamesData.length >= 10,
        progress: () => Math.min(gamesData.length / 10, 1),
        goal: 10
      },
      {
        id: '100_hours',
        title: 'Dedicated Gamer',
        description: 'Play for 100+ hours',
        icon: 'fas fa-clock',
        condition: () => (userData.total_hours || 0) >= 100,
        progress: () => Math.min((userData.total_hours || 0) / 100, 1),
        goal: 100
      },
      {
        id: '1000_credits',
        title: 'Credit Master',
        description: 'Earn 1,000+ credits',
        icon: 'fas fa-coins',
        condition: () => (userData.total_credits || 0) >= 1000,
        progress: () => Math.min((userData.total_credits || 0) / 1000, 1),
        goal: 1000
      },
      {
        id: '50_sessions',
        title: 'Session Master',
        description: 'Complete 50+ gaming sessions',
        icon: 'fas fa-list',
        condition: () => gamesData.reduce((sum, game) => sum + (game.total_sessions || 0), 0) >= 50,
        progress: () => Math.min(gamesData.reduce((sum, game) => sum + (game.total_sessions || 0), 0) / 50, 1),
        goal: 50
      },
      {
        id: 'top_rank',
        title: 'Leaderboard Legend',
        description: 'Achieve a top 10 global rank',
        icon: 'fas fa-medal',
        condition: () => userData.rank !== null && userData.rank <= 10,
        progress: () => userData.rank !== null ? Math.max(0, 1 - (userData.rank - 1) / 10) : 0,
        goal: 1
      }
    ];

    // Clear loading state
    achievementsGrid.innerHTML = '';

    // Render achievements as large badge cards
    achievements.forEach(achievement => {
      const isEarned = achievement.condition();
      const progress = achievement.progress();
      const percent = Math.round(progress * 100);
      
      const card = document.createElement('div');
      card.className = `achievement-badge-card${isEarned ? ' earned' : ' locked'}`;
      card.innerHTML = `
        <div class="badge-icon-wrap">
          <i class="${achievement.icon} badge-icon"></i>
          ${!isEarned ? '<div class="badge-lock"><i class="fas fa-lock"></i></div>' : ''}
        </div>
        <div class="badge-content">
          <h4 class="badge-title">${achievement.title}</h4>
          <p class="badge-desc">${achievement.description}</p>
          <div class="badge-progress-bar-wrap">
            <div class="badge-progress-bar-bg">
              <div class="badge-progress-bar" style="width: ${percent}%;"></div>
            </div>
            <span class="badge-progress-label">${isEarned ? 'Completed!' : percent + '%'}</span>
          </div>
        </div>
      `;
      achievementsGrid.appendChild(card);
    });
  }

  // Setup event listeners
  function setupEventListeners() {
    // Search functionality
    document.getElementById('gameSearch').addEventListener('input', (e) => {
      searchTerm = e.target.value;
      currentPage = 1;
      renderGamesTable();
    });

    // Sort functionality
    document.getElementById('sortSelect').addEventListener('change', (e) => {
      sortField = e.target.value;
      renderGamesTable();
    });

    document.getElementById('sortDirection').addEventListener('click', () => {
      sortDirection = sortDirection === 'desc' ? 'asc' : 'desc';
      const icon = document.querySelector('#sortDirection i');
      icon.className = sortDirection === 'desc' ? 'fas fa-sort-amount-down' : 'fas fa-sort-amount-up';
      renderGamesTable();
    });

    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        renderGamesTable();
      }
    });

    document.getElementById('nextPage').addEventListener('click', () => {
      const totalPages = Math.ceil(gamesData.filter(game => 
        game.game_name.toLowerCase().includes(searchTerm.toLowerCase())
      ).length / itemsPerPage);
      
      if (currentPage < totalPages) {
        currentPage++;
        renderGamesTable();
      }
    });
  }

  // Show error message
  function showError(message) {
    const main = document.querySelector('.stats-main');
    main.innerHTML = `
      <div class="card" style="text-align: center; padding: 2rem;">
        <h2 style="color: #ff5555;">Error</h2>
        <p>${message}</p>
        <a href="/" class="nav-link-btn" style="display: inline-block; margin-top: 1rem;">
          <i class="fas fa-home"></i> Back to Home
        </a>
      </div>
    `;
  }

  // Load session data for heatmap (now fetches pre-aggregated daily credits)
  async function loadSessionData() {
    try {
      const response = await fetch(`/api/user-daily-credits/${encodeURIComponent(userIdentifier)}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      sessionData = await response.json();
      renderActivityHeatmap(sessionData);
    } catch (error) {
      console.error('Error loading session data:', error);
    }
  }

  // Update renderActivityHeatmap to accept data
  function renderActivityHeatmap(dataSource = null) {
    const dataArr = dataSource || gamesData;
    // Use pre-aggregated daily credits if available
    const data = Array.isArray(dataArr) && dataArr.length > 0 && dataArr[0].credits !== undefined
      ? dataArr.map(entry => ({ date: entry.date, count: Math.round(entry.credits) }))
      : [];
    console.log('Heatmap: final data array', data);

    const heatmapContainer = document.getElementById('activityHeatmap');
    console.log('Heatmap container:', heatmapContainer);
    console.log('Heatmap data:', data);
    if (!heatmapContainer) return;
    
    // Clear container
    heatmapContainer.innerHTML = '';
    
    // Create month navigation
    const navDiv = document.createElement('div');
    navDiv.className = 'heatmap-nav';
    navDiv.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 0 10px;';
    
    const prevBtn = document.createElement('button');
    prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
    prevBtn.className = 'heatmap-nav-btn';
    prevBtn.style.cssText = 'background: linear-gradient(135deg, #2a2a2a, #3a3a3a); border: none; color: white; padding: 8px 12px; border-radius: 6px; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.2);';
    
    const monthLabel = document.createElement('span');
    monthLabel.className = 'heatmap-month-label';
    monthLabel.style.cssText = 'font-weight: 700; color: #f8f8f2; font-size: 16px; text-shadow: 0 1px 2px rgba(0,0,0,0.3);';
    
    const nextBtn = document.createElement('button');
    nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
    nextBtn.className = 'heatmap-nav-btn';
    nextBtn.style.cssText = 'background: linear-gradient(135deg, #2a2a2a, #3a3a3a); border: none; color: white; padding: 8px 12px; border-radius: 6px; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.2);';
    
    // Add hover effects
    [prevBtn, nextBtn].forEach(btn => {
      btn.addEventListener('mouseenter', () => {
        btn.style.background = 'linear-gradient(135deg, #3a3a3a, #4a4a4a)';
        btn.style.transform = 'translateY(-1px)';
        btn.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
      });
      btn.addEventListener('mouseleave', () => {
        btn.style.background = 'linear-gradient(135deg, #2a2a2a, #3a3a3a)';
        btn.style.transform = 'translateY(0)';
        btn.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
      });
    });
    
    navDiv.appendChild(prevBtn);
    navDiv.appendChild(monthLabel);
    navDiv.appendChild(nextBtn);
    heatmapContainer.appendChild(navDiv);
    
    // Create SVG container
    const svgContainer = document.createElement('div');
    svgContainer.className = 'heatmap-svg-container';
    svgContainer.style.cssText = 'height: 200px; overflow: hidden; display: flex; justify-content: center; align-items: center; margin: 10px 0;';
    heatmapContainer.appendChild(svgContainer);
    
    // Create legend below the calendar
    const legendDiv = document.createElement('div');
    legendDiv.className = 'heatmap-legend';
    legendDiv.style.cssText = 'display: flex; flex-direction: column; align-items: center; anchor-items: center; gap: 2px; margin-bottom: 15px; padding-top: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); max-width: 40%; margin-left: auto; margin-right: auto;';

    // Swatch legend for the four stops
    const swatchRow = document.createElement('div');
    swatchRow.style.cssText = 'display: flex; gap: 18px; align-items: center; margin-bottom: 2px;';
    const swatches = [
      { value: '0', color: '#ffffff', label: '0' },
      { value: '500', color: '#7fd3ff', label: '500' },
      { value: '1,000', color: '#5ca9e6', label: '1,000' },
      { value: '3,000+', color: '#0a2342', label: '3,000+' }
    ];
    swatches.forEach(s => {
      const swatch = document.createElement('div');
      swatch.style.cssText = `display: flex; flex-direction: column; align-items: center;`;
      const colorBox = document.createElement('div');
      colorBox.style.cssText = `width: 22px; height: 14px; border-radius: 4px; background: ${s.color}; border: 1px solid #222; margin-bottom: 2px;`;
      const label = document.createElement('span');
      label.style.cssText = 'font-size: 12px; color: #ccc; font-weight: 500;';
      label.textContent = s.label;
      swatch.appendChild(colorBox);
      swatch.appendChild(label);
      swatchRow.appendChild(swatch);
    });
    legendDiv.appendChild(swatchRow);

    // Description
    const legendDesc = document.createElement('div');
    legendDesc.style.cssText = 'font-size: 12px; color: #aaa; margin-top: 2px; text-align: center;';
    legendDiv.appendChild(legendDesc);

    heatmapContainer.appendChild(legendDiv);
    
    // Current month state
    let currentMonth = new Date().getMonth();
    let currentYearState = new Date().getFullYear();
    
    // Create data map for quick lookup
    const dataMap = {};
    data.forEach(item => {
      dataMap[item.date] = item.count;
    });
    
    // Find max value for color scaling
    const maxValue = Math.max(...data.map(d => d.count), 1);
    
    // Create color scale function with smooth gradient
    function interpolateColor(color1, color2, t) {
      // color1, color2: hex strings; t: 0-1
      const c1 = color1.match(/#(..)(..)(..)/).slice(1).map(x => parseInt(x, 16));
      const c2 = color2.match(/#(..)(..)(..)/).slice(1).map(x => parseInt(x, 16));
      const c = c1.map((v, i) => Math.round(v + (c2[i] - v) * t));
      return `#${c.map(x => x.toString(16).padStart(2, '0')).join('')}`;
    }

    const colorStops = [
      { value: 0, color: '#ffffff' },      // White
      { value: 500, color: '#7fd3ff' },   // More visible Light Blue
      { value: 1000, color: '#5ca9e6' },  // Medium Blue
      { value: 3000, color: '#0a2342' }   // Deepest Blue
    ];

    function getColor(value) {
      if (value <= colorStops[0].value) return colorStops[0].color;
      if (value >= colorStops[colorStops.length - 1].value) return colorStops[colorStops.length - 1].color;
      for (let i = 0; i < colorStops.length - 1; i++) {
        const stop1 = colorStops[i];
        const stop2 = colorStops[i + 1];
        if (value >= stop1.value && value < stop2.value) {
          const t = (value - stop1.value) / (stop2.value - stop1.value);
          return interpolateColor(stop1.color, stop2.color, t);
        }
      }
      return colorStops[colorStops.length - 1].color;
    }
    
    // Render month function
    function renderMonth(month, year) {
      svgContainer.innerHTML = '';
      
      const svgWidth = 500;
      const svgHeight = 200;
      const cellWidth = 50;
      const cellHeight = 20;
      const colCount = 7;
      const rowCount = 6;
      const colSpacing = 10;
      const rowSpacing = 5;
      const gridWidth = colCount * cellWidth + (colCount - 1) * colSpacing;
      const gridStartX = (svgWidth - gridWidth) / 2;
      const gridStartY = 35;
      
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', '100%');
      svg.setAttribute('height', '100%');
      svg.setAttribute('viewBox', `0 0 ${svgWidth} ${svgHeight}`);
      
      // Update month label
      const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                         'July', 'August', 'September', 'October', 'November', 'December'];
      monthLabel.textContent = `${monthNames[month]} ${year}`;
      
      // Get first day of month and number of days
      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);
      const daysInMonth = lastDay.getDate();
      const startWeekday = firstDay.getDay(); // 0 = Sunday, 1 = Monday, etc.
      
      // Day labels above the calendar
      const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      dayLabels.forEach((day, index) => {
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', gridStartX + index * (cellWidth + colSpacing) + cellWidth / 2);
        text.setAttribute('y', 25);
        text.setAttribute('font-family', 'Inter, sans-serif');
        text.setAttribute('font-size', '14');
        text.setAttribute('font-weight', '600');
        text.setAttribute('fill', '#888');
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('pointer-events', 'none');
        text.textContent = day;
        svg.appendChild(text);
      });
      
      // Render calendar squares
      let dayCount = 1;
      for (let i = 0; i < rowCount; i++) { // Max 6 weeks
        for (let j = 0; j < colCount; j++) { // 7 days per week
          if (i === 0 && j < startWeekday) {
            // Empty space before first day
            continue;
          }
          if (dayCount > daysInMonth) {
            // Month is done
            break;
          }
          const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(dayCount).padStart(2, '0')}`;
          const value = dataMap[dateStr] || 0;
          const color = getColor(value);
          const x = gridStartX + j * (cellWidth + colSpacing);
          const y = gridStartY + i * (cellHeight + rowSpacing);
          // Add shadow filter
          const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
          const filter = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
          filter.setAttribute('id', `shadow-${dayCount}`);
          filter.setAttribute('x', '-20%');
          filter.setAttribute('y', '-20%');
          filter.setAttribute('width', '140%');
          filter.setAttribute('height', '140%');
          const feDropShadow = document.createElementNS('http://www.w3.org/2000/svg', 'feDropShadow');
          feDropShadow.setAttribute('dx', '0');
          feDropShadow.setAttribute('dy', '2');
          feDropShadow.setAttribute('stdDeviation', '3');
          feDropShadow.setAttribute('flood-color', 'rgba(0,0,0,0.3)');
          filter.appendChild(feDropShadow);
          defs.appendChild(filter);
          svg.appendChild(defs);
          const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
          rect.setAttribute('x', x);
          rect.setAttribute('y', y);
          rect.setAttribute('width', cellWidth);
          rect.setAttribute('height', cellHeight);
          rect.setAttribute('fill', color);
          rect.setAttribute('stroke', value > 0 ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.1)');
          rect.setAttribute('stroke-width', '1');
          rect.setAttribute('rx', '4');
          rect.setAttribute('filter', value > 0 ? `url(#shadow-${dayCount})` : 'none');
          // Add tooltip
          const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
          title.textContent = `${dateStr}: ${value} credits`;
          rect.appendChild(title);
          // Add day number (non-interactive) - centered in the square
          const dayText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          dayText.setAttribute('x', x + cellWidth / 2);
          dayText.setAttribute('y', y + cellHeight / 2 + 2);
          dayText.setAttribute('font-family', 'Inter, sans-serif');
          dayText.setAttribute('font-size', '12');
          dayText.setAttribute('font-weight', value > 0 ? '700' : '600');
          // Adaptive text color and shadow for contrast
          if (value >= 1000) {
            dayText.setAttribute('fill', '#fff');
            dayText.setAttribute('style', 'text-shadow: 0 1px 3px #0a2342, 0 0 2px #0a2342;');
          } else if (value >= 500) {
            dayText.setAttribute('fill', '#0a2342');
            dayText.setAttribute('style', 'text-shadow: 0 1px 2px #e3f6ff, 0 0 2px #e3f6ff;');
          } else {
            dayText.setAttribute('fill', '#222');
            dayText.setAttribute('style', 'text-shadow: 0 1px 2px #fff, 0 0 2px #fff;');
          }
          dayText.setAttribute('text-anchor', 'middle');
          dayText.setAttribute('dominant-baseline', 'middle');
          dayText.setAttribute('pointer-events', 'none');
          dayText.textContent = dayCount;
          svg.appendChild(rect);
          svg.appendChild(dayText);
          dayCount++;
        }
      }
      svgContainer.appendChild(svg);
    }
    
    // Navigation event listeners
    prevBtn.addEventListener('click', () => {
      currentMonth--;
      if (currentMonth < 0) {
        currentMonth = 11;
        currentYearState--;
      }
      renderMonth(currentMonth, currentYearState);
    });
    
    nextBtn.addEventListener('click', () => {
      currentMonth++;
      if (currentMonth > 11) {
        currentMonth = 0;
        currentYearState++;
      }
      renderMonth(currentMonth, currentYearState);
    });
    
    // Initial render
    renderMonth(currentMonth, currentYearState);
    
    console.log('Custom month heatmap rendered successfully');
  }

  // Initialize the page
  init();
}); 