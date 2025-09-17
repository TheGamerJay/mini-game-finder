// War Leaderboard JavaScript - CSP compliant

// Load war leaderboard
async function loadWarLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard/war-wins', { credentials: 'include' });
        const data = await response.json();

        document.getElementById('loadingMessage').style.display = 'none';

        if (data.leaders && data.leaders.length > 0) {
            const listDiv = document.getElementById('leaderboardList');
            listDiv.innerHTML = '';

            data.leaders.forEach((leader, index) => {
                const rank = index + 1;
                const rankColor = getRankColor(rank);
                const rankIcon = getRankIcon(rank);

                const entryDiv = document.createElement('div');
                entryDiv.className = 'war-leaderboard-entry';
                entryDiv.style.borderLeftColor = rankColor;

                const avatarContent = leader.avatar ?
                    `<img src="${leader.avatar}" class="war-leader-avatar">` :
                    `<div class="war-leader-avatar-default">
                        ${leader.name[0].toUpperCase()}
                    </div>`;

                entryDiv.innerHTML = `
                    <div class="war-leader-rank" style="color: ${rankColor};">
                        ${rankIcon} ${rank}
                    </div>

                    <div class="war-leader-avatar-container">
                        ${avatarContent}
                    </div>

                    <div class="war-leader-info">
                        <div class="war-leader-name">${leader.name}</div>
                        <div class="war-leader-title">War Champion</div>
                    </div>

                    <div class="war-leader-stats">
                        <div class="war-leader-wins" style="color: ${rankColor};">
                            ⚔️ ${leader.wins}
                        </div>
                        <div class="war-leader-wins-label">
                            ${leader.wins === 1 ? 'victory' : 'victories'}
                        </div>
                    </div>
                `;

                listDiv.appendChild(entryDiv);
            });
        } else {
            document.getElementById('emptyMessage').style.display = 'block';
        }
    } catch (err) {
        console.error('Error loading leaderboard:', err);
        document.getElementById('loadingMessage').textContent = 'Error loading leaderboard';
    }
}

// Load badge catalog
async function loadBadgeCatalog() {
    try {
        const response = await fetch('/api/badges/war-catalog', { credentials: 'include' });
        const data = await response.json();

        if (data.levels) {
            const catalogDiv = document.getElementById('badgeCatalog');
            catalogDiv.innerHTML = '';

            data.levels.forEach(level => {
                const badgeDiv = document.createElement('div');
                badgeDiv.className = 'war-badge-item';
                badgeDiv.style.background = `linear-gradient(135deg, ${level.theme}, rgba(255,255,255,0.1))`;
                badgeDiv.style.borderColor = level.theme;

                badgeDiv.innerHTML = `
                    <div class="war-badge-icon">${level.icon}</div>
                    <div class="war-badge-name">${level.name}</div>
                    <div class="war-badge-level">Level ${level.level}</div>
                    <div class="war-badge-requirement">
                        ${level.wins_required} ${level.wins_required === 1 ? 'win' : 'wins'} required
                    </div>
                `;

                catalogDiv.appendChild(badgeDiv);
            });
        }
    } catch (err) {
        console.error('Error loading badge catalog:', err);
    }
}

function getRankColor(rank) {
    switch(rank) {
        case 1: return '#ffd700'; // Gold
        case 2: return '#c0c0c0'; // Silver
        case 3: return '#cd7f32'; // Bronze
        default: return 'rgba(255,255,255,0.8)';
    }
}

function getRankIcon(rank) {
    switch(rank) {
        case 1: return '🥇';
        case 2: return '🥈';
        case 3: return '🥉';
        default: return '';
    }
}

// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadWarLeaderboard();
    loadBadgeCatalog();
});