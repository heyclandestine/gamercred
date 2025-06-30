// Games Module
window.gamesModule = {
  searchQuery: '',

  async load() {
    try {
      this.setupEventListeners();
      await this.loadGames();
    } catch (error) {
      console.error('Failed to load games:', error);
      if (window.app) {
        window.app.showNotification('Failed to load games', 'error');
      }
    }
  },

  setupEventListeners() {
    const searchInput = document.getElementById('games-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value;
        this.debounceSearch();
      });
    }
  },

  debounceSearch() {
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.loadGames();
    }, 300);
  },

  async loadGames() {
    try {
      const gamesGrid = document.getElementById('games-grid');
      const loadingElement = document.getElementById('games-loading');
      
      if (loadingElement) loadingElement.style.display = 'flex';
      if (gamesGrid) gamesGrid.style.display = 'none';

      let endpoint = '/api/all-games';
      if (this.searchQuery.trim()) {
        endpoint = `/api/search-games?q=${encodeURIComponent(this.searchQuery)}`;
      }

      const response = await window.app.apiCall(endpoint);
      
      if (response.success && response.games) {
        this.renderGames(response.games);
      } else {
        this.showNoGames();
      }
    } catch (error) {
      console.error('Failed to load games data:', error);
      this.showNoGames();
    }
  },

  renderGames(games) {
    const gamesGrid = document.getElementById('games-grid');
    const loadingElement = document.getElementById('games-loading');
    
    if (!gamesGrid) return;

    if (loadingElement) loadingElement.style.display = 'none';
    gamesGrid.style.display = 'grid';

    if (!games || games.length === 0) {
      this.showNoGames();
      return;
    }

    const gamesHTML = games.map(game => `
      <div class="game-card" onclick="window.gamesModule.openGame('${game.name}')">
        <div class="game-card-image">
          ${game.box_art_url ? 
            `<img src="${game.box_art_url}" alt="${game.name}" onerror="this.style.display='none'">` :
            `<i class="fas fa-gamepad"></i>`
          }
        </div>
        <div class="game-card-content">
          <div class="game-card-title">${game.name}</div>
          <div class="game-card-stats">
            <span>${game.credits_per_hour} cred/hour</span>
            <span>${game.total_hours?.toFixed(1) || '0'}h played</span>
          </div>
        </div>
      </div>
    `).join('');

    gamesGrid.innerHTML = gamesHTML;
  },

  openGame(gameName) {
    // Open game details in new window or navigate to game page
    const encodedGame = encodeURIComponent(gameName);
    const gameUrl = `${window.app.settings.apiUrl}/game.html?game=${encodedGame}`;
    window.open(gameUrl, '_blank');
  },

  showNoGames() {
    const gamesGrid = document.getElementById('games-grid');
    const loadingElement = document.getElementById('games-loading');
    
    if (loadingElement) loadingElement.style.display = 'none';
    if (gamesGrid) {
      gamesGrid.style.display = 'block';
      gamesGrid.innerHTML = `
        <div class="no-games">
          <i class="fas fa-gamepad"></i>
          <p>${this.searchQuery ? 'No games found' : 'No games available'}</p>
        </div>
      `;
    }
  }
}; 