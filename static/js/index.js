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

    // Add event listeners to play buttons
    const playButtons = document.querySelectorAll('.play-btn');
    playButtons.forEach(button => {
        button.addEventListener('click', function() {
            const mode = this.dataset.mode;
            const daily = this.dataset.daily === '1';
            goto(mode, daily);
        });
    });

    function goto(mode, daily) {
        const c = sel ? sel.value : '';
        const q = new URLSearchParams();
        if (daily) q.set('daily', '1');
        if (c) q.set('category', c);
        location.href = `/play/${mode}` + (q.toString() ? `?${q.toString()}` : '');
    }
});