console.log('Script loaded');
document.addEventListener('DOMContentLoaded', function() {
  // Fetch and display recent bonuses
  const bonusesSection = document.querySelector('.bonuses');
  if (bonusesSection) {
    fetch('/api/recent-bonuses')
      .then(res => res.json())
      .then(bonuses => {
        const spinner = bonusesSection.querySelector('.loading-spinner');
        if (spinner) spinner.remove();
        
        const ul = document.createElement('ul');
        bonuses.forEach(bonus => {
          const li = document.createElement('li');
          li.innerHTML = `
            <img class="avatar-sm" src="${bonus.avatar_url || `https://cdn.discordapp.com/embed/avatars/${parseInt(bonus.user_id.slice(-1)) % 6}.png`}" alt="${bonus.username}">
            <a class="user-link" href="user.html?user=${bonus.user_id}">${bonus.username}</a> earned 
            <span class="bonus"><i class="fas fa-bolt"></i> "${bonus.reason}"</span>
          `;
          ul.appendChild(li);
        });
        bonusesSection.appendChild(ul);
      })
      .catch(error => {
        console.error('Error fetching bonuses:', error);
        const spinner = bonusesSection.querySelector('.loading-spinner');
        if (spinner) {
          spinner.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading bonuses';
        }
      });
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
        heartBtn.parentNode.insertBefore(display, heartBtn.nextSibling);
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
        document.getElementById(tab).style.display = '';
      }
      // Tabs for most popular
      if (btn.closest('.popular-tabs')) {
        document.querySelectorAll('.popular-tabs .tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.most-popular .tab-content').forEach(tc => tc.style.display = 'none');
        const tab = btn.getAttribute('data-tab');
        document.getElementById(tab).style.display = '';
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
      dropdown.classList.toggle('open');
      if (dropdown.classList.contains('open')) {
        // Clone the menu and append to body
        const menu = dropdown.querySelector('.react-dropdown-content.horizontal');
        const menuClone = menu.cloneNode(true);
        // Wrap in .dropdown-inner
        const inner = document.createElement('div');
        inner.className = 'dropdown-inner';
        while (menuClone.firstChild) inner.appendChild(menuClone.firstChild);
        menuClone.appendChild(inner);
        menuClone.style.display = 'inline-flex';
        menuClone.style.position = 'absolute';
        menuClone.style.zIndex = 2000;
        menuClone.classList.add('dropdown-portal');
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
            origBtns[i].click();
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
  const carousel = activityWide ? activityWide.querySelector('.activity-carousel') : null;
  if (carousel && activityWide) {
    const leftArrow = activityWide.querySelector('.carousel-arrow.left');
    const rightArrow = activityWide.querySelector('.carousel-arrow.right');
    const card = carousel.querySelector('.activity-card-wrap');
    const gap = 32; // 2rem gap in px (default root font-size is 16px)
    function scrollByCard(dir) {
      if (!card) return;
      const cardWidth = card.offsetWidth + gap;
      carousel.scrollBy({ left: dir * cardWidth, behavior: 'smooth' });
    }
    if (leftArrow) leftArrow.addEventListener('click', () => scrollByCard(-1));
    if (rightArrow) rightArrow.addEventListener('click', () => scrollByCard(1));
  }

  // --- Navbar Search Autocomplete ---
  const searchBar = document.querySelector('.search-bar');
  console.log('Autocomplete: searchBar found?', !!searchBar);
  if (!searchBar) return;

  // Create dropdown element
  let dropdown = document.createElement('div');
  dropdown.className = 'autocomplete-dropdown';
  searchBar.parentNode.appendChild(dropdown);

  let debounceTimeout = null;
  let lastQuery = '';
  let results = { games: [], users: [] };
  let activeIndex = -1;
  let flatResults = [];

  function renderDropdown() {
    console.log('Autocomplete: renderDropdown called', results);
    dropdown.innerHTML = '';
    flatResults = [];
    // Force dropdown to show for debugging
    dropdown.classList.add('active');
    if (!results.games.length && !results.users.length) {
      // dropdown.classList.remove('active');
      return;
    }
    // Games section
    if (results.games.length) {
      const section = document.createElement('div');
      section.className = 'autocomplete-section';
      section.innerHTML = '<div class="autocomplete-section-title">Games</div>';
      const list = document.createElement('ul');
      list.className = 'autocomplete-list';
      results.games.forEach((game, i) => {
        const item = document.createElement('li');
        item.className = 'autocomplete-item';
        item.innerHTML = `
          <img class="autocomplete-avatar" src="${game.box_art_url || 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png'}" alt="${game.name}">
          <span class="autocomplete-title">${game.name}</span>
          <span class="autocomplete-type">Game</span>
        `;
        item.addEventListener('mousedown', e => {
          e.preventDefault();
          window.location.href = `game.html?game=${encodeURIComponent(game.name)}`;
        });
        list.appendChild(item);
        flatResults.push(item);
      });
      section.appendChild(list);
      dropdown.appendChild(section);
    }
    // Users section
    if (results.users.length) {
      const section = document.createElement('div');
      section.className = 'autocomplete-section';
      section.innerHTML = '<div class="autocomplete-section-title">Users</div>';
      const list = document.createElement('ul');
      list.className = 'autocomplete-list';
      results.users.forEach((user, i) => {
        const item = document.createElement('li');
        item.className = 'autocomplete-item';
        item.innerHTML = `
          <img class="autocomplete-avatar" src="${user.avatar_url || `https://cdn.discordapp.com/embed/avatars/${parseInt(user.user_id.slice(-1)) % 6}.png`}" alt="User">
          <span class="autocomplete-title">${user.username || user.user_id}</span>
          <span class="autocomplete-type">User</span>
        `;
        item.addEventListener('mousedown', e => {
          e.preventDefault();
          window.location.href = `user.html?user=${encodeURIComponent(user.user_id)}`;
        });
        list.appendChild(item);
        flatResults.push(item);
      });
      section.appendChild(list);
      dropdown.appendChild(section);
    }
    dropdown.classList.add('active');
  }

  function fetchResults(query) {
    console.log('Autocomplete: fetchResults called with', query);
    fetch(`/api/search?query=${encodeURIComponent(query)}`)
      .then(res => res.json())
      .then(data => {
        console.log('Autocomplete: fetchResults got data', data);
        results = data;
        activeIndex = -1;
        renderDropdown();
      });
  }

  searchBar.addEventListener('input', function(e) {
    const query = searchBar.value.trim();
    console.log('Autocomplete: input event, query =', query);
    if (!query) {
      dropdown.classList.remove('active');
      return;
    }
    if (query === lastQuery) return;
    lastQuery = query;
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => fetchResults(query), 180);
  });

  searchBar.addEventListener('keydown', function(e) {
    if (!dropdown.classList.contains('active')) return;
    if (e.key === 'ArrowDown') {
      activeIndex = Math.min(flatResults.length - 1, activeIndex + 1);
      updateActiveItem();
      e.preventDefault();
    } else if (e.key === 'ArrowUp') {
      activeIndex = Math.max(0, activeIndex - 1);
      updateActiveItem();
      e.preventDefault();
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && flatResults[activeIndex]) {
        flatResults[activeIndex].dispatchEvent(new MouseEvent('mousedown'));
        dropdown.classList.remove('active');
        e.preventDefault();
      }
    } else if (e.key === 'Escape') {
      dropdown.classList.remove('active');
    }
  });

  function updateActiveItem() {
    flatResults.forEach((item, i) => {
      if (i === activeIndex) item.classList.add('active');
      else item.classList.remove('active');
    });
    if (activeIndex >= 0 && flatResults[activeIndex]) {
      flatResults[activeIndex].scrollIntoView({ block: 'nearest' });
    }
  }

  document.addEventListener('mousedown', function(e) {
    if (!dropdown.contains(e.target) && e.target !== searchBar) {
      dropdown.classList.remove('active');
    }
  });

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
}); 