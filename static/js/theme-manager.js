/* ============================================
   CHESS PLATFORM - THEME MANAGER
   Dark Mode Toggle & Theme Management
   ============================================ */

(function() {
  'use strict';

  const THEME_KEY = 'chess-platform-theme';
  const THEMES = {
    LIGHT: 'light',
    DARK: 'dark',
    AUTO: 'auto'
  };

  class ThemeManager {
    constructor() {
      this.currentTheme = null;
      this.systemPreference = null;
      this.listeners = [];

      // Initialize immediately to prevent FOUC
      this.init();
    }

    /**
     * Initialize theme system
     */
    init() {
      // Detect system preference
      this.detectSystemPreference();

      // Load saved preference or use system default
      const savedTheme = this.getSavedTheme();
      const initialTheme = savedTheme || THEMES.AUTO;

      // Apply theme without transition on initial load
      this.applyTheme(this.resolveTheme(initialTheme), false);

      // Listen for system preference changes
      this.watchSystemPreference();

      // Make HTML visible now that theme is set
      document.documentElement.style.visibility = 'visible';
    }

    /**
     * Detect system color scheme preference
     */
    detectSystemPreference() {
      if (window.matchMedia) {
        const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
        this.systemPreference = darkModeQuery.matches ? THEMES.DARK : THEMES.LIGHT;
      } else {
        this.systemPreference = THEMES.LIGHT;
      }
    }

    /**
     * Watch for system preference changes
     */
    watchSystemPreference() {
      if (window.matchMedia) {
        const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');

        // Modern browsers
        if (darkModeQuery.addEventListener) {
          darkModeQuery.addEventListener('change', (e) => {
            this.systemPreference = e.matches ? THEMES.DARK : THEMES.LIGHT;

            // If user is on AUTO mode, update theme
            const savedTheme = this.getSavedTheme();
            if (!savedTheme || savedTheme === THEMES.AUTO) {
              this.applyTheme(this.systemPreference, true);
            }
          });
        }
        // Legacy browsers
        else if (darkModeQuery.addListener) {
          darkModeQuery.addListener((e) => {
            this.systemPreference = e.matches ? THEMES.DARK : THEMES.LIGHT;

            const savedTheme = this.getSavedTheme();
            if (!savedTheme || savedTheme === THEMES.AUTO) {
              this.applyTheme(this.systemPreference, true);
            }
          });
        }
      }
    }

    /**
     * Resolve theme (handle AUTO mode)
     */
    resolveTheme(theme) {
      if (theme === THEMES.AUTO) {
        return this.systemPreference;
      }
      return theme;
    }

    /**
     * Apply theme to document
     */
    applyTheme(theme, withTransition = true) {
      const resolvedTheme = this.resolveTheme(theme);

      // Add transition class for smooth animation
      if (withTransition) {
        document.body.classList.add('theme-transitioning');
      }

      // Set theme attribute
      document.documentElement.setAttribute('data-theme', resolvedTheme);
      this.currentTheme = resolvedTheme;

      // Update meta theme-color for mobile browsers
      this.updateMetaThemeColor(resolvedTheme);

      // Remove transition class after animation completes
      if (withTransition) {
        setTimeout(() => {
          document.body.classList.remove('theme-transitioning');
        }, 500);
      }

      // Notify listeners
      this.notifyListeners(resolvedTheme);

      // Dispatch custom event for other scripts
      window.dispatchEvent(new CustomEvent('themechange', {
        detail: { theme: resolvedTheme }
      }));
    }

    /**
     * Update meta theme-color for mobile browsers
     */
    updateMetaThemeColor(theme) {
      let metaThemeColor = document.querySelector('meta[name="theme-color"]');

      if (!metaThemeColor) {
        metaThemeColor = document.createElement('meta');
        metaThemeColor.name = 'theme-color';
        document.head.appendChild(metaThemeColor);
      }

      // Set color based on theme
      const color = theme === THEMES.DARK ? '#0a0e1a' : '#ffffff';
      metaThemeColor.setAttribute('content', color);
    }

    /**
     * Toggle between light and dark mode
     */
    toggle() {
      const newTheme = this.currentTheme === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK;
      this.setTheme(newTheme);
    }

    /**
     * Set specific theme
     */
    setTheme(theme) {
      if (!Object.values(THEMES).includes(theme)) {
        console.warn(`Invalid theme: ${theme}. Using AUTO.`);
        theme = THEMES.AUTO;
      }

      this.saveTheme(theme);
      this.applyTheme(theme, true);
    }

    /**
     * Get current active theme (resolved)
     */
    getTheme() {
      return this.currentTheme;
    }

    /**
     * Get saved theme preference
     */
    getSavedTheme() {
      try {
        return localStorage.getItem(THEME_KEY);
      } catch (e) {
        console.warn('localStorage not available:', e);
        return null;
      }
    }

    /**
     * Save theme preference to localStorage
     */
    saveTheme(theme) {
      try {
        localStorage.setItem(THEME_KEY, theme);
      } catch (e) {
        console.warn('Could not save theme preference:', e);
      }
    }

    /**
     * Clear saved theme preference
     */
    clearTheme() {
      try {
        localStorage.removeItem(THEME_KEY);
      } catch (e) {
        console.warn('Could not clear theme preference:', e);
      }
    }

    /**
     * Check if dark mode is currently active
     */
    isDarkMode() {
      return this.currentTheme === THEMES.DARK;
    }

    /**
     * Check if light mode is currently active
     */
    isLightMode() {
      return this.currentTheme === THEMES.LIGHT;
    }

    /**
     * Add a theme change listener
     */
    addListener(callback) {
      if (typeof callback === 'function') {
        this.listeners.push(callback);
      }
    }

    /**
     * Remove a theme change listener
     */
    removeListener(callback) {
      const index = this.listeners.indexOf(callback);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    }

    /**
     * Notify all listeners of theme change
     */
    notifyListeners(theme) {
      this.listeners.forEach(callback => {
        try {
          callback(theme);
        } catch (e) {
          console.error('Error in theme change listener:', e);
        }
      });
    }
  }

  // Create singleton instance
  const themeManager = new ThemeManager();

  // Expose to window for global access
  window.ThemeManager = themeManager;

  // Also expose the THEMES constant
  window.THEMES = THEMES;

  /* ============================================
     UI TOGGLE HELPER FUNCTIONS
     ============================================ */

  /**
   * Create and setup a theme toggle button
   * Call this from your template after DOM is ready
   */
  window.setupThemeToggle = function(buttonId = 'theme-toggle') {
    const button = document.getElementById(buttonId);

    if (!button) {
      console.warn(`Theme toggle button #${buttonId} not found`);
      return;
    }

    // Update button icon/text based on current theme
    const updateButton = (theme) => {
      const isDark = theme === THEMES.DARK;

      // Update icon (if using icon elements)
      const sunIcon = button.querySelector('.sun-icon');
      const moonIcon = button.querySelector('.moon-icon');

      if (sunIcon && moonIcon) {
        sunIcon.style.display = isDark ? 'inline-block' : 'none';
        moonIcon.style.display = isDark ? 'none' : 'inline-block';
      }

      // Update aria-label for accessibility
      button.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');

      // Update title tooltip
      button.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');

      // Update aria-pressed state
      button.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    };

    // Initial button state
    updateButton(themeManager.getTheme());

    // Add click handler
    button.addEventListener('click', () => {
      themeManager.toggle();
      updateButton(themeManager.getTheme());
    });

    // Listen for theme changes from other sources
    themeManager.addListener(updateButton);

    return button;
  };

  /**
   * Keyboard shortcut for theme toggle (Ctrl/Cmd + Shift + D)
   */
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
      e.preventDefault();
      themeManager.toggle();
    }
  });

  /* ============================================
     DEVELOPER UTILITIES
     ============================================ */

  // Log current theme on console for debugging
  console.log(`🎨 Theme Manager initialized. Current theme: ${themeManager.getTheme()}`);
  console.log('💡 Use ThemeManager.toggle() to switch themes');
  console.log('⌨️  Keyboard shortcut: Ctrl/Cmd + Shift + D');

})();
