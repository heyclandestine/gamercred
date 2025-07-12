// All Games Page JavaScript

let games = [];
let currentSort = {
    field: 'name',
    direction: 'asc'
};

// Fetch all games
async function fetchGames() {
    try {
        console.log('Fetching games from /api/all-games...');
        // Clear any cached games data
        localStorage.removeItem('popular_weekly');
        localStorage.removeItem('popular_monthly');
        localStorage.removeItem('popular_alltime');
        
        // Force a fresh fetch by adding a timestamp
        const response = await fetch(`/api/all-games?t=${Date.now()}`);
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.error) {
            throw new Error(data.error);
        }
        games = Array.isArray(data) ? data : [];
        console.log('Processed games array:', games);
        renderGames();
        // Set initial sort direction icon
        const icon = document.querySelector('#sortDirection i');
        icon.className = 'fas fa-sort-amount-up';
    } catch (error) {
        console.error('Error fetching games:', error);
        document.getElementById('gamesGrid').innerHTML = '<div class="error-message">Error loading games. Please try again later.</div>';
    }
}

// Format game title to title case
function toTitleCase(str) {
    if (!str) return '';
    
    // First, capitalize the first letter of the entire string
    let name = str[0].toUpperCase() + str.slice(1);
    
    // Then capitalize each word, preserving Roman numerals
    const words = name.split(' ');
    const romanNumerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV'];
    
    return words.map(word => {
        if (romanNumerals.includes(word.toUpperCase())) {
            return word.toUpperCase();
        }
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    }).join(' ');
}

// Format date to readable format
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

// Render games with current sort and filter
function renderGames() {
    const searchTerm = document.getElementById('gameSearch').value.toLowerCase();
    
    const filteredGames = games.filter(game => 
        game.name.toLowerCase().includes(searchTerm)
    );

    const sortedGames = sortGames(filteredGames);
    
    const gamesGrid = document.getElementById('gamesGrid');
    gamesGrid.innerHTML = '';

    if (sortedGames.length === 0) {
        gamesGrid.innerHTML = '<div class="no-games">No games found</div>';
        return;
    }

    sortedGames.forEach(game => {
        const gameCard = document.createElement('div');
        gameCard.className = 'game-card list-view';
        
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
        mediaElement.className = 'game-card-image';
        mediaElement.alt = game.name;

        const cphValue = Math.round(game.credits_per_hour || 0);
        gameCard.innerHTML = `
            <a href="/pages/game.html?game=${encodeURIComponent(game.name)}" class="game-card-link">
            </a>
            <div class="game-card-info">
                <h3 class="game-card-title">
                    <a href="/pages/game.html?game=${encodeURIComponent(game.name)}" class="game-title-link">${game.name}</a>
                </h3>
                <div class="game-card-stats">
                    <div class="stat">
                        <span class="stat-label">CPH</span>
                        <span class="stat-value">${cphValue}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Hours</span>
                        <span class="stat-value">${formatNumber(game.total_hours || 0)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Players</span>
                        <span class="stat-value">${formatNumber(game.unique_players || 0)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Released</span>
                        <span class="stat-value">${game.release_date ? new Date(game.release_date).getFullYear() : 'N/A'}</span>
                    </div>
                </div>
            </div>
        `;
        
        const link = gameCard.querySelector('.game-card-link');
        link.insertBefore(mediaElement, link.firstChild);

        // Always add CPH indicator, CSS will handle visibility
        const cphIndicator = document.createElement('div');
        cphIndicator.className = 'cph-indicator';
        
        // Add half-life information to CPH indicator if available
        if (game.half_life_hours) {
            cphIndicator.textContent = `${cphValue} CPH (${game.half_life_hours}h half-life)`;
            cphIndicator.title = `CPH halves every ${game.half_life_hours} hours`;
        } else {
            cphIndicator.textContent = `${cphValue} CPH`;
            cphIndicator.title = 'No CPH decay';
        }
        
        gameCard.appendChild(cphIndicator);

        gamesGrid.appendChild(gameCard);
    });
}

// Sort games based on current sort settings
function sortGames(games) {
    return [...games].sort((a, b) => {
        let valueA = a[currentSort.field];
        let valueB = b[currentSort.field];

        // Handle release date comparisons
        if (currentSort.field === 'release_date') {
            valueA = valueA ? new Date(valueA).getTime() : (currentSort.direction === 'asc' ? Infinity : -Infinity);
            valueB = valueB ? new Date(valueB).getTime() : (currentSort.direction === 'asc' ? Infinity : -Infinity);
        }
        // Handle string comparisons
        else if (typeof valueA === 'string') {
            valueA = valueA.toLowerCase();
            valueB = valueB.toLowerCase();
        }

        // Handle null/undefined values
        if (valueA === null || valueA === undefined) valueA = currentSort.direction === 'asc' ? Infinity : -Infinity;
        if (valueB === null || valueB === undefined) valueB = currentSort.direction === 'asc' ? Infinity : -Infinity;

        if (valueA < valueB) return currentSort.direction === 'asc' ? -1 : 1;
        if (valueA > valueB) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });
}

// Format numbers with commas
function formatNumber(num) {
    return num.toLocaleString();
}

// Event Listeners
document.getElementById('sortBy').addEventListener('change', (e) => {
    currentSort.field = e.target.value;
    // Set descending as default for all categories except name
    currentSort.direction = e.target.value === 'name' ? 'asc' : 'desc';
    const icon = document.querySelector('#sortDirection i');
    icon.className = currentSort.direction === 'asc' ? 'fas fa-sort-amount-up' : 'fas fa-sort-amount-down';
    renderGames();
});

document.getElementById('sortDirection').addEventListener('click', () => {
    currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    const icon = document.querySelector('#sortDirection i');
    icon.className = currentSort.direction === 'asc' ? 'fas fa-sort-amount-down' : 'fas fa-sort-amount-up';
    renderGames();
});

document.getElementById('gameSearch').addEventListener('input', () => {
    renderGames();
});

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

    // Existing all games page logic
    fetchGames();

    // Add view toggle functionality
    const viewButtons = document.querySelectorAll('.view-btn');
    const gamesGrid = document.querySelector('.games-grid');

    viewButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Update active button
            viewButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update view
            const view = button.dataset.view;
            gamesGrid.className = `games-grid ${view}-view`;

            // Update game cards
            const gameCards = document.querySelectorAll('.game-card');
            gameCards.forEach(card => {
                card.className = `game-card ${view}-view`;
            });
        });
    });

    // Add search functionality
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const gameCards = document.querySelectorAll('.game-card');
            const currentView = document.querySelector('.games-grid').classList.contains('grid-view') ? 'grid-view' : 'list-view';
            
            gameCards.forEach(card => {
                const gameName = card.querySelector('.game-card-title').textContent.toLowerCase();
                if (gameName.includes(searchTerm)) {
                    card.style.display = '';
                    // Ensure the view class is preserved
                    card.className = `game-card ${currentView}`;
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
});

function toggleView(view) {
    const grid = document.querySelector('.games-grid');
    const cards = document.querySelectorAll('.game-card');
    
    if (view === 'grid') {
        grid.classList.add('grid-view');
        cards.forEach(card => {
            card.classList.remove('list-view');
            card.classList.add('grid-view');
        });
    } else {
        grid.classList.remove('grid-view');
        cards.forEach(card => {
            card.classList.remove('grid-view');
            card.classList.add('list-view');
        });
    }
    
    // Re-render games to update CPH indicators
    renderGames();
} 