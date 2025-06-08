/*
// --- Autocomplete logic disabled: unified in script.js ---

document.addEventListener('DOMContentLoaded', function() {
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
    if (!results.games.length && !results.users.length) {
      dropdown.classList.remove('active');
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
        // Ensure user_id is treated as a string
        const userId = String(user.user_id);
        item.innerHTML = `
          <img class="autocomplete-avatar" src="${user.avatar_url || `https://cdn.discordapp.com/embed/avatars/${parseInt(userId.slice(-1)) % 6}.png`}" alt="User">
          <span class="autocomplete-title">${user.username || userId}</span>
          <span class="autocomplete-type">User</span>
        `;
        item.addEventListener('mousedown', e => {
          e.preventDefault();
          window.location.href = `user.html?user=${encodeURIComponent(userId)}`;
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
}); 
*/ 