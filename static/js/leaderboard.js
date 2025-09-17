// Leaderboard JavaScript - CSP compliant

// Load top war champions preview
async function loadTopWarChampions() {
    try {
        const response = await fetch('/api/leaderboard/war-wins', { credentials: 'include' });
        const data = await response.json();

        const container = document.getElementById('topWarChampions');

        if (data.leaders && data.leaders.length > 0) {
            const top3 = data.leaders.slice(0, 3);
            container.innerHTML = '';

            top3.forEach((leader, index) => {
                const rank = index + 1;
                const rankIcon = rank === 1 ? '🥇' : rank === 2 ? '🥈' : '🥉';
                const rankColor = rank === 1 ? '#ffd700' : rank === 2 ? '#c0c0c0' : '#cd7f32';

                const entryDiv = document.createElement('div');
                entryDiv.className = 'war-champion-preview-item';

                entryDiv.innerHTML = `
                    <div class="war-champion-rank" style="color: ${rankColor};">${rankIcon}</div>
                    <div class="war-champion-name">${leader.name}</div>
                    <div class="war-champion-wins">⚔️ ${leader.wins}</div>
                `;

                container.appendChild(entryDiv);
            });
        } else {
            container.innerHTML = '<div class="war-champion-empty">No war champions yet!</div>';
        }
    } catch (err) {
        console.error('Error loading war champions:', err);
    }
}

// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadTopWarChampions();
});