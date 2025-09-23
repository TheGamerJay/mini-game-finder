import { getJSON } from "./http.js";

export async function refreshQuota(gameKey) {
    try {
        const data = await getJSON(`/game/api/quota?game=${encodeURIComponent(gameKey)}`);
        if (!data.ok) {
            console.error("Quota fetch failed:", data.error);
            return null;
        }

        // Update quota display elements
        const quotaEl = document.querySelector('.quota-display');
        if (quotaEl) {
            quotaEl.textContent = `${data.used}/${data.limit}`;
        }

        const leftEl = document.querySelector('.quota-left');
        if (leftEl) {
            leftEl.textContent = data.left;
        }

        // Disable/enable game buttons based on quota
        const startBtn = document.querySelector('.start-game-btn, #start-btn');
        if (startBtn) {
            if (data.left <= 0) {
                startBtn.disabled = true;
                startBtn.textContent = "Daily Limit Reached";
                startBtn.classList.add('disabled');
            } else {
                startBtn.disabled = false;
                startBtn.textContent = "Start Game";
                startBtn.classList.remove('disabled');
            }
        }

        return data;
    } catch (error) {
        console.error("Failed to refresh quota:", error);
        return null;
    }
}

export function showQuotaUI(gameKey) {
    // Create quota display if it doesn't exist
    if (!document.querySelector('.quota-container')) {
        const container = document.createElement('div');
        container.className = 'quota-container';
        container.innerHTML = `
            <div class="quota-info">
                <strong>Daily Games:</strong>
                <span class="quota-display">0/5</span>
                (<span class="quota-left">5</span> remaining)
            </div>
        `;

        // Insert before game area or at top of main content
        const gameArea = document.querySelector('.game-area, .container > *');
        if (gameArea) {
            gameArea.parentNode.insertBefore(container, gameArea);
        }
    }

    // Refresh the quota data
    refreshQuota(gameKey);
}