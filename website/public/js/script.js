// console.log('Script loaded');
document.addEventListener('DOMContentLoaded', function() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('just_logged_in')) {
    localStorage.removeItem('selected-theme');
    // Optionally, remove the param from the URL for cleanliness
    window.history.replaceState({}, document.title, window.location.pathname);
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
      if (authContainer) {
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
      }
    })
    .catch(error => {
      // console.log('Not authenticated:', error);
    });

  // Fetch and display recent bonuses
  const bonusesSection = document.querySelector('.bonuses');
  if (bonusesSection) {
    // Try to show cached data instantly
    const cacheKey = 'recent_bonuses';
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        const bonuses = JSON.parse(cached);
        renderBonuses(bonuses);
      } catch (e) {}
    }

    // Always fetch fresh data in the background
    fetch('/api/recent-bonuses')
      .then(res => res.json())
      .then(bonuses => {
        renderBonuses(bonuses);
        localStorage.setItem(cacheKey, JSON.stringify(bonuses));
      })
      .catch(error => {
        // console.error('Error fetching bonuses:', error);
        const spinner = bonusesSection.querySelector('.loading-spinner');
        if (spinner) {
          spinner.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading bonuses';
        }
      });
  }

  function renderBonuses(bonuses) {
    const bonusesSection = document.querySelector('.bonuses');
    if (!bonusesSection) return;
    
    const spinner = bonusesSection.querySelector('.loading-spinner');
    if (spinner) spinner.remove();
    
    // Clear previous bonuses list to prevent duplicates
    const oldUl = bonusesSection.querySelector('ul');
    if (oldUl) oldUl.remove();
    
    const ul = document.createElement('ul');
    if (!bonuses || bonuses.length === 0) {
      ul.innerHTML = '<li>No recent bonuses</li>';
    } else {
      bonuses.forEach(bonus => {
        const li = document.createElement('li');
        li.innerHTML = `
          <img class="avatar-sm" src="${bonus.avatar_url || `https://cdn.discordapp.com/embed/avatars/${parseInt(bonus.user_id.slice(-1)) % 6}.png`}" alt="${bonus.username}">
          <a class="user-link" href="/pages/user.html?user=${String(bonus.user_id)}">${bonus.username}</a> earned 
          <span class="bonus-credits">${bonus.credits.toLocaleString()} cred</span>
          <span class="bonus"><i class="fas fa-bolt"></i> "${bonus.reason}"</span>
        `;
        ul.appendChild(li);
      });
    }
    bonusesSection.appendChild(ul);
  }

  // Discord login button mockup
  const loginBtn = document.querySelector('.discord-login');
  if (loginBtn) {
    loginBtn.addEventListener('click', function() {
      alert('Discord login coming soon!');
    });
  }

  // Reaction logic: one heart and one dropdown per card
  document.querySelectorAll('.activity-card-wrap').forEach(cardWrap => {
    // Heart
    const heartBtn = cardWrap.querySelector('.react-btn.react-pink');
    if (heartBtn) {
      heartBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        let countSpan = heartBtn.querySelector('.react-count');
        let count = parseInt(countSpan.textContent);
        if (heartBtn.classList.contains('active')) {
          count = Math.max(0, count - 1);
          heartBtn.classList.remove('active');
        } else {
          count = count + 1;
          heartBtn.classList.add('active');
        }
        countSpan.textContent = count;
        updateOtherReactionDisplay();
      });
    }
    // Dropdown
    const dropdownBtns = cardWrap.querySelectorAll('.react-dropdown-content .react-btn');
    dropdownBtns.forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        // Remove active from all, decrement their counts if needed
        dropdownBtns.forEach(otherBtn => {
          if (otherBtn !== btn && otherBtn.classList.contains('active')) {
            let otherCount = otherBtn.querySelector('.react-count');
            let val = parseInt(otherCount.textContent);
            otherCount.textContent = Math.max(0, val - 1);
            otherBtn.classList.remove('active');
          }
        });
        // Toggle this one
        let countSpan = btn.querySelector('.react-count');
        let count = parseInt(countSpan.textContent);
        if (btn.classList.contains('active')) {
          count = Math.max(0, count - 1);
          btn.classList.remove('active');
        } else {
          count = count + 1;
          btn.classList.add('active');
        }
        countSpan.textContent = count;
        updateOtherReactionDisplay();
      });
    });
    // Show up to 3 other reactions (besides heart) with count > 0, each with emoji and counter below
    function updateOtherReactionDisplay() {
      let display = cardWrap.querySelector('.other-reaction-display');
      if (!display) {
        display = document.createElement('span');
        display.className = 'other-reaction-display';
        const heartBtn = cardWrap.querySelector('.react-btn.react-pink');
        if (heartBtn) {
          heartBtn.parentNode.insertBefore(display, heartBtn.nextSibling);
        }
      }
      // Gather all dropdown reactions with count > 0, up to 3
      const activeReactions = [];
      dropdownBtns.forEach(btn => {
        const count = parseInt(btn.querySelector('.react-count').textContent);
        if (count > 0) {
          // Get the emoji (first span child)
          const emoji = btn.querySelector('span').textContent;
          activeReactions.push({ emoji, count });
        }
      });
      // Only show if there are any
      if (activeReactions.length === 0) {
        display.innerHTML = '';
        display.style.display = 'none';
      } else {
        display.innerHTML = activeReactions.slice(0, 3).map(r =>
          `<span class="other-emoji-bubble">
            <span class="other-emoji">${r.emoji}</span>
            <span class="other-react-count">${r.count}</span>
          </span>`
        ).join('');
        display.style.display = 'inline-flex';
      }
    }
    updateOtherReactionDisplay();
  });

  // Tab switching for leaderboard and most popular
  const allTabBtns = document.querySelectorAll('.tab-btn');
  allTabBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      // Tabs for leaderboard
      if (btn.closest('.leaderboard-tabs')) {
        document.querySelectorAll('.leaderboard-tabs .tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.leaderboard .tab-content').forEach(tc => tc.style.display = 'none');
        const tab = btn.getAttribute('data-tab');
        const tabContent = document.getElementById(tab);
        if (tabContent) {
          tabContent.style.display = '';
        }
      }
      // Tabs for most popular
      if (btn.closest('.popular-tabs')) {
        document.querySelectorAll('.popular-tabs .tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.most-popular .tab-content').forEach(tc => tc.style.display = 'none');
        const tab = btn.getAttribute('data-tab');
        const tabContent = document.getElementById(tab);
        if (tabContent) {
          tabContent.style.display = '';
        }
      }
    });
  });

  // Robust dropdown: move menu to body when open, improved auto-close on mouse leave
  let openDropdownMenu = null;
  let dropdownCloseTimeout = null;
  let overBtn = false, overMenu = false;
  document.querySelectorAll('.react-dropdown-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      // Close any open dropdown
      if (openDropdownMenu) {
        document.body.removeChild(openDropdownMenu);
        openDropdownMenu = null;
        document.querySelectorAll('.react-dropdown').forEach(drop => drop.classList.remove('open'));
      }
      const dropdown = btn.closest('.react-dropdown');
      if (dropdown) {
        dropdown.classList.toggle('open');
        if (dropdown.classList.contains('open')) {
          // Clone the menu and append to body
          const menu = dropdown.querySelector('.react-dropdown-content.horizontal');
          if (menu) {
            const menuClone = menu.cloneNode(true);
            // Wrap in .dropdown-inner
            const inner = document.createElement('div');
            inner.className = 'dropdown-inner';
            while (menuClone.firstChild) inner.appendChild(menuClone.firstChild);
            menuClone.appendChild(inner);
            menuClone.style.display = 'inline-flex';
            menuClone.style.position = 'absolute';
            menuClone.style.zIndex = 2000;
            menuClone.style.background = 'transparent';
            menuClone.style.boxShadow = 'none';
            menuClone.style.borderRadius = '0';
            menuClone.style.padding = '0';
            menuClone.style.margin = '0';
            menuClone.style.width = 'auto';
            menuClone.style.minWidth = '0';
            menuClone.style.maxWidth = 'none';
            // Position below the button
            const rect = btn.getBoundingClientRect();
            menuClone.style.left = rect.left + window.scrollX + 'px';
            menuClone.style.top = rect.bottom + window.scrollY + 6 + 'px';
            document.body.appendChild(menuClone);
            openDropdownMenu = menuClone;
            // Add click handlers to the cloned buttons
            const origBtns = menu.querySelectorAll('.react-btn');
            const cloneBtns = inner.querySelectorAll('.react-btn');
            cloneBtns.forEach((cloneBtn, i) => {
              cloneBtn.addEventListener('click', function(ev) {
                ev.stopPropagation();
                if (origBtns[i]) {
                  origBtns[i].click();
                }
                // Close after click
                if (openDropdownMenu) {
                  document.body.removeChild(openDropdownMenu);
                  openDropdownMenu = null;
                  dropdown.classList.remove('open');
                }
              });
            });
            // Improved auto-close: only close if mouse is not over btn or menu
            function closeDropdown() {
              if (openDropdownMenu) {
                document.body.removeChild(openDropdownMenu);
                openDropdownMenu = null;
                dropdown.classList.remove('open');
              }
            }
            let closeTimeout = null;
            function scheduleClose() {
              closeTimeout = setTimeout(() => {
                if (!overBtn && !overMenu) closeDropdown();
              }, 200);
            }
            function cancelClose() {
              if (closeTimeout) clearTimeout(closeTimeout);
            }
            btn.addEventListener('mouseover', () => { overBtn = true; cancelClose(); });
            btn.addEventListener('mouseout', () => { overBtn = false; scheduleClose(); });
            menuClone.addEventListener('mouseover', () => { overMenu = true; cancelClose(); });
            menuClone.addEventListener('mouseout', () => { overMenu = false; scheduleClose(); });
          }
        }
      }
    });
  });
  // Close dropdowns when clicking outside
  document.addEventListener('click', function() {
    if (openDropdownMenu) {
      document.body.removeChild(openDropdownMenu);
      openDropdownMenu = null;
      document.querySelectorAll('.react-dropdown').forEach(drop => drop.classList.remove('open'));
    }
  });

  // Carousel arrow scroll logic
  const activityWide = document.querySelector('.activity-wide');
  if (activityWide) {
    const carousel = activityWide.querySelector('.activity-carousel');
    const leftArrow = activityWide.querySelector('.carousel-arrow.left');
    const rightArrow = activityWide.querySelector('.carousel-arrow.right');
    if (carousel && leftArrow && rightArrow) {
      function scrollByCard(dir) {
        const cardWidth = carousel.querySelector('.activity-card-wrap')?.offsetWidth || 0;
        const scrollAmount = cardWidth * dir;
        carousel.scrollBy({ left: scrollAmount, behavior: 'smooth' });
      }
      leftArrow.addEventListener('click', () => scrollByCard(-1));
      rightArrow.addEventListener('click', () => scrollByCard(1));
    }
  }

  // Search functionality
  const searchInput = document.querySelector('.search-bar');
  const searchDropdown = document.querySelector('.navbar .autocomplete-dropdown');
  if (searchInput && searchDropdown) {
    let activeIndex = -1;
    let results = [];

    function renderDropdown() {
      if (results.length === 0) {
        searchDropdown.style.display = 'none';
        return;
      }
      searchDropdown.innerHTML = `
        <ul class="autocomplete-list">
          ${results.map((result, index) => `
            <li class="autocomplete-item ${index === activeIndex ? 'active' : ''}" data-index="${index}">
              ${result.type === 'game' && result.avatar && result.avatar.endsWith('.webm') 
                ? `<video class="autocomplete-avatar" src="${result.avatar}" autoplay loop muted playsinline></video>`
                : `<img src="${result.avatar}" alt="${result.name}" class="autocomplete-avatar">`}
              <span class="autocomplete-title">${result.name}</span>
              <span class="autocomplete-type">${result.type === 'game' ? 'Game' : 'User'}</span>
            </li>
          `).join('')}
        </ul>
      `;
      searchDropdown.style.display = 'block';
    }

    function fetchResults(query) {
      if (!query) {
        results = [];
        renderDropdown();
        return;
      }
      fetch(`/api/search?query=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
          // Transform both games and users into the expected format
          const games = data.games.map(game => ({
            name: game.name,
            avatar: game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png',
            type: 'game'
          }));
          const users = data.users.map(user => ({
            name: user.username,
            avatar: user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png',
            type: 'user'
          }));
          results = [...games, ...users];
          renderDropdown();
        })
        .catch(error => {
          // console.error('Error fetching results:', error);
          results = [];
          renderDropdown();
        });
    }

    function updateActiveItem() {
      const items = searchDropdown.querySelectorAll('.autocomplete-item');
      items.forEach((item, index) => {
        item.classList.toggle('active', index === activeIndex);
      });
    }

    // Debounce the search
    let searchTimeout;
    searchInput.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        fetchResults(this.value);
      }, 300);
    });

    // Handle keyboard navigation
    searchInput.addEventListener('keydown', function(e) {
      if (!searchDropdown.style.display || searchDropdown.style.display === 'none') return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          activeIndex = Math.min(activeIndex + 1, results.length - 1);
          updateActiveItem();
          break;
        case 'ArrowUp':
          e.preventDefault();
          activeIndex = Math.max(activeIndex - 1, -1);
          updateActiveItem();
          break;
        case 'Enter':
          e.preventDefault();
          if (activeIndex >= 0 && activeIndex < results.length) {
            const result = results[activeIndex];
            if (result.type === 'game') {
              window.location.href = `/pages/game.html?game=${encodeURIComponent(result.name)}`;
            } else {
              window.location.href = `/pages/user.html?user=${result.id}`;
            }
          }
          break;
        case 'Escape':
          e.preventDefault();
          searchDropdown.style.display = 'none';
          break;
      }
    });

    // Handle clicks on dropdown items
    searchDropdown.addEventListener('click', function(e) {
      const item = e.target.closest('.autocomplete-item');
      if (item) {
        const index = parseInt(item.dataset.index);
        if (index >= 0 && index < results.length) {
          const result = results[index];
          if (result.type === 'game') {
            window.location.href = `/pages/game.html?game=${encodeURIComponent(result.name)}`;
          } else {
            window.location.href = `/pages/user.html?user=${result.id}`;
          }
        }
      }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
      if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
        searchDropdown.style.display = 'none';
      }
    });
  }

  // Setup activity carousel
  const leftArrow = document.querySelector('.activity-left-arrow');
  const rightArrow = document.querySelector('.activity-right-arrow');
  const activityCarousel = document.querySelector('.activity-carousel');

  if (leftArrow && activityCarousel) {
    leftArrow.addEventListener('click', () => {
      activityCarousel.scrollBy({ left: -200, behavior: 'smooth' });
    });
  }

  if (rightArrow && activityCarousel) {
    rightArrow.addEventListener('click', () => {
      activityCarousel.scrollBy({ left: 200, behavior: 'smooth' });
    });
  }

  // Setup leaderboard tabs
  const leaderboardTabs = document.querySelectorAll('.leaderboard-tab');
  if (leaderboardTabs) {
    leaderboardTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        // Remove active class from all tabs
        leaderboardTabs.forEach(t => t.classList.remove('active'));
        // Add active class to clicked tab
        this.classList.add('active');
        // Fetch and display leaderboard data for selected timeframe
        const timeframe = this.getAttribute('data-timeframe');
        fetchLeaderboardData(timeframe);
      });
    });
  }

  // Setup popular games tabs
  const popularGamesTabs = document.querySelectorAll('.popular-games-tab');
  if (popularGamesTabs) {
    popularGamesTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        // Remove active class from all tabs
        popularGamesTabs.forEach(t => t.classList.remove('active'));
        // Add active class to clicked tab
        this.classList.add('active');
        // Fetch and display popular games data for selected timeframe
        const timeframe = this.getAttribute('data-timeframe');
        fetchPopularGamesData(timeframe);
      });
    });
  }

  // Autocomplete for log game form (game name input)
  (function() {
    const gameNameInput = document.getElementById('game-name');
    if (!gameNameInput) return;

    // Remove any existing global dropdown
    let globalDropdown = document.getElementById('global-autocomplete-dropdown');
    if (globalDropdown) globalDropdown.remove();

    // Create dropdown as a direct child of body
    globalDropdown = document.createElement('div');
    globalDropdown.id = 'global-autocomplete-dropdown';
    globalDropdown.className = 'autocomplete-dropdown';
    globalDropdown.style.position = 'absolute';
    globalDropdown.style.display = 'none';
    globalDropdown.style.zIndex = '2147483647';
    document.body.appendChild(globalDropdown);

    let results = [];
    let activeIndex = -1;
    let lastQuery = '';
    let debounceTimeout;

    function positionDropdown() {
      const rect = gameNameInput.getBoundingClientRect();
      globalDropdown.style.left = rect.left + window.scrollX + 'px';
      globalDropdown.style.top = rect.bottom + window.scrollY + 2 + 'px';
      globalDropdown.style.width = rect.width + 'px';
    }

    function renderDropdown(results) {
      if (results.length === 0) {
        globalDropdown.style.display = 'none';
        return;
      }
      globalDropdown.innerHTML = `
        <ul class="autocomplete-list">
          ${results.map((result, index) => `
            <li class="autocomplete-item ${index === activeIndex ? 'active' : ''}" data-index="${index}">
              ${result.avatar && result.avatar.endsWith('.webm')
                ? `<video class="autocomplete-avatar" src="${result.avatar}" autoplay loop muted playsinline></video>`
                : `<img src="${result.avatar}" alt="${result.title}" class="autocomplete-avatar">`}
              <span class="autocomplete-title">${result.title}</span>
            </li>
          `).join('')}
        </ul>
      `;
      globalDropdown.style.display = 'block';
    }

    function fetchResults(query) {
      if (!query) {
        renderDropdown([]);
        return;
      }
      fetch(`/api/search?query=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          const games = (data.games || []).map(g => ({
            title: g.name,
            avatar: g.box_art_url || '/public/placeholder.png',
          }));
          results = games;
          activeIndex = -1;
          renderDropdown(results);
        })
        .catch(() => renderDropdown([]));
    }

    gameNameInput.addEventListener('input', function(e) {
      clearTimeout(debounceTimeout);
      const query = e.target.value.trim();
      debounceTimeout = setTimeout(() => {
        lastQuery = query;
        fetchResults(query);
      }, 150);
    });

    gameNameInput.addEventListener('focus', function() {
      if (lastQuery) fetchResults(lastQuery);
      positionDropdown();
    });

    gameNameInput.addEventListener('blur', function() {
      setTimeout(() => {
        globalDropdown.style.display = 'none';
      }, 150);
    });

    globalDropdown.addEventListener('mousedown', function(e) {
      e.preventDefault();
      const item = e.target.closest('.autocomplete-item');
      if (item) {
        const idx = parseInt(item.getAttribute('data-index'), 10);
        if (results[idx]) {
          gameNameInput.value = results[idx].title;
          globalDropdown.style.display = 'none';
          gameNameInput.focus();
        }
      }
    });

    gameNameInput.addEventListener('keydown', function(e) {
      if (!results.length || globalDropdown.style.display === 'none') return;
      if (e.key === 'ArrowDown') {
        activeIndex = (activeIndex + 1) % results.length;
        renderDropdown(results);
        e.preventDefault();
      } else if (e.key === 'ArrowUp') {
        activeIndex = (activeIndex - 1 + results.length) % results.length;
        renderDropdown(results);
        e.preventDefault();
      } else if (e.key === 'Enter') {
        if (activeIndex >= 0 && results[activeIndex]) {
          gameNameInput.value = results[activeIndex].title;
          globalDropdown.style.display = 'none';
          e.preventDefault();
        }
      } else if (e.key === 'Escape') {
        globalDropdown.style.display = 'none';
      }
    });

    window.addEventListener('resize', positionDropdown);
    window.addEventListener('scroll', positionDropdown, true);
  })();

  // Autocomplete for navbar search bar
  (function() {
    // Remove index page check so this runs everywhere
    const navbarSearchInput = document.querySelector('.search-bar');
    if (!navbarSearchInput) return;

    // Remove any existing navbar dropdown
    let navbarDropdown = document.getElementById('navbar-autocomplete-dropdown');
    if (navbarDropdown) navbarDropdown.remove();

    // Create dropdown as a direct child of body
    navbarDropdown = document.createElement('div');
    navbarDropdown.id = 'navbar-autocomplete-dropdown';
    navbarDropdown.className = 'autocomplete-dropdown';
    navbarDropdown.style.position = 'absolute';
    navbarDropdown.style.display = 'none';
    navbarDropdown.style.zIndex = '2147483647';
    document.body.appendChild(navbarDropdown);

    let results = [];
    let activeIndex = -1;
    let lastQuery = '';
    let debounceTimeout;

    function positionDropdown() {
      const rect = navbarSearchInput.getBoundingClientRect();
      navbarDropdown.style.position = 'fixed';
      navbarDropdown.style.left = rect.left + 'px';
      navbarDropdown.style.top = rect.bottom + 2 + 'px';
      navbarDropdown.style.width = rect.width + 'px';
      navbarDropdown.style.border = '';
    }

    function renderDropdown({games, users}) {
      if (!games.length && !users.length) {
        navbarDropdown.style.display = 'none';
        return;
      }
      navbarDropdown.innerHTML = `
        <ul class="autocomplete-list">
          ${games.map((game, index) => `
            <li class="autocomplete-item ${index === activeIndex ? 'active' : ''}" data-index="${index}">
              ${game.avatar && game.avatar.endsWith('.webm')
                ? `<video class="autocomplete-avatar" src="${game.avatar}" autoplay loop muted playsinline></video>`
                : `<img src="${game.avatar}" alt="${game.title}" class="autocomplete-avatar">`}
              <span class="autocomplete-title">${game.title}</span>
              <span class="autocomplete-type">Game</span>
            </li>
          `).join('')}
          ${users.map((user, index) => `
            <li class="autocomplete-item ${index + games.length === activeIndex ? 'active' : ''}" data-index="${index + games.length}">
              <img src="${user.avatar}" alt="${user.title}" class="autocomplete-avatar">
              <span class="autocomplete-title">${user.title}</span>
              <span class="autocomplete-type">User</span>
            </li>
          `).join('')}
        </ul>
      `;
      navbarDropdown.style.display = 'block';
    }

    function fetchResults(query) {
      if (!query) {
        renderDropdown({games: [], users: []});
        return;
      }
      fetch(`/api/search?query=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          const games = (data.games || []).map(g => ({
            title: g.name,
            avatar: g.box_art_url || '/public/placeholder.png',
            type: 'game'
          }));
          const users = (data.users || []).map(u => ({
            title: u.username,
            avatar: u.avatar_url || '/public/placeholder.png',
            user_id: u.user_id,
            type: 'user'
          }));
          results = [...games, ...users];
          activeIndex = -1;
          renderDropdown({games, users});
        })
        .catch(() => renderDropdown({games: [], users: []}));
    }

    navbarSearchInput.addEventListener('input', function(e) {
      clearTimeout(debounceTimeout);
      const query = e.target.value.trim();
      debounceTimeout = setTimeout(() => {
        lastQuery = query;
        fetchResults(query);
      }, 150);
    });

    navbarSearchInput.addEventListener('focus', function() {
      if (lastQuery) fetchResults(lastQuery);
      positionDropdown();
    });

    navbarSearchInput.addEventListener('blur', function() {
      setTimeout(() => {
        navbarDropdown.style.display = 'none';
      }, 150);
    });

    navbarDropdown.addEventListener('mousedown', function(e) {
      e.preventDefault();
      const item = e.target.closest('.autocomplete-item');
      if (item) {
        const idx = parseInt(item.dataset.index);
        if (results[idx]) {
          const result = results[idx];
          if (result.type === 'game') {
            window.location.href = `/pages/game.html?game=${encodeURIComponent(result.title)}`;
          } else if (result.type === 'user') {
            window.location.href = `/pages/user.html?user=${result.user_id}`;
          }
        }
      }
    });

    navbarSearchInput.addEventListener('keydown', function(e) {
      const gamesCount = results.filter(r => r.type === 'game').length;
      const usersCount = results.filter(r => r.type === 'user').length;
      const total = gamesCount + usersCount;
      if (!total || navbarDropdown.style.display === 'none') return;
      if (e.key === 'ArrowDown') {
        activeIndex = (activeIndex + 1) % total;
        // Re-render with new activeIndex
        fetchResults(navbarSearchInput.value.trim());
        e.preventDefault();
      } else if (e.key === 'ArrowUp') {
        activeIndex = (activeIndex - 1 + total) % total;
        fetchResults(navbarSearchInput.value.trim());
        e.preventDefault();
      } else if (e.key === 'Enter') {
        if (activeIndex >= 0 && results[activeIndex]) {
          const result = results[activeIndex];
          if (result.type === 'game') {
            window.location.href = `/pages/game.html?game=${encodeURIComponent(result.title)}`;
          } else if (result.type === 'user') {
            window.location.href = `/pages/user.html?user=${result.user_id}`;
          }
          e.preventDefault();
        }
      } else if (e.key === 'Escape') {
        navbarDropdown.style.display = 'none';
      }
    });

    window.addEventListener('resize', positionDropdown);
    window.addEventListener('scroll', positionDropdown, true);
  })();

  // Add toast container to the body
  const toastContainer = document.createElement('div');
  toastContainer.className = 'toast-container';
  document.body.appendChild(toastContainer);

  function showToast(title, message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    const color = type === 'success' ? '#3ba55c' : '#ed4245';
    
    toast.innerHTML = `
      <i class="fas ${icon}"></i>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close">
        <i class="fas fa-times"></i>
      </button>
    `;
    
    toast.style.borderLeftColor = color;
    toast.querySelector('i').style.color = color;
    
    toastContainer.appendChild(toast);
    
    // Show the toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Add click handler to close button
    const closeButton = toast.querySelector('.toast-close');
    closeButton.addEventListener('click', () => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    });
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      if (toast.parentNode) {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
      }
    }, 5000);
  }

  // Log game form submission
  const logGameForm = document.getElementById('log-game-form');
  if (logGameForm) {
    logGameForm.addEventListener('submit', function(event) {
      event.preventDefault();
      const gameName = document.getElementById('game-name').value;
      const hours = document.getElementById('hours').value;
      const players = document.getElementById('players').value;

      fetch('/api/user')
        .then(response => {
          if (!response.ok) throw new Error('Not logged in');
          return response.json();
        })
        .then(user => {
          fetch('/api/log-game', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              user_id: user.id,
              game_name: gameName,
              hours: hours,
              players: players
            })
          })
          .then(response => response.json())
          .then(data => {
            if (data.error) {
              showToast('Error', data.error, 'error');
            } else {
              showToast('Success', `Logged ${hours} hours of ${gameName}!`);
              document.getElementById('log-game-form').reset();
            }
          })
          .catch(error => {
            // console.error('Error:', error);
            showToast('Error', 'An error occurred while logging the game session.', 'error');
          });
        })
        .catch(() => {
          showToast('Error', 'Please log in to log a game session.', 'error');
        });
    });
  }

  // Timer functionality
  (function() {
    const timerSection = document.querySelector('.timer-section');
    const timerGameNameInput = document.getElementById('timer-game-name');
    const startTimerButton = document.getElementById('start-timer');
    const stopTimerButton = document.getElementById('stop-timer');
    const pauseTimerButton = document.getElementById('pause-timer');
    const resumeTimerButton = document.getElementById('resume-timer');
    const logTimerButton = document.getElementById('log-timer');
    const timerHours = document.getElementById('timer-hours');
    const timerMinutes = document.getElementById('timer-minutes');
    const timerSeconds = document.getElementById('timer-seconds');
    const timerDisplay = document.querySelector('.timer-display');
    const timerBoxArt = document.getElementById('timer-box-art');
    const logGameCard = document.querySelector('.log-game');
    const logGameForm = document.getElementById('log-game-form');
    const signInMessage = document.querySelector('.sign-in-message');

    if (!timerGameNameInput || !startTimerButton || !stopTimerButton) return;

    let isRunning = false;
    let startTime = 0;
    let elapsedTime = 0;
    let timerInterval = null;
    let currentGame = null;
    let selectedPlayers = 1; // Store the selected players value
    let isPaused = false;
    let isLoggedIn = false;

    // Check login status on load
    fetch('/api/user')
      .then(response => {
        if (response.ok) {
          isLoggedIn = true;
          startTimerButton.disabled = false;
          if (signInMessage) signInMessage.style.display = 'none';
        } else {
          isLoggedIn = false;
          startTimerButton.disabled = true;
          startTimerButton.title = 'Please log in with Discord to use the timer';
          if (signInMessage) signInMessage.style.display = 'flex';
        }
      })
      .catch(() => {
        isLoggedIn = false;
        startTimerButton.disabled = true;
        startTimerButton.title = 'Please log in with Discord to use the timer';
        if (signInMessage) signInMessage.style.display = 'flex';
      });

    // Initialize autocomplete for timer game name input
    let results = [];
    let activeIndex = -1;
    let lastQuery = '';
    let debounceTimeout;

    // Create a separate dropdown for the timer
    const timerDropdown = document.createElement('div');
    timerDropdown.className = 'autocomplete-dropdown timer-dropdown';
    timerDropdown.style.position = 'absolute';
    timerDropdown.style.display = 'none';
    timerDropdown.style.zIndex = '2147483647';
    document.body.appendChild(timerDropdown);

    function positionDropdown() {
      const rect = timerGameNameInput.getBoundingClientRect();
      timerDropdown.style.left = rect.left + window.scrollX + 'px';
      timerDropdown.style.top = rect.bottom + window.scrollY + 2 + 'px';
      timerDropdown.style.width = rect.width + 'px';
    }

    function renderDropdown(results) {
      if (!Array.isArray(results) || results.length === 0) {
        timerDropdown.style.display = 'none';
        return;
      }

      timerDropdown.innerHTML = `
        <ul class="autocomplete-list">
          ${results.map((game, index) => `
            <li class="autocomplete-item ${index === activeIndex ? 'active' : ''}" data-index="${index}">
              ${game.box_art_url && game.box_art_url.endsWith('.webm')
                ? `<video class="autocomplete-avatar" src="${game.box_art_url}" autoplay loop muted playsinline></video>`
                : `<img src="${game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'}" 
                        alt="${game.name}" 
                        class="autocomplete-avatar"
                        onerror="this.src='https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'">`}
              <span class="autocomplete-title">${game.name}</span>
            </li>
          `).join('')}
        </ul>
      `;
      timerDropdown.style.display = 'block';
    }

    timerGameNameInput.addEventListener('input', function() {
      const query = this.value.trim();
      if (query === lastQuery) return;
      lastQuery = query;

      clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        if (query.length < 2) {
          renderDropdown([]);
          return;
        }

        fetch(`/api/search-games?query=${encodeURIComponent(query)}`)
          .then(response => response.json())
          .then(data => {
            results = Array.isArray(data) ? data : [];
            activeIndex = -1;
            renderDropdown(results);
            positionDropdown();
          })
          .catch(error => {
            // console.error('Error fetching game suggestions:', error);
            renderDropdown([]);
          });
      }, 300);
    });

    timerGameNameInput.addEventListener('keydown', function(e) {
      if (timerDropdown.style.display === 'none') return;

      const items = timerDropdown.querySelectorAll('.autocomplete-item');
      if (items.length === 0) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          activeIndex = (activeIndex + 1) % items.length;
          items.forEach((item, index) => {
            item.classList.toggle('active', index === activeIndex);
          });
          break;
        case 'ArrowUp':
          e.preventDefault();
          activeIndex = (activeIndex - 1 + items.length) % items.length;
          items.forEach((item, index) => {
            item.classList.toggle('active', index === activeIndex);
          });
          break;
        case 'Enter':
          e.preventDefault();
          if (activeIndex >= 0 && activeIndex < results.length) {
            this.value = results[activeIndex].name;
            currentGame = results[activeIndex];
            if (currentGame.box_art_url) {
              updateTimerBoxArt(currentGame.box_art_url);
            }
            timerDropdown.style.display = 'none';
          }
          break;
        case 'Escape':
          timerDropdown.style.display = 'none';
          break;
      }
    });

    // Handle clicks on autocomplete items
    timerDropdown.addEventListener('click', function(e) {
      const item = e.target.closest('.autocomplete-item');
      if (!item) return;

      const index = parseInt(item.dataset.index);
      if (index >= 0 && index < results.length) {
        timerGameNameInput.value = results[index].name;
        currentGame = results[index];
        if (currentGame.box_art_url) {
          updateTimerBoxArt(currentGame.box_art_url);
        }
        this.style.display = 'none';
      }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
      if (!timerGameNameInput.contains(e.target) && !timerDropdown.contains(e.target)) {
        timerDropdown.style.display = 'none';
      }
    });

    window.addEventListener('scroll', positionDropdown, true);
    window.addEventListener('resize', positionDropdown);

    function updateTimer() {
      if (isPaused) return;
      
      const now = Date.now();
      elapsedTime = now - startTime;
      const totalSeconds = Math.floor(elapsedTime / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;

      timerHours.textContent = hours.toString().padStart(2, '0');
      timerMinutes.textContent = minutes.toString().padStart(2, '0');
      timerSeconds.textContent = seconds.toString().padStart(2, '0');
    }

    function updateTimerBoxArt(boxArtUrl) {
      const timerBoxArt = document.getElementById('timer-box-art');
      if (!timerBoxArt) return;

      if (boxArtUrl && boxArtUrl.endsWith('.webm')) {
        // Create video element for webm files
        const video = document.createElement('video');
        video.src = boxArtUrl;
        video.autoplay = true;
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.className = 'timer-box-art';
        video.alt = currentGame;
        timerBoxArt.parentNode.replaceChild(video, timerBoxArt);
      } else {
        // Use image for non-webm files
        if (timerBoxArt.tagName === 'VIDEO') {
          const img = document.createElement('img');
          img.id = 'timer-box-art';
          img.className = 'timer-box-art';
          img.alt = currentGame;
          timerBoxArt.parentNode.replaceChild(img, timerBoxArt);
        }
        timerBoxArt.src = boxArtUrl || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
        timerBoxArt.onerror = function() {
          this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
        };
      }
    }

    function startTimer() {
      if (!currentGame) {
        showToast('Error', 'Please select a game first', 'error');
        return;
      }

      if (!isLoggedIn) {
        showToast('Error', 'Please log in to start the timer', 'error');
        return;
      }

      isRunning = true;
      startTime = Date.now() - elapsedTime;
      timerInterval = setInterval(updateTimer, 1000);
      
      // Show timer display with animation
      const timerDisplay = document.querySelector('.timer-display');
      if (timerDisplay) {
        timerDisplay.style.display = 'flex';
        // Force a reflow to ensure the animation plays
        void timerDisplay.offsetWidth;
        timerDisplay.classList.add('active');
      }
      
      // Show co-op indicator if multiple players
      // Wait a moment for the DOM to update, then find the elements
      setTimeout(() => {
        const coopIndicator = document.querySelector('.timer-coop-indicator');
        const playerCountSpan = document.querySelector('.timer-player-count');
        console.log('Co-op indicator element:', coopIndicator);
        console.log('Player count span element:', playerCountSpan);
        console.log('Selected players value:', selectedPlayers);
        console.log('Timer display element:', document.querySelector('.timer-display'));
        console.log('Timer display HTML:', document.querySelector('.timer-display')?.innerHTML);
        
        if (coopIndicator && playerCountSpan) {
          if (selectedPlayers > 1) {
            playerCountSpan.textContent = selectedPlayers;
            coopIndicator.style.display = 'flex';
            console.log('SHOWING co-op indicator with', selectedPlayers, 'players');
          } else {
            coopIndicator.style.display = 'none';
            console.log('HIDING co-op indicator (single player)');
          }
        } else {
          console.log('Co-op indicator elements NOT found');
          // Try to find them within the timer display specifically
          const timerDisplay = document.querySelector('.timer-display');
          if (timerDisplay) {
            const coopIndicatorInDisplay = timerDisplay.querySelector('.timer-coop-indicator');
            const playerCountInDisplay = timerDisplay.querySelector('.timer-player-count');
            console.log('Co-op indicator in timer display:', coopIndicatorInDisplay);
            console.log('Player count in timer display:', playerCountInDisplay);
          }
        }
      }, 100);
      
      // Add timer-session-active class to log-game card and remove unnecessary elements
      if (logGameCard) {
        logGameCard.classList.add('timer-session-active');
        
        // Store the selected players value before removing the timer input
        const timerPlayersElement = document.getElementById('timer-players');
        console.log('Timer players element found:', timerPlayersElement);
        if (timerPlayersElement) {
          selectedPlayers = timerPlayersElement.value;
          console.log('Selected players value captured:', selectedPlayers);
        } else {
          console.log('Timer players element NOT found');
        }
        
        const title = logGameCard.querySelector('h2');
        const subtitle = logGameCard.querySelector('h3');
        const divider = logGameCard.querySelector('.timer-divider');
        const logGameForm = logGameCard.querySelector('#log-game-form');
        const timerInput = logGameCard.querySelector('.timer-input');
        if (title) title.remove();
        if (subtitle) subtitle.remove();
        if (divider) divider.remove();
        if (logGameForm) logGameForm.remove();
        if (timerInput) timerInput.remove();
      }
      
      // Update button states
      startTimerButton.style.display = 'none';
      stopTimerButton.style.display = 'block';
      pauseTimerButton.style.display = 'block';
      resumeTimerButton.style.display = 'none';
      logTimerButton.style.display = 'block';
    }

    function stopTimer() {
      isRunning = false;
      clearInterval(timerInterval);
      elapsedTime = 0;
      
      // Hide timer display with animation
      const timerDisplay = document.querySelector('.timer-display');
      if (timerDisplay) {
        timerDisplay.classList.remove('active');
        // Wait for animation to complete before hiding
        setTimeout(() => {
          timerDisplay.style.display = 'none';
        }, 300);
      }
      
      // Remove timer-session-active class from log-game card and restore form
      if (logGameCard) {
        logGameCard.classList.remove('timer-session-active');
        // Restore the form
        const formHTML = `
          <h3>(10% boost for each additional player)</h3>
          <form id="log-game-form">
            <div class="form-row">
              <div class="form-group game-name-group">
                <label for="game-name">
                  <i class="fas fa-gamepad"></i>
                  Manual Entry
                </label>
                <div class="search-container">
                  <input type="text" id="game-name" placeholder="Enter game name..." required>
                  <div class="autocomplete-dropdown"></div>
                </div>
              </div>
              <div class="form-group hours-group">
                <label for="hours">
                  <i class="fas fa-clock"></i>
                  Hours
                </label>
                <input type="number" id="hours" placeholder="Hours..." step="0.5" min="0.5" required>
              </div>
              <div class="form-group players-group">
                <label for="players">
                  <i class="fas fa-users"></i>
                  Players
                </label>
                <select id="players" class="players-dropdown" required>
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                  <option value="4">4</option>
                  <option value="5+">5+</option>
                </select>
              </div>
              <button type="submit" class="submit-button">
                <i class="fas fa-plus"></i>
                Log
              </button>
            </div>
          </form>
          <div class="timer-divider">
            <span>OR</span>
          </div>
          <div class="timer-input">
            <div class="form-group">
              <label for="timer-game-name">
                <i class="fas fa-gamepad"></i>
                Session Timer
              </label>
              <div class="search-container">
                <input type="text" id="timer-game-name" placeholder="Search for a game..." autocomplete="off">
              </div>
            </div>
            <div class="form-group timer-players-group">
              <label for="timer-players">
                <i class="fas fa-users"></i>
                Players
              </label>
              <select id="timer-players" class="players-dropdown" required>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5+">5+</option>
              </select>
            </div>
            <div class="timer-controls">
              <button id="start-timer" class="timer-button" disabled>START TIMER</button>
              <button id="stop-timer" class="timer-button" disabled style="display: none;">STOP</button>
            </div>
          </div>
          <div class="timer-display" style="display: none;">
            <div class="timer-box-art">
              <img src="https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png" alt="Game Box Art" id="timer-box-art">
            </div>
            <div class="timer-coop-indicator" style="display: none;">
              <span class="timer-player-count"></span><i class="fas fa-users"></i>
            </div>
            <div class="timer-time">
              <span id="timer-hours">00</span>:<span id="timer-minutes">00</span>:<span id="timer-seconds">00</span>
            </div>
            <div class="timer-active-controls">
              <button id="pause-timer" class="timer-button">PAUSE</button>
              <button id="resume-timer" class="timer-button" style="display: none;">RESUME</button>
              <button id="log-timer" class="timer-button">LOG SESSION</button>
            </div>
          </div>
        `;
        logGameCard.insertAdjacentHTML('afterbegin', formHTML);
        // Reattach event listener to the new form
        const newForm = logGameCard.querySelector('#log-game-form');
        if (newForm) {
          newForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const gameName = document.getElementById('game-name').value;
            const hours = document.getElementById('hours').value;
            const players = document.getElementById('players').value;

            fetch('/api/user')
              .then(response => {
                if (!response.ok) throw new Error('Not logged in');
                return response.json();
              })
              .then(user => {
                fetch('/api/log-game', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify({
                    user_id: user.id,
                    game_name: gameName,
                    hours: hours,
                    players: players
                  })
                })
                .then(response => response.json())
                .then(data => {
                  if (data.error) {
                    showToast('Error', data.error, 'error');
                  } else {
                    showToast('Success', `Logged ${hours} hours of ${gameName}!`);
                    document.getElementById('log-game-form').reset();
                  }
                })
                .catch(error => {
                  // console.error('Error:', error);
                  showToast('Error', 'An error occurred while logging the game session.', 'error');
                });
              })
              .catch(() => {
                showToast('Error', 'Please log in to log a game session.', 'error');
              });
          });
        }
      }
      
      // Reset timer display
      timerHours.textContent = '00';
      timerMinutes.textContent = '00';
      timerSeconds.textContent = '00';
      updateTimerBoxArt('https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png');
      
      // Hide co-op indicator
      const coopIndicator = document.querySelector('.timer-coop-indicator');
      if (coopIndicator) {
        coopIndicator.style.display = 'none';
      }
      
      currentGame = null;
      
      // Update button states
      startTimerButton.style.display = 'block';
      stopTimerButton.style.display = 'none';
      pauseTimerButton.style.display = 'none';
      resumeTimerButton.style.display = 'none';
      logTimerButton.style.display = 'none';
    }

    function pauseTimer() {
      if (!isRunning) return;
      isRunning = false;
      clearInterval(timerInterval);
      elapsedTime = Date.now() - startTime;
      
      // Update button states
      pauseTimerButton.style.display = 'none';
      resumeTimerButton.style.display = 'block';
    }

    function resumeTimer() {
      if (isRunning) return;
      isRunning = true;
      startTime = Date.now() - elapsedTime;
      timerInterval = setInterval(updateTimer, 1000);
      
      // Update button states
      pauseTimerButton.style.display = 'block';
      resumeTimerButton.style.display = 'none';
    }

    function logSession() {
      if (!isRunning) return;

      const hours = elapsedTime / 3600000; // Convert milliseconds to hours
      const players = selectedPlayers; // Use the stored players value
      
      fetch('/api/user')
        .then(response => {
          if (!response.ok) throw new Error('Not logged in');
          return response.json();
        })
        .then(user => {
          fetch('/api/log-game', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              user_id: user.id,
              game_name: currentGame.name,
              hours: hours.toFixed(2),
              players: players
            })
          })
          .then(response => response.json())
          .then(data => {
            if (data.error) {
              showToast('Error', data.error, 'error');
            } else {
              showToast('Success', `Logged ${hours.toFixed(2)} hours of ${currentGame.name}!`);
              stopTimer();
            }
          })
          .catch(error => {
            // console.error('Error:', error);
            showToast('Error', 'An error occurred while logging the game session.', 'error');
          });
        })
        .catch(() => {
          showToast('Error', 'Please log in to log a game session.', 'error');
        });
    }

    function setRate(rating) {
      if (!currentGame) {
        showToast('Error', 'Please select a game first', 'error');
        return;
      }

      if (!isLoggedIn) {
        showToast('Error', 'Please log in to rate a game', 'error');
        return;
      }

      fetch('/api/user')
        .then(response => {
          if (!response.ok) throw new Error('Not logged in');
          return response.json();
        })
        .then(user => {
          fetch('/api/rate-game', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              user_id: user.id,
              game_name: currentGame.name,
              rating: rating,
              rawg_id: currentGame.rawg_id,
              box_art_url: currentGame.box_art_url,
              release_date: currentGame.release_date
            })
          })
          .then(response => response.json())
          .then(data => {
            if (data.error) {
              showToast('Error', data.error, 'error');
            } else {
              showToast('Success', `Rated ${currentGame.name} ${rating}/10!`);
              // Update the rating display
              const ratingDisplay = document.querySelector('.rating-display');
              if (ratingDisplay) {
                ratingDisplay.textContent = `${rating}/10`;
              }
            }
          })
          .catch(error => {
            // console.error('Error:', error);
            showToast('Error', 'An error occurred while rating the game.', 'error');
          });
        })
        .catch(() => {
          showToast('Error', 'Please log in to rate a game.', 'error');
        });
    }

    startTimerButton.addEventListener('click', startTimer);
    stopTimerButton.addEventListener('click', stopTimer);
    pauseTimerButton.addEventListener('click', pauseTimer);
    resumeTimerButton.addEventListener('click', resumeTimer);
    logTimerButton.addEventListener('click', logSession);
  })();

  // Utility function to format timestamps in CST
  function formatTimestampCST(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        timeZone: 'America/Chicago',
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        second: 'numeric',
        hour12: true
    });
  }

  // Update formatTimeAgo to use CST
  function formatTimeAgo(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    return formatTimestampCST(timestamp);
  }
}); 

