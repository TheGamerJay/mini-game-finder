// Daily Leaderboard JavaScript - CSP compliant

document.addEventListener('DOMContentLoaded', function() {
    const daySelect = document.getElementById('day');
    if (daySelect) {
        daySelect.addEventListener('change', function() {
            this.form.submit();
        });
    }
});