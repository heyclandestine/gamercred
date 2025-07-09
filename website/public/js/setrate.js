// Setrate Page JavaScript
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const gameSearch = document.getElementById('game-search');
    const gameAutocompleteDropdown = document.getElementById('game-autocomplete-dropdown');
    const selectedGameDisplay = document.getElementById('selected-game-display');
    const selectedGameCover = document.getElementById('selected-game-cover');
    const selectedGameName = document.getElementById('selected-game-name');
    const currentCph = document.getElementById('current-cph');
    const currentHalfLife = document.getElementById('current-half-life');
    const cphInput = document.getElementById('cph-input');
    const halfLifeInput = document.getElementById('half-life-input');
    const boxArtUrlInput = document.getElementById('box-art-url');
    const saveRateBtn = document.getElementById('save-rate-btn');
    const resetFormBtn = document.getElementById('reset-form-btn');
    const similarGamesGrid = document.getElementById('similar-games-grid');
    const recentChangesList = document.getElementById('recent-changes-list');
    const toastContainer = document.getElementById('toast-container');

    // State
    let currentUser = null;
    let selectedGame = null;
    let searchTimeout = null;
    let allGames = [];

    // Initialize
    init();

    async function init() {
        await checkAuth();
        await loadAllGames();
        await loadRecentChanges();
        setupEventListeners();
    }

    async function checkAuth() {
        try {
            const response = await fetch('/api/user');
            if (response.ok) {
                currentUser = await response.json();
            } else {
                showToast('Please log in to use this feature', 'warning');
            }
        } catch (error) {
            console.error('Auth check failed:', error);
        }
    }

    async function loadAllGames() {
        try {
            const response = await fetch('/api/all-games');
            if (response.ok) {
                allGames = await response.json();
            }
        } catch (error) {
            console.error('Failed to load games:', error);
        }
    }

    function setupEventListeners() {
        // Game search
        gameSearch.addEventListener('input', handleGameSearch);
        gameSearch.addEventListener('focus', () => {
            if (gameSearch.value.trim()) {
                showAutocomplete();
            }
        });

        // CPH input for similar games
        cphInput.addEventListener('input', debounce(handleCphInput, 300));

        // Form actions
        saveRateBtn.addEventListener('click', handleSaveRate);
        resetFormBtn.addEventListener('click', handleResetForm);

        // Click outside to close autocomplete
        document.addEventListener('click', (e) => {
            if (!gameSearch.contains(e.target) && !gameAutocompleteDropdown.contains(e.target)) {
                hideAutocomplete();
            }
        });
    }

    function handleGameSearch() {
        const query = gameSearch.value.trim();
        
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        if (query.length < 2) {
            hideAutocomplete();
            return;
        }

        searchTimeout = setTimeout(() => {
            searchGames(query);
        }, 200);
    }

    async function searchGames(query) {
        try {
            const response = await fetch(`/api/search-games?query=${encodeURIComponent(query)}`);
            if (response.ok) {
                const games = await response.json();
                displayAutocomplete(games);
            }
        } catch (error) {
            console.error('Search failed:', error);
        }
    }

    // Helper to check if a URL is a video
    function isVideoUrl(url) {
        return url && /\.(mp4|webm|ogg)$/i.test(url);
    }

    // --- Update displayAutocomplete to support video covers and open in new tab ---
    function displayAutocomplete(games) {
        gameAutocompleteDropdown.innerHTML = '';
        if (games.length === 0) {
            gameAutocompleteDropdown.innerHTML = '<div class="autocomplete-item">No games found</div>';
            showAutocomplete();
            return;
        }
        games.slice(0, 8).forEach(game => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            let coverHtml = '';
            if (isVideoUrl(game.box_art_url)) {
                coverHtml = `
                    <span class="autocomplete-avatar video-cover">
                        <video src="${game.box_art_url}" autoplay muted loop playsinline poster="https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png"></video>
                    </span>
                `;
            } else {
                coverHtml = `<img src="${game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'}" alt="${game.name}" class="autocomplete-avatar" onerror="this.src='https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'">`;
            }
            item.innerHTML = `
                ${coverHtml}
                <span class="autocomplete-title">${game.name}</span>
            `;
            // Select game on click
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                selectGame(game);
            });
            gameAutocompleteDropdown.appendChild(item);
        });
        showAutocomplete();
    }

    function showAutocomplete() {
        gameAutocompleteDropdown.classList.add('active');
    }

    function hideAutocomplete() {
        gameAutocompleteDropdown.classList.remove('active');
    }

    async function selectGame(game) {
        selectedGame = game;
        gameSearch.value = game.name;
        hideAutocomplete();

        // Load game details
        try {
            const response = await fetch(`/api/game?game=${encodeURIComponent(game.name)}`);
            if (response.ok) {
                const gameDetails = await response.json();
                displaySelectedGame(gameDetails);
                populateForm(gameDetails);
            }
        } catch (error) {
            console.error('Failed to load game details:', error);
            showToast('Failed to load game details', 'error');
        }
    }

    // --- Update displaySelectedGame to support video covers ---
    function displaySelectedGame(game) {
        if (isVideoUrl(game.box_art_url)) {
            selectedGameCover.outerHTML = `<span id="selected-game-cover" class="selected-game-cover video-cover"><video src="${game.box_art_url}" autoplay muted loop playsinline poster="https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png"></video></span>`;
        } else {
            selectedGameCover.outerHTML = `<img id="selected-game-cover" src="${game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'}" alt="Game Cover" class="selected-game-cover" onerror="this.src='https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'">`;
        }
        // Update references
        window.selectedGameCover = document.getElementById('selected-game-cover');
        selectedGameName.textContent = game.name;
        currentCph.textContent = game.credits_per_hour.toFixed(1);
        currentHalfLife.textContent = game.half_life_hours ? `${game.half_life_hours}h` : 'None';
        selectedGameDisplay.style.display = 'block';
    }

    function populateForm(game) {
        cphInput.value = game.credits_per_hour;
        halfLifeInput.value = game.half_life_hours || '';
        boxArtUrlInput.value = game.box_art_url || '';
    }

    function handleCphInput() {
        const cph = parseFloat(cphInput.value);
        if (cph && cph > 0) {
            findSimilarGames(cph);
        } else {
            showNoSimilarGames();
        }
    }

    function findSimilarGames(targetCph) {
        const tolerance = 5; // ±5 CPH tolerance
        const similarGames = allGames.filter(game => {
            const diff = Math.abs(game.credits_per_hour - targetCph);
            return diff <= tolerance && game.name !== selectedGame?.name;
        });

        // Sort by CPH similarity
        similarGames.sort((a, b) => {
            const diffA = Math.abs(a.credits_per_hour - targetCph);
            const diffB = Math.abs(b.credits_per_hour - targetCph);
            return diffA - diffB;
        });

        displaySimilarGames(similarGames.slice(0, 16));
    }

    // --- Update displaySimilarGames to support video covers and open in new tab ---
    function displaySimilarGames(games) {
        if (games.length === 0) {
            showNoSimilarGames();
            return;
        }
        similarGamesGrid.innerHTML = games.map(game => {
            let coverHtml = '';
            if (isVideoUrl(game.box_art_url)) {
                coverHtml = `
                    <span class="similar-game-cover video-cover">
                        <video src="${game.box_art_url}" autoplay muted loop playsinline poster="https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png"></video>
                    </span>
                `;
            } else {
                coverHtml = `<img src="${game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'}" alt="${game.name}" class="similar-game-cover" onerror="this.src='https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'">`;
            }
            return `
                <div class="similar-game-card" style="cursor:pointer" onclick="window.open('/pages/game.html?game=${encodeURIComponent(game.name)}', '_blank')">
                    ${coverHtml}
                    <div class="similar-game-name">${game.name}</div>
                    <div class="similar-game-cph">${game.credits_per_hour.toFixed(1)} CPH</div>
                    <div class="similar-game-half-life">
                        ${game.half_life_hours ? `${game.half_life_hours}h half-life` : 'No decay'}
                    </div>
                </div>
            `;
        }).join('');
    }

    function showNoSimilarGames() {
        similarGamesGrid.innerHTML = `
            <div class="no-similar-games">
                <i class="fas fa-info-circle"></i>
                <p>No games found with similar CPH rates</p>
            </div>
        `;
    }

    // Global function for similar game selection
    window.selectGameFromSimilar = function(gameName) {
        const game = allGames.find(g => g.name === gameName);
        if (game) {
            selectGame(game);
        }
    };

    async function handleSaveRate() {
        if (!currentUser) {
            showToast('Please log in to save changes', 'warning');
            return;
        }

        const gameName = gameSearch.value.trim();
        if (!gameName) {
            showToast('Please enter a game name', 'warning');
            return;
        }

        const cph = parseFloat(cphInput.value);
        const halfLife = parseFloat(halfLifeInput.value) || 0;
        const boxArtUrl = boxArtUrlInput.value.trim();

        if (!cph || cph < 0.1) {
            showToast('CPH must be at least 0.1', 'error');
            return;
        }

        saveRateBtn.disabled = true;
        saveRateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        try {
            // Save CPH
            const cphResponse = await fetch('/api/set-game-rate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: currentUser.id,
                    game_name: gameName,
                    cph: cph,
                    half_life: halfLife,
                    box_art_url: boxArtUrl
                })
            });

            if (cphResponse.ok) {
                showToast('Game rate updated successfully!', 'success');
                await loadRecentChanges();
                
                // Update current display
                currentCph.textContent = cph.toFixed(1);
                currentHalfLife.textContent = halfLife > 0 ? `${halfLife}h` : 'None';
                
                // Update selected game object
                selectedGame.credits_per_hour = cph;
                selectedGame.half_life_hours = halfLife > 0 ? halfLife : null;
                selectedGame.box_art_url = boxArtUrl;
                
                // Update box art if provided
                if (boxArtUrl) {
                    selectedGameCover.src = boxArtUrl;
                }
            } else {
                const error = await cphResponse.json();
                showToast(error.error || 'Failed to update game rate', 'error');
            }
        } catch (error) {
            console.error('Save failed:', error);
            showToast('Failed to save changes', 'error');
        } finally {
            saveRateBtn.disabled = false;
            saveRateBtn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
        }
    }

    function handleResetForm() {
        if (selectedGame) {
            populateForm(selectedGame);
        } else {
            cphInput.value = '';
            halfLifeInput.value = '';
            boxArtUrlInput.value = '';
        }
        showToast('Form reset', 'warning');
    }

    async function loadRecentChanges() {
        try {
            const response = await fetch('/api/recent-rate-changes');
            if (response.ok) {
                const changes = await response.json();
                displayRecentChanges(changes);
            }
        } catch (error) {
            console.error('Failed to load recent changes:', error);
            recentChangesList.innerHTML = '<div class="error-message">Failed to load recent changes</div>';
        }
    }

    function displayRecentChanges(changes) {
        if (changes.length === 0) {
            recentChangesList.innerHTML = '<div class="no-changes">No recent rate changes</div>';
            return;
        }

        recentChangesList.innerHTML = changes.map(change => `
            <div class="recent-change-item">
                <a href="/pages/game.html?game=${encodeURIComponent(change.game_name)}" target="_blank" class="recent-change-cover-link">
                    <img src="${change.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'}" 
                         alt="${change.game_name}" class="recent-change-cover"
                         onerror="this.src='https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'">
                </a>
                <div class="recent-change-details">
                    <a href="/pages/game.html?game=${encodeURIComponent(change.game_name)}" target="_blank" class="recent-change-game-link">
                        <div class="recent-change-game">${change.game_name}</div>
                    </a>
                    <div class="recent-change-info">
                        CPH: ${change.current_cph.toFixed(1)}
                        ${change.current_half_life ? `<br>Half-life: ${change.current_half_life}h` : '<br>Half-life: None'}
                    </div>
                    <div class="recent-change-time">Set by ${change.user_name}</div>
                </div>
            </div>
        `).join('');
    }

    function formatTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return time.toLocaleDateString();
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
        `;

        toastContainer.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Auto remove
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    async function loadCphDistribution() {
        if (allGames.length === 0) return;

        const cphs = allGames.map(game => game.credits_per_hour).filter(cph => cph > 0);
        
        if (cphs.length === 0) return;

        // Calculate statistics
        const avgCph = cphs.reduce((sum, cph) => sum + cph, 0) / cphs.length;
        const sortedCphs = [...cphs].sort((a, b) => a - b);
        const medianCph = sortedCphs.length % 2 === 0 
            ? (sortedCphs[sortedCphs.length / 2 - 1] + sortedCphs[sortedCphs.length / 2]) / 2
            : sortedCphs[Math.floor(sortedCphs.length / 2)];

        // Count games in each range
        const lowCount = cphs.filter(cph => cph >= 0.1 && cph <= 0.5).length;
        const mediumCount = cphs.filter(cph => cph >= 0.6 && cph <= 1.5).length;
        const highCount = cphs.filter(cph => cph >= 1.6).length;

        // Update UI
        document.getElementById('avg-cph').textContent = avgCph.toFixed(2);
        document.getElementById('median-cph').textContent = medianCph.toFixed(2);
        document.getElementById('total-games').textContent = allGames.length;
        document.getElementById('low-cph-count').textContent = lowCount;
        document.getElementById('medium-cph-count').textContent = mediumCount;
        document.getElementById('high-cph-count').textContent = highCount;
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}); 

// === CPH Calculator Logic ===
(function() {
    const relevanceInput = document.getElementById('calc-relevance');
    const popularityInput = document.getElementById('calc-popularity');
    const importanceInput = document.getElementById('calc-importance');
    const accessibilityInput = document.getElementById('calc-accessibility');
    const ageInput = document.getElementById('calc-age');
    const calcBtn = document.getElementById('calc-cph-btn');
    const resultSpan = document.getElementById('cph-calc-value');
    const copyBtn = document.getElementById('copy-cph-btn');
    const cphInput = document.getElementById('cph-input');

    function clamp(val) {
        val = Number(val);
        if (isNaN(val)) return 0;
        return Math.max(0, Math.min(100, val));
    }

    function calculateCPH() {
        const relevance = clamp(relevanceInput.value);
        const popularity = clamp(popularityInput.value);
        const importance = clamp(importanceInput.value);
        const accessibility = clamp(accessibilityInput.value);
        const age = clamp(ageInput.value);
        const cph = 5*((relevance * 0.4) + (popularity * 0.25) + (importance * 0.15) + (accessibility * 0.1) + (age * 0.1));
        return Math.round(cph);
    }

    calcBtn.addEventListener('click', function() {
        const cph = calculateCPH();
        resultSpan.textContent = cph.toFixed(1);
    });

    copyBtn.addEventListener('click', function() {
        const cph = calculateCPH();
        if (cphInput) {
            cphInput.value = cph.toFixed(1);
            // Briefly highlight the input
            cphInput.classList.add('highlight-cph');
            setTimeout(() => cphInput.classList.remove('highlight-cph'), 800);
        }
    });

    // Optional: allow pressing Enter in any field to calculate
    document.getElementById('cph-calc-form').addEventListener('submit', function(e) {
        e.preventDefault();
        calcBtn.click();
    });
})(); 