// THEME PREFERENCE LOGIC
(function() {
  // Helper: set theme
  function setTheme(theme) {
    if (theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('selected-theme', theme);
    }
  }

  // Helper: get theme from localStorage
  function getLocalTheme() {
    return localStorage.getItem('selected-theme');
  }

  // Helper: clear theme from localStorage
  function clearLocalTheme() {
    localStorage.removeItem('selected-theme');
  }

  // Helper: check if user is logged in (by cookie)
  function isLoggedIn() {
    return document.cookie.includes('user_id=');
  }

  // Helper: apply background to site (supports image and video)
  function applyBackgroundUniversal(url, opacity, type = 'image') {
    if (url) {
      if (type === 'video') {
        // For video backgrounds, use a video element
        let videoBg = document.getElementById('background-video');
        if (!videoBg) {
          videoBg = document.createElement('video');
          videoBg.id = 'background-video';
          videoBg.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            z-index: -3;
            pointer-events: none;
          `;
          videoBg.autoplay = true;
          videoBg.muted = true;
          videoBg.loop = true;
          videoBg.playsInline = true;
          document.body.appendChild(videoBg);
        }
        videoBg.src = url;
        document.body.style.setProperty('--bg-opacity', opacity);
        // Remove image background
        document.body.style.backgroundImage = 'none';
      } else {
        // Remove video if it exists
        const existingVideo = document.getElementById('background-video');
        if (existingVideo) {
          existingVideo.remove();
        }
        // Apply image background
        document.body.style.backgroundImage = `url(${url})`;
        document.body.style.backgroundSize = 'cover';
        document.body.style.backgroundPosition = 'center';
        document.body.style.backgroundAttachment = 'fixed';
        document.body.style.backgroundRepeat = 'no-repeat';
        document.body.style.setProperty('--bg-opacity', opacity);
      }
    } else {
      // Remove video if it exists
      const existingVideo = document.getElementById('background-video');
      if (existingVideo) {
        existingVideo.remove();
      }
      // Remove image background
      document.body.style.backgroundImage = 'none';
      document.body.style.removeProperty('--bg-opacity');
    }
  }

  // On page load
  document.addEventListener('DOMContentLoaded', function() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('just_logged_in')) {
      localStorage.removeItem('selected-theme');
      localStorage.removeItem('background-image-url');
      localStorage.removeItem('background-opacity');
      localStorage.removeItem('background-type');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    let localTheme = localStorage.getItem('selected-theme');
    let localBackgroundUrl = localStorage.getItem('background-image-url');
    let localBackgroundOpacity = localStorage.getItem('background-opacity');
    let localBackgroundType = localStorage.getItem('background-type') || 'image';
    
    if (!localTheme && !localBackgroundUrl) {
      fetch('/api/preferences', { credentials: 'include' })
        .then(r => r.json())
        .then(data => {
          if (data.theme) {
            document.documentElement.setAttribute('data-theme', data.theme);
            localStorage.setItem('selected-theme', data.theme);
          }
          
          let bgType = data.background_type || 'image';
          let bgUrl;
          let bgOpacity = data.background_opacity || 0.3;
          
          // Determine background URL (handle both database-stored and external URLs)
          if (bgType === 'image') {
            if (data.background_image_data) {
              // File stored in database
              bgUrl = `/api/preferences/background/${data.user_id}/image?t=${Date.now()}`;
            } else {
              // External URL
              bgUrl = data.background_image_url;
            }
          } else if (bgType === 'video') {
            if (data.background_video_data) {
              // File stored in database
              bgUrl = `/api/preferences/background/${data.user_id}/video?t=${Date.now()}`;
            } else {
              // External URL
              bgUrl = data.background_video_url;
            }
          }
          
          if (bgUrl) {
            applyBackgroundUniversal(bgUrl, bgOpacity, bgType);
            localStorage.setItem('background-image-url', bgUrl);
            localStorage.setItem('background-opacity', bgOpacity);
            localStorage.setItem('background-type', bgType);
          }
        })
        .catch(error => {
          console.error('Error fetching preferences:', error);
        });
    } else {
      if (localTheme) {
        document.documentElement.setAttribute('data-theme', localTheme);
      }
      if (localBackgroundUrl) {
        applyBackgroundUniversal(localBackgroundUrl, localBackgroundOpacity || 0.3, localBackgroundType);
      }
    }
  });

  // On logout, clear local theme and background
  function setupLogoutThemeClear() {
    // Find logout buttons/links
    const logoutLinks = document.querySelectorAll('a[href="/logout"]');
    logoutLinks.forEach(link => {
      link.addEventListener('click', function() {
        clearLocalTheme();
        localStorage.removeItem('background-image-url');
        localStorage.removeItem('background-opacity');
        localStorage.removeItem('background-type');
        // Remove background from body
        document.body.style.backgroundImage = 'none';
        document.body.style.removeProperty('--bg-opacity');
      });
    });
    // If logout is via a form or button, add similar logic as needed
  }
  document.addEventListener('DOMContentLoaded', setupLogoutThemeClear);

  // Expose setTheme for theme switchers
  window.setTheme = setTheme;
})(); 

// THEME SWITCHER DROPDOWN FUNCTIONALITY
(function() {
  let initialized = false;
  
  function initializeThemeSwitcher() {
    const themeSwitcherBtn = document.getElementById('theme-switcher-btn');
    const themeDropdown = document.getElementById('theme-dropdown');
    const themeOptions = document.querySelectorAll('.theme-option');

    if (!themeSwitcherBtn || !themeDropdown || initialized) return;

    // Toggle dropdown
    themeSwitcherBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      themeDropdown.classList.toggle('show');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
      if (!themeSwitcherBtn.contains(e.target) && !themeDropdown.contains(e.target)) {
        themeDropdown.classList.remove('show');
      }
    });

    // Handle theme selection
    themeOptions.forEach(option => {
      option.addEventListener('click', function() {
        const selectedTheme = this.getAttribute('data-theme');
        
        // Update active state
        themeOptions.forEach(opt => opt.classList.remove('active'));
        this.classList.add('active');
        
        // Apply theme
        document.documentElement.setAttribute('data-theme', selectedTheme);
        localStorage.setItem('selected-theme', selectedTheme);
        
        // Save to backend if logged in
        if (document.cookie.includes('user_id=')) {
          fetch('/api/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ theme: selectedTheme })
          }).catch(error => {
            console.error('Error saving theme preference:', error);
          });
        }
        
        // Close dropdown
        themeDropdown.classList.remove('show');
      });
    });

    // Set initial active state based on current theme
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'default';
    themeOptions.forEach(option => {
      const optionTheme = option.getAttribute('data-theme');
      if (optionTheme === currentTheme) {
        option.classList.add('active');
      } else {
        option.classList.remove('active');
      }
    });
    
    initialized = true;
  }

  // Initialize on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', initializeThemeSwitcher);
  
  // Also initialize immediately if DOM is already loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeThemeSwitcher);
  } else {
    initializeThemeSwitcher();
  }
})(); 