// Index page JavaScript - CSP compliant

document.addEventListener('DOMContentLoaded', function() {
    const sel = document.getElementById('categorySel');
    if (sel) {
        // Load saved category preference
        sel.value = localStorage.getItem('mwf_category') || '';

        // Save category changes to localStorage
        sel.addEventListener('change', function() {
            localStorage.setItem('mwf_category', sel.value);
        });
    }

    // Store category for game start
    function getGameCategory() {
        return sel ? sel.value : '';
    }

    // Make category available globally for credits system
    window.getGameCategory = getGameCategory;

    // Set puzzle ID and category data for credits system
    function setupGameData() {
        const category = getGameCategory();
        const daily = new URLSearchParams(window.location.search).get('daily') === '1';

        // Set meta data for credits system
        let metaEl = document.getElementById('meta');
        if (!metaEl) {
            metaEl = document.createElement('div');
            metaEl.id = 'meta';
            metaEl.style.display = 'none';
            document.body.appendChild(metaEl);
        }

        metaEl.dataset.category = category;
        metaEl.dataset.daily = daily ? '1' : '0';

        // Generate puzzle ID
        window.CURRENT_PUZZLE_ID = Math.floor(Math.random() * 1000000);
    }

    // Initialize game data
    setupGameData();

    // Fallback for users not logged in - direct navigation
    function directNavigation(mode, daily) {
        const c = sel ? sel.value : '';
        const q = new URLSearchParams();
        if (daily) q.set('daily', '1');
        if (c) q.set('category', c);
        location.href = `/play/${mode}` + (q.toString() ? `?${q.toString()}` : '');
    }

    // Check if user is logged in and credits system is available
    const isLoggedIn = document.querySelector('#credit-badge, #wallet') !== null ||
                      document.body.dataset.authenticated === 'true';

    if (!isLoggedIn) {
        // For non-logged in users, use direct navigation
        const playButtons = document.querySelectorAll('.play-btn');
        playButtons.forEach(button => {
            button.addEventListener('click', function() {
                const mode = this.dataset.mode;
                const daily = this.dataset.daily === '1';
                directNavigation(mode, daily);
            });
        });
    }
    // For logged in users, the credits system will handle the buttons automatically
});