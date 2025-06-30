// API Utilities
window.apiUtils = {
  // Format time durations
  formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
  },

  // Format relative time
  formatRelativeTime(timestamp) {
    if (!timestamp) return 'Unknown time';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  },

  // Format numbers with commas
  formatNumber(num) {
    return num.toLocaleString();
  },

  // Format credits
  formatCredits(credits) {
    return `${credits.toLocaleString()} cred`;
  },

  // Format hours
  formatHours(hours) {
    return `${hours.toFixed(1)}h`;
  },

  // Get ordinal suffix
  getOrdinalSuffix(num) {
    const j = num % 10;
    const k = num % 100;
    if (j == 1 && k != 11) {
      return num + "st";
    }
    if (j == 2 && k != 12) {
      return num + "nd";
    }
    if (j == 3 && k != 13) {
      return num + "rd";
    }
    return num + "th";
  },

  // Validate game name
  validateGameName(name) {
    if (!name || name.trim().length === 0) {
      return { valid: false, error: 'Game name cannot be empty' };
    }
    if (name.trim().length > 100) {
      return { valid: false, error: 'Game name too long (max 100 characters)' };
    }
    return { valid: true };
  },

  // Validate hours
  validateHours(hours) {
    if (isNaN(hours) || hours <= 0) {
      return { valid: false, error: 'Hours must be a positive number' };
    }
    if (hours > 1000) {
      return { valid: false, error: 'Hours cannot exceed 1000' };
    }
    return { valid: true };
  },

  // Debounce function
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // Throttle function
  throttle(func, limit) {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  },

  // Local storage utilities
  storage: {
    get(key, defaultValue = null) {
      try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
      } catch (error) {
        console.error('Failed to get from localStorage:', error);
        return defaultValue;
      }
    },

    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (error) {
        console.error('Failed to set to localStorage:', error);
        return false;
      }
    },

    remove(key) {
      try {
        localStorage.removeItem(key);
        return true;
      } catch (error) {
        console.error('Failed to remove from localStorage:', error);
        return false;
      }
    },

    clear() {
      try {
        localStorage.clear();
        return true;
      } catch (error) {
        console.error('Failed to clear localStorage:', error);
        return false;
      }
    }
  },

  // Error handling
  handleError(error, context = '') {
    console.error(`Error in ${context}:`, error);
    
    let message = 'An unexpected error occurred';
    
    if (error.response) {
      // Server responded with error status
      message = error.response.data?.message || `Server error: ${error.response.status}`;
    } else if (error.request) {
      // Network error
      message = 'Network error - please check your connection';
    } else if (error.message) {
      // Other error
      message = error.message;
    }
    
    return message;
  },

  // Retry function
  async retry(fn, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await fn();
      } catch (error) {
        if (i === maxRetries - 1) throw error;
        await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
      }
    }
  }
}; 