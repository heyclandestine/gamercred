// Game Page JavaScript

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

      // Show user stats section and fetch user's game stats
      const userStatsSection = document.getElementById('userGameStats');
      userStatsSection.style.display = 'block';
      
      // Get game name from URL
      const urlParams = new URLSearchParams(window.location.search);
      const gameName = urlParams.get('game');
      
      // Fetch user's stats for this game
      fetch(`/api/user-stats/${user.id}/game?name=${encodeURIComponent(gameName)}`)
        .then(response => response.json())
        .then(data => {
          const loadingSpinner = userStatsSection.querySelector('.loading-spinner');
          const statsContainer = userStatsSection.querySelector('.user-stats-grid');
          
          if (data.error) {
            loadingSpinner.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.error}`;
            return;
          }
          
          // Update stats
          document.getElementById('userHours').textContent = formatNumber(data.total_hours || 0);
          document.getElementById('userCredits').textContent = formatNumber(data.total_credits || 0);
          document.getElementById('userSessions').textContent = formatNumber(data.total_sessions || 0);
          document.getElementById('firstPlayed').textContent = data.first_played ? new Date(data.first_played).toLocaleDateString() : 'Never';
          document.getElementById('lastPlayed').textContent = data.last_played ? new Date(data.last_played).toLocaleDateString() : 'Never';
          
          // Show stats container and hide loading spinner
          loadingSpinner.style.display = 'none';
          statsContainer.style.display = 'flex';
          userStatsSection.querySelector('.user-stats-header').style.display = 'flex';
        })
        .catch(error => {
          console.error('Error fetching user game stats:', error);
          const loadingSpinner = userStatsSection.querySelector('.loading-spinner');
          loadingSpinner.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error loading your stats';
        });
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

  // Get game name from URL
  const urlParams = new URLSearchParams(window.location.search);
  const gameName = urlParams.get('game');
  if (!gameName) {
    showError('No game specified');
    return;
  }

  // Update page title
  document.title = `${gameName} - Gamer Cred`;

  // Fetch game data
  console.log('DEBUG: Fetching game data for:', gameName);
  fetch(`/api/game?name=${encodeURIComponent(gameName)}`)
    .then(response => {
      console.log('DEBUG: API response status:', response.status);
      return response.json();
    })
    .then(data => {
      console.log('DEBUG: API response data:', data);
      if (data.error) {
        console.error('DEBUG: API returned error:', data.error);
        showError(data.error);
        return;
      }
      console.log('DEBUG: Updating game info with:', data);
      updateGameInfo(data);
    })
    .catch(error => {
      console.error('Error fetching game data:', error);
      showError('Failed to load game information');
    });

  // Fetch current players
  fetch(`/api/game/players?name=${encodeURIComponent(gameName)}`)
    .then(response => response.json())
    .then(data => {
      const playersList = document.querySelector('.players-list');
      const loadingSpinner = document.querySelector('.game-playing .loading-spinner');
      
      if (data.error) {
        playersList.innerHTML = `<li>Error loading players: ${data.error}</li>`;
      } else if (data.length === 0) {
        playersList.innerHTML = '<li>No one is currently playing this game</li>';
      } else {
        playersList.innerHTML = data.map(player => `
          <li>
            <img class="avatar-sm" src="${player.avatar_url}" alt="${player.username}">
            <a class="user-link" href="/pages/user.html?user=${player.user_id}">${player.username}</a>
          </li>
        `).join('');
      }
      
      loadingSpinner.style.display = 'none';
      playersList.style.display = 'flex';
    })
    .catch(error => {
      console.error('Error fetching players:', error);
      document.querySelector('.game-playing .loading-spinner').style.display = 'none';
      document.querySelector('.players-list').innerHTML = '<li>Error loading players</li>';
      document.querySelector('.players-list').style.display = 'flex';
    });

  // Fetch recent activity
  fetch(`/api/game/activity?name=${encodeURIComponent(gameName)}&limit=15`)
    .then(response => response.json())
    .then(data => {
      const activityList = document.querySelector('.activity-list');
      const loadingSpinner = document.querySelector('.game-activity .loading-spinner');
      
      if (data.error) {
        activityList.innerHTML = `<li>Error loading activity: ${data.error}</li>`;
      } else if (data.length === 0) {
        activityList.innerHTML = '<li>No recent activity</li>';
      } else {
        activityList.innerHTML = data.map(activity => `
          <li>
            <img class="avatar-sm" src="${activity.avatar_url}" alt="${activity.username}">
            <div class="activity-details">
              <a class="user-link" href="/pages/user.html?user=${String(activity.user_id)}">${activity.username}</a>
              <span class="activity-text">played for ${formatHours(activity.hours)}</span>
            </div>
            <span class="activity-time">${formatTimeAgo(activity.timestamp)}</span>
          </li>
        `).join('');
      }
      
      loadingSpinner.style.display = 'none';
      activityList.style.display = 'grid';
    })
    .catch(error => {
      console.error('Error fetching activity:', error);
      document.querySelector('.game-activity .loading-spinner').style.display = 'none';
      document.querySelector('.activity-list').innerHTML = '<li>Error loading activity</li>';
      document.querySelector('.activity-list').style.display = 'grid';
    });
});

function updateGameInfo(game) {
  // Update page title with game name
  document.title = `${game.name} - Gamer Cred`;

  // Update game title
  document.getElementById('gameTitle').textContent = game.name;

  // Update game description
  const descriptionElement = document.getElementById('gameDescription');
  const moreButton = document.querySelector('.more-button');
  const lessButton = document.querySelector('.less-button');
  
  if (game.description) {
    descriptionElement.textContent = game.description;
    
    // Check if description is truncated and show/hide buttons accordingly
    setTimeout(() => {
      const isTruncated = descriptionElement.scrollHeight > descriptionElement.clientHeight;
      
      if (isTruncated) {
        moreButton.style.display = 'inline-block';
        lessButton.style.display = 'none';
      } else {
        moreButton.style.display = 'none';
        lessButton.style.display = 'none';
      }
    }, 100); // Small delay to ensure content is rendered
  } else {
    descriptionElement.textContent = 'No description available.';
    moreButton.style.display = 'none';
    lessButton.style.display = 'none';
  }

  // Update game stats
  document.getElementById('totalHours').textContent = formatNumber(game.total_hours || 0);
  document.getElementById('uniquePlayers').textContent = formatNumber(game.unique_players || 0);
  document.getElementById('creditsPerHour').textContent = formatNumber(game.credits_per_hour || 0);
  document.getElementById('releaseDate').textContent = game.release_date ? new Date(game.release_date).toLocaleDateString() : 'N/A';

  // Update half-life information if available
  const halfLifeElement = document.getElementById('halfLife');
  if (halfLifeElement) {
    if (game.half_life_hours) {
      halfLifeElement.textContent = `${game.half_life_hours}h`;
      halfLifeElement.style.display = 'block';
    } else {
      halfLifeElement.textContent = 'None';
      halfLifeElement.style.display = 'block';
    }
  }

  // Update game cover
  const coverElement = document.getElementById('gameCover');
  if (game.box_art_url) {
    if (game.box_art_url.endsWith('.webm')) {
      // Create video element for webm files
      const video = document.createElement('video');
      video.src = game.box_art_url;
      video.autoplay = true;
      video.loop = true;
      video.muted = true;
      video.playsInline = true;
      video.className = 'game-cover';
      video.alt = game.name;
      coverElement.parentNode.replaceChild(video, coverElement);
    } else {
      // Use image for non-webm files
      if (coverElement.tagName === 'VIDEO') {
        const img = document.createElement('img');
        img.id = 'gameCover';
        img.className = 'game-cover';
        img.alt = game.name;
        coverElement.parentNode.replaceChild(img, coverElement);
      }
      coverElement.src = game.box_art_url;
      coverElement.onerror = function() {
        this.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
      };
    }
  } else {
    coverElement.src = 'https://static-cdn.jtvnw.net/ttv-boxart/loading_boxart.png';
  }
  coverElement.alt = game.name;

  // Update Backloggd link
  const backloggdLink = document.getElementById('backloggdLink');
  if (game.backloggd_url) {
    backloggdLink.href = game.backloggd_url;
    backloggdLink.style.display = 'inline-block';
  } else {
    backloggdLink.style.display = 'none';
  }
}

function formatNumber(num) {
  return num.toLocaleString();
}

function formatHours(hours) {
  return hours.toFixed(1) + 'h';
}

function formatTimeAgo(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (minutes < 60) {
    return `${minutes}m ago`;
  } else if (hours < 24) {
    return `${hours}h ago`;
  } else {
    return `${days}d ago`;
  }
}

function showError(message) {
  const main = document.querySelector('main');
  main.innerHTML = `
    <div class="error-message">
      <h2>Error</h2>
      <p>${message}</p>
      <a href="/" class="back-link">&larr; Back to Home</a>
    </div>
  `;
}

// Enhanced message display function
function showMessage(message, type = 'success') {
  const messageDiv = document.createElement('div');
  messageDiv.className = type === 'success' ? 'success-message' : 'error-message';
  messageDiv.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
    <span>${message}</span>
  `;
  
  // Insert at the top of the game-interactivity section
  const gameInteractivity = document.querySelector('.game-interactivity');
  gameInteractivity.insertBefore(messageDiv, gameInteractivity.firstChild);
  
  // Remove after 5 seconds
  setTimeout(() => {
    messageDiv.style.opacity = '0';
    messageDiv.style.transform = 'translateY(-10px)';
    setTimeout(() => messageDiv.remove(), 300);
  }, 5000);
}

// Screenshot Modal Functions
function openScreenshotModal(imageUrl, caption, username, avatarUrl) {
  const modal = document.getElementById('screenshotModal');
  const modalImage = document.getElementById('modalImage');
  const modalCaption = document.getElementById('modalCaption');
  const modalUsername = document.getElementById('modalUsername');
  const modalUserAvatar = document.getElementById('modalUserAvatar');
  
  modalImage.src = imageUrl;
  modalCaption.textContent = caption || '';
  modalUsername.textContent = username;
  modalUserAvatar.src = avatarUrl;
  modalUserAvatar.alt = username;
  
  // Hide caption div if no caption
  if (!caption || caption.trim() === '') {
    modalCaption.style.display = 'none';
  } else {
    modalCaption.style.display = 'block';
  }
  
  modal.classList.add('active');
  document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

function closeScreenshotModal() {
  const modal = document.getElementById('screenshotModal');
  modal.classList.remove('active');
  document.body.style.overflow = ''; // Restore scrolling
}

// Close modal when clicking outside the content
document.addEventListener('click', function(e) {
  const modal = document.getElementById('screenshotModal');
  if (e.target === modal) {
    closeScreenshotModal();
  }
});

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeScreenshotModal();
  }
});

// Add event listeners for More/Less buttons
document.addEventListener('DOMContentLoaded', function() {
  const moreButton = document.querySelector('.more-button');
  const lessButton = document.querySelector('.less-button');
  const descriptionElement = document.getElementById('gameDescription');

  if (moreButton && lessButton && descriptionElement) {
    moreButton.addEventListener('click', function() {
      descriptionElement.style.maxHeight = 'none';
      descriptionElement.style.overflow = 'visible';
      moreButton.style.display = 'none';
      lessButton.style.display = 'inline-block';
    });

    lessButton.addEventListener('click', function() {
      descriptionElement.style.maxHeight = '200px';
      descriptionElement.style.overflow = 'hidden';
      moreButton.style.display = 'inline-block';
      lessButton.style.display = 'none';
    });
  }
}); 

// --- GAME INTERACTIVITY LOGIC ---
document.addEventListener('DOMContentLoaded', function() {
  const urlParams = new URLSearchParams(window.location.search);
  const gameName = urlParams.get('game');
  let currentUser = null;

  // Check login status and fetch user info
  fetch('/api/user').then(r => r.ok ? r.json() : null).then(user => {
    currentUser = user;
    setupInteractivityUI(user);
  }).catch(() => {
    setupInteractivityUI(null);
  });

  function setupInteractivityUI(user) {
    // Ratings
    fetch(`/api/game/ratings?name=${encodeURIComponent(gameName)}`)
      .then(r => r.json())
      .then(data => {
        document.getElementById('averageRating').textContent = data.average !== null ? data.average : '-';
        // Pluralization fix for rating count
        const ratingCount = data.count;
        const ratingText = ratingCount === 1 ? 'rating' : 'ratings';
        document.getElementById('ratingCount').textContent = ratingCount;
        document.querySelector('.game-info-rating-display').innerHTML = `${data.average !== null ? data.average : '-'} / 5 (<span id="ratingCount">${ratingCount}</span> ${ratingText})`;
        if (user) {
          document.getElementById('user-rating-widget').style.display = 'block';
          renderStarWidget(data.user_rating || 0);
        }
      });

    // Completion
    fetch(`/api/game/completions?name=${encodeURIComponent(gameName)}`)
      .then(r => r.json())
      .then(data => {
        document.getElementById('completionCount').textContent = data.count;
        if (user) {
          if (data.user_completed) {
            document.getElementById('completedBadge').style.display = 'inline-block';
            document.getElementById('markCompletedBtn').style.display = 'none';
            document.getElementById('undoCompletedBtn').style.display = 'inline-block';
          } else {
            document.getElementById('completedBadge').style.display = 'none';
            document.getElementById('markCompletedBtn').style.display = 'inline-block';
            document.getElementById('undoCompletedBtn').style.display = 'none';
          }
        }
      });
    if (user) {
      document.getElementById('markCompletedBtn').addEventListener('click', function() {
        const btn = this;
        const originalText = btn.textContent;
        btn.textContent = 'Marking...';
        btn.disabled = true;
        
        fetch('/api/game/complete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ game_name: gameName })
        })
        .then(r => r.json())
        .then(data => {
          if (data.already_completed) {
            document.getElementById('completedBadge').style.display = 'inline-block';
            document.getElementById('markCompletedBtn').style.display = 'none';
            document.getElementById('undoCompletedBtn').style.display = 'inline-block';
            showMessage('You have already completed this game!', 'success');
          } else {
            document.getElementById('completedBadge').style.display = 'inline-block';
            document.getElementById('markCompletedBtn').style.display = 'none';
            document.getElementById('undoCompletedBtn').style.display = 'inline-block';
            document.getElementById('completionCount').textContent = parseInt(document.getElementById('completionCount').textContent) + 1;
            showMessage('🎉 Congratulations! You have been awarded 1,000 credits for completing this game!', 'success');
          }
        })
        .catch(error => {
          console.error('Error marking game as completed:', error);
          showMessage('Failed to mark game as completed. Please try again.', 'error');
          btn.textContent = originalText;
          btn.disabled = false;
        });
      });
      // Undo Completion button logic
      document.getElementById('undoCompletedBtn').addEventListener('click', function() {
        const btn = this;
        const originalText = btn.textContent;
        btn.textContent = 'Undoing...';
        btn.disabled = true;
        fetch('/api/game/uncomplete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ game_name: gameName })
        })
        .then(r => r.json())
        .then(data => {
          if (data.error) {
            showMessage(data.error, 'error');
          } else {
            document.getElementById('completedBadge').style.display = 'none';
            document.getElementById('markCompletedBtn').style.display = 'inline-block';
            document.getElementById('undoCompletedBtn').style.display = 'none';
            document.getElementById('completionCount').textContent = data.completion_count;
            showMessage('Completion undone and credits removed.', 'success');
          }
        })
        .catch(error => {
          console.error('Error undoing completion:', error);
          showMessage('Failed to undo completion. Please try again.', 'error');
        })
        .finally(() => {
          btn.textContent = originalText;
          btn.disabled = false;
        });
      });
    }

    // Reviews
    fetch(`/api/game/reviews?name=${encodeURIComponent(gameName)}`)
      .then(r => r.json())
      .then(reviews => {
        renderReviews(reviews);
      });
    if (user) {
      document.getElementById('reviewFormContainer').style.display = 'block';
      document.getElementById('submitReviewBtn').onclick = function() {
        const text = document.getElementById('reviewText').value.trim();
        if (!text) {
          showMessage('Review cannot be empty!', 'error');
          return;
        }
        
        const btn = this;
        const originalText = btn.textContent;
        btn.textContent = 'Submitting...';
        btn.disabled = true;
        
        fetch('/api/game/review', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ game_name: gameName, review_text: text })
        })
        .then(r => r.json())
        .then(data => {
          if (data.error) {
            showMessage(data.error, 'error');
          } else {
            document.getElementById('reviewText').value = '';
            showMessage('Review submitted successfully!', 'success');
            fetch(`/api/game/reviews?name=${encodeURIComponent(gameName)}`)
              .then(r => r.json())
              .then(renderReviews);
          }
        })
        .catch(error => {
          console.error('Error submitting review:', error);
          showMessage('Failed to submit review. Please try again.', 'error');
        })
        .finally(() => {
          btn.textContent = originalText;
          btn.disabled = false;
        });
      };
    }

    // Screenshots
    fetch(`/api/game/screenshots?name=${encodeURIComponent(gameName)}`)
      .then(r => r.json())
      .then(renderScreenshots);
    if (user) {
      document.getElementById('screenshotUploadForm').style.display = 'block';
      document.getElementById('screenshotUploadForm').onsubmit = function(e) {
        e.preventDefault();
        const fileInput = document.getElementById('screenshotFile');
        if (!fileInput.files.length) {
          showMessage('Please select a screenshot to upload.', 'error');
          return;
        }
        
        const file = fileInput.files[0];
        
        // Check file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
          showMessage('Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WebP.', 'error');
          return;
        }
        
        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
          showMessage('File too large. Maximum size is 10MB.', 'error');
          return;
        }
        
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Uploading...';
        submitBtn.disabled = true;
        
        // Convert file to base64
        const reader = new FileReader();
        reader.onload = function(e) {
          const base64Data = e.target.result.split(',')[1]; // Remove data:image/...;base64, prefix
          
          const uploadData = {
            game_name: gameName,
            caption: document.getElementById('screenshotCaption').value,
            image_data: base64Data,
            filename: file.name,
            mime_type: file.type
          };
          
          fetch('/api/game/screenshot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(uploadData)
          })
          .then(r => r.json())
          .then(data => {
            if (data.error) {
              showMessage(data.error, 'error');
            } else if (data.screenshot_id) {
              showMessage('Screenshot uploaded successfully!', 'success');
              fetch(`/api/game/screenshots?name=${encodeURIComponent(gameName)}`)
                .then(r => r.json())
                .then(renderScreenshots);
              fileInput.value = '';
              document.getElementById('screenshotCaption').value = '';
            }
          })
          .catch(error => {
            console.error('Error uploading screenshot:', error);
            showMessage('Failed to upload screenshot. Please try again.', 'error');
          })
          .finally(() => {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
          });
        };
        
        reader.onerror = function() {
          showMessage('Error reading file. Please try again.', 'error');
          submitBtn.textContent = originalText;
          submitBtn.disabled = false;
        };
        
        reader.readAsDataURL(file);
      };
    }
  }

  function renderStarWidget(userRating) {
    const starRating = document.getElementById('starRating');
    starRating.innerHTML = '';
    let current = userRating;
    
    // Store the current rating in a variable that can be updated
    let currentUserRating = userRating;
    
    for (let i = 1; i <= 5; i++) {
      const full = current >= 1;
      const half = !full && current >= 0.5;
      const star = document.createElement('span');
      star.className = 'star-widget-star';
      star.innerHTML = full ? '<i class="fas fa-star"></i>' : (half ? '<i class="fas fa-star-half-alt"></i>' : '<i class="far fa-star"></i>');
      star.style.cursor = 'pointer';
      star.dataset.value = i;
      star.dataset.half = half ? '1' : '0';
      star.onmousemove = function(e) {
        const rect = star.getBoundingClientRect();
        const isHalf = (e.clientX - rect.left) < rect.width / 2;
        highlightStars(i - (isHalf ? 0.5 : 0));
      };
      star.onmouseleave = function() {
        highlightStars(currentUserRating);
      };
      star.onclick = function(e) {
        const rect = star.getBoundingClientRect();
        const value = (e.clientX - rect.left) < rect.width / 2 ? i - 0.5 : i;
        
        // Add visual feedback
        this.style.transform = 'scale(0.9)';
        setTimeout(() => {
          this.style.transform = 'scale(1)';
        }, 150);
        
        fetch('/api/game/rating', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ game_name: gameName, rating: value })
        })
        .then(r => r.json())
        .then(data => {
          if (data.error) {
            showMessage(data.error, 'error');
          } else {
            // Update the stored rating value
            currentUserRating = value;
            highlightStars(value);
            showMessage(`Rating updated to ${value} stars!`, 'success');
            
            // Update average rating and count in real-time
            fetch(`/api/game/ratings?name=${encodeURIComponent(gameName)}`)
              .then(r => r.json())
              .then(data => {
                document.getElementById('averageRating').textContent = data.average !== null ? data.average : '-';
                document.getElementById('ratingCount').textContent = data.count;
              });
          }
        })
        .catch(error => {
          console.error('Error submitting rating:', error);
          showMessage('Failed to submit rating. Please try again.', 'error');
        });
      };
      starRating.appendChild(star);
      current -= 1;
    }
    highlightStars(userRating);
  }
  
  function highlightStars(value) {
    const stars = document.querySelectorAll('.star-widget-star');
    let v = value;
    stars.forEach(star => {
      if (v >= 1) {
        star.innerHTML = '<i class="fas fa-star"></i>';
      } else if (v >= 0.5) {
        star.innerHTML = '<i class="fas fa-star-half-alt"></i>';
      } else {
        star.innerHTML = '<i class="far fa-star"></i>';
      }
      v -= 1;
    });
  }
  
  function renderReviews(reviews) {
    const reviewsList = document.getElementById('reviewsList');
    if (!reviews.length) {
      reviewsList.innerHTML = '<div style="text-align: center; color: #6272a4; padding: 2rem;">No reviews yet. Be the first to share your thoughts!</div>';
      return;
    }
    reviewsList.innerHTML = reviews.map(r => {
      // Generate star rating HTML
      const ratingStars = r.rating ? generateStarRatingHTML(r.rating) : '';
      
      // Format hours
      const hoursAtReview = r.hours_at_review ? formatHours(r.hours_at_review) : '0h';
      const totalHours = r.total_hours ? formatHours(r.total_hours) : '0h';
      
      return `
        <div class="review-item">
          <div class="review-header">
            <div class="review-user-info">
              <img class="avatar-sm" src="${r.avatar_url}" alt="${r.username}">
              <span class="review-username">${r.username}</span>
              <span class="review-date">${new Date(r.timestamp).toLocaleString()}</span>
            </div>
          </div>
          <div class="review-meta">
            ${r.rating ? `
              <div class="review-rating">
                <div class="review-rating-stars">${ratingStars}</div>
                <span class="review-rating-value">${r.rating}</span>
              </div>
            ` : ''}
            <div class="review-hours">
              <i class="fas fa-clock"></i>
              <span class="review-hours-text">${hoursAtReview} at review</span>
              <span class="review-hours-total">(${totalHours} total)</span>
            </div>
          </div>
          <div class="review-text">${r.review_text}</div>
        </div>
      `;
    }).join('');
  }
  
  function generateStarRatingHTML(rating) {
    let stars = '';
    let remaining = rating;
    
    for (let i = 1; i <= 5; i++) {
      if (remaining >= 1) {
        stars += '<i class="fas fa-star"></i>';
        remaining -= 1;
      } else if (remaining >= 0.5) {
        stars += '<i class="fas fa-star-half-alt"></i>';
        remaining -= 0.5;
      } else {
        stars += '<i class="far fa-star"></i>';
      }
    }
    
    return stars;
  }
  
  function renderScreenshots(screens) {
    const gallery = document.getElementById('screenshotsGallery');
    if (!screens.length) {
      gallery.innerHTML = '<div style="text-align: center; color: #6272a4; padding: 2rem;">No screenshots yet. Share your first screenshot!</div>';
      return;
    }
    gallery.innerHTML = screens.map(s => {
      const hasCaption = s.caption && s.caption.trim() !== '';
      return `
        <div class="screenshot-item" onclick="openScreenshotModal('${s.image_url}', '${s.caption || ''}', '${s.username}', '${s.avatar_url}')">
          <img src="${s.image_url}" alt="Screenshot by ${s.username}" loading="lazy" style="height: ${hasCaption ? '200px' : '280px'};">
          ${hasCaption ? `<div class="screenshot-caption">${s.caption}</div>` : ''}
          <div class="screenshot-user">
            <img class="avatar-sm" src="${s.avatar_url}" alt="${s.username}">
            <span>${s.username}</span>
          </div>
        </div>
      `;
    }).join('');
  }
}); 