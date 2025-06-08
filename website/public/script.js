console.log('[DEBUG] Current pathname:', window.location.pathname);
console.log('Script loaded');
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
      if (authContainer) {
        authContainer.innerHTML = `
          <a href="/user.html?user=${user.id}" class="user-profile">
            <img src="${user.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : 'https://cdn.discordapp.com/embed/avatars/0.png'}" 
                 alt="${user.username}" 
                 class="user-avatar">
            <span class="user-name">${user.username}</span>
          </a>
          <a href="/logout" class="logout-button" title="Logout">
            <i class="fas fa-sign-out-alt"></i>
          </a>
        `;
      }
    })
    .catch(error => {
      console.log('Not authenticated:', error);
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
        console.error('Error fetching bonuses:', error);
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
          <a class="user-link" href="user.html?user=${bonus.user_id}">${bonus.username}</a> earned 
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
              <img src="${result.avatar}" alt="${result.name}" class="autocomplete-avatar">
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
          console.error('Error fetching results:', error);
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
              window.location.href = `/game.html?game=${encodeURIComponent(result.name)}`;
            } else {
              window.location.href = `/user.html?user=${result.id}`;
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
            window.location.href = `/game.html?game=${encodeURIComponent(result.name)}`;
          } else {
            window.location.href = `/user.html?user=${result.id}`;
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

    function renderDropdown(items) {
      if (!items.length) {
        globalDropdown.style.display = 'none';
        return;
      }
      globalDropdown.innerHTML = `<ul class=\"autocomplete-list\">${items.map((item, i) => `
        <li class=\"autocomplete-item${i === activeIndex ? ' active' : ''}\" data-index=\"${i}\">
          <img class=\"autocomplete-avatar\" src=\"${item.avatar}\" alt=\"\" />
          <span class=\"autocomplete-title\">${item.title}</span>
        </li>`).join('')}</ul>`;
      globalDropdown.style.display = 'block';
      positionDropdown();
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
    console.log('[DEBUG] Navbar autocomplete script loaded. Found input:', !!navbarSearchInput);
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

    function renderDropdown(items) {
      if (!items.games.length && !items.users.length) {
        navbarDropdown.style.display = 'none';
        return;
      }
      let html = '';
      if (items.games.length) {
        html += '<div class="autocomplete-section autocomplete-games-header">Games</div>';
        html += '<ul class="autocomplete-list">' + items.games.map((item, i) => `
          <li class="autocomplete-item autocomplete-game-item${i === activeIndex ? ' active' : ''}" data-index="g${i}">
            <img class="autocomplete-avatar" src="${item.avatar}" alt="" />
            <span class="autocomplete-title">${item.title}</span>
          </li>`).join('') + '</ul>';
      }
      if (items.users.length) {
        html += '<div class="autocomplete-section autocomplete-users-header">Users</div>';
        html += '<ul class="autocomplete-list">' + items.users.map((item, i) => `
          <li class="autocomplete-item autocomplete-user-item${i + items.games.length === activeIndex ? ' active' : ''}" data-index="u${i}">
            <img class="autocomplete-avatar" src="${item.avatar}" alt="" />
            <span class="autocomplete-title">${item.title}</span>
          </li>`).join('') + '</ul>';
      }
      navbarDropdown.innerHTML = html;
      navbarDropdown.style.display = 'block';
      positionDropdown();
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
          }));
          const users = (data.users || []).map(u => ({
            title: u.username,
            avatar: u.avatar_url || '/public/placeholder.png',
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
        const idx = item.getAttribute('data-index');
        let selected;
        if (idx.startsWith('g')) {
          selected = parseInt(idx.slice(1), 10);
          if (results[selected]) {
            navbarSearchInput.value = results[selected].title;
          }
        } else if (idx.startsWith('u')) {
          selected = parseInt(idx.slice(1), 10) + (results.length - (results.length - (results.filter(r => r.avatar && r.title).length)));
          if (results[selected]) {
            navbarSearchInput.value = results[selected].title;
          }
        }
        navbarDropdown.style.display = 'none';
        navbarSearchInput.focus();
      }
    });

    navbarSearchInput.addEventListener('keydown', function(e) {
      const gamesCount = results.filter(r => r.avatar && r.title && !r.username).length;
      const usersCount = results.length - gamesCount;
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
          navbarSearchInput.value = results[activeIndex].title;
          navbarDropdown.style.display = 'none';
          e.preventDefault();
        }
      } else if (e.key === 'Escape') {
        navbarDropdown.style.display = 'none';
      }
    });

    window.addEventListener('resize', positionDropdown);
    window.addEventListener('scroll', positionDropdown, true);
  })();

  // Log game form submission
  const logGameForm = document.getElementById('log-game-form');
  if (logGameForm) {
    logGameForm.addEventListener('submit', function(event) {
      event.preventDefault();
      const gameName = document.getElementById('game-name').value;
      const hours = document.getElementById('hours').value;

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
              hours: hours
            })
          })
          .then(response => response.json())
          .then(data => {
            if (data.error) {
              alert(data.error);
            } else {
              alert('Game session logged successfully!');
              document.getElementById('log-game-form').reset();
            }
          })
          .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while logging the game session.');
          });
        })
        .catch(() => {
          alert('Please log in to log a game session.');
        });
    });
  }
}); 