// Community page functionality - moved from inline script for CSP compliance

// Post composer functionality
document.addEventListener('DOMContentLoaded', function() {
    const postBody = document.getElementById('postBody');
    if (postBody) {
        postBody.addEventListener('input', function() {
            const count = this.value.length;
            document.getElementById('postCharCount').textContent = count + '/500';
            const charCountEl = document.getElementById('postCharCount');
            if (count > 450) {
                charCountEl.classList.add('text-danger');
                charCountEl.classList.remove('text-muted');
            } else {
                charCountEl.classList.add('text-muted');
                charCountEl.classList.remove('text-danger');
            }
        });
    }


    const postForm = document.getElementById('postForm');
    if (postForm) {
        postForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData();
            const body = document.getElementById('postBody').value.trim();

            if (!body) {
                alert('Please add some content to your post!');
                return;
            }

            formData.append('body', body);

            try {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
                const response = await fetch('/community/new', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'X-CSRF-Token': csrfToken
                    },
                    body: formData
                });

                if (response.ok) {
                    window.location.reload();
                } else if (response.status === 429) {
                    // Handle cooldown error
                    const errorData = await response.json();
                    if (errorData.cooldown && errorData.remaining_seconds) {
                        alert(`Slow down! ${errorData.error}\n\nThis prevents spam and keeps the community friendly.`);
                    } else {
                        alert('Error posting: ' + errorData.error);
                    }
                } else {
                    const error = await response.text();
                    alert('Error posting: ' + error);
                }
            } catch (err) {
                alert('Error posting: ' + err.message);
            }
        });
    }

    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeImageModal();
        }
    });

    // Event delegation for reaction buttons
    document.addEventListener('click', function(e) {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.getAttribute('data-action');
        const postId = target.getAttribute('data-post-id');

        switch (action) {
            case 'toggle-reaction':
                const reactionType = target.getAttribute('data-reaction');
                if (reactionType && postId) {
                    toggleReaction(postId, reactionType);
                }
                break;
            case 'boost':
                if (postId) {
                    boostPost(postId);
                }
                break;
            case 'challenge-war':
                const userId = target.getAttribute('data-user-id');
                if (postId && userId) {
                    challengeToWar(postId, userId);
                }
                break;
            case 'report':
                if (postId) {
                    reportPost(postId);
                }
                break;
            case 'open-modal':
                const imageUrl = target.getAttribute('data-image-url');
                if (imageUrl) {
                    openImageModal(imageUrl);
                }
                break;
            case 'close-modal':
                closeImageModal();
                break;
        }
    });
});


// Reaction cooldown tracking
let reactionCooldown = null;

// Reaction functionality with permanent reaction system
async function toggleReaction(postId, reactionType) {
    // Check cooldown
    if (reactionCooldown && Date.now() < reactionCooldown) {
        const remainingMs = reactionCooldown - Date.now();
        const remainingSeconds = Math.ceil(remainingMs / 1000);
        alert(`Please wait ${remainingSeconds} more seconds before reacting to another post.`);
        return;
    }

    // Check if user already has a reaction on this post
    const existingActiveBtn = document.querySelector(`[data-post-id="${postId}"].reaction-active`);
    if (existingActiveBtn) {
        const existingReaction = existingActiveBtn.getAttribute('data-reaction');
        const reactionEmojis = {
            'love': '❤️',
            'magic': '✨',
            'peace': '🌿',
            'fire': '🔥',
            'gratitude': '🙏',
            'star': '⭐',
            'applause': '👏',
            'support': '🫶'
        };
        alert(`You've already reacted with ${reactionEmojis[existingReaction]}. Reactions are permanent and cannot be changed!`);
        return;
    }

    // Show confirmation dialog for new reaction
    const reactionEmojis = {
        'love': '❤️',
        'magic': '✨',
        'peace': '🌿',
        'fire': '🔥',
        'gratitude': '🙏',
        'star': '⭐',
        'applause': '👏',
        'support': '🫶'
    };

    const confirmed = confirm(`Confirm Permanent Reaction
${reactionEmojis[reactionType]}
Are you sure you want to react with ${reactionEmojis[reactionType]}?

⚠️ This reaction is permanent and cannot be changed or removed!`);

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/community/react/${postId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                reaction_type: reactionType
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Set 2-minute cooldown
            reactionCooldown = Date.now() + (2 * 60 * 1000);

            // Update the specific reaction button
            const reactionBtn = document.querySelector(`[data-post-id="${postId}"][data-reaction="${reactionType}"]`);
            reactionBtn.classList.add('reaction-active');

            // Update total reaction count
            const totalReactionsSpan = document.querySelector(`[data-post-id="${postId}"] .total-reactions`);
            if (totalReactionsSpan) {
                totalReactionsSpan.textContent = data.total_reactions;
            }

        } else if (response.status === 400 && data.permanent) {
            // User already has a permanent reaction
            alert(data.error);
        } else if (response.status === 429) {
            alert(`Reaction cooldown: ${data.error}`);
        } else {
            alert(`Error: ${data.error || 'Failed to process reaction'}`);
        }
    } catch (err) {
        console.error('Error toggling reaction:', err);
        alert('Error processing reaction. Please try again.');
    }
}

// Report functionality
async function reportPost(postId) {
    const reason = prompt('Why are you reporting this post?');
    if (!reason || !reason.trim()) return;

    try {
        const response = await fetch(`/community/report/${postId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ reason: reason.trim() })
        });

        if (response.ok) {
            alert('Report submitted. Thank you for helping keep our community safe!');
        } else {
            alert('Error submitting report. Please try again.');
        }
    } catch (err) {
        alert('Error submitting report: ' + err.message);
    }
}

// Image modal functionality
function openImageModal(imageUrl) {
    document.getElementById('modalImage').src = imageUrl;
    document.getElementById('imageModal').classList.remove('modal-overlay');
    document.getElementById('imageModal').classList.add('modal-overlay-visible');
    document.body.classList.add('modal-open');
}

function closeImageModal() {
    document.getElementById('imageModal').classList.remove('modal-overlay-visible');
    document.getElementById('imageModal').classList.add('modal-overlay');
    document.body.classList.remove('modal-open');
}

// Boost post functionality
async function boostPost(postId) {
    if (!confirm('Spend 10 💎 to boost this post and make it more visible?')) return;

    try {
        const response = await fetch('/api/community/boost', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ postId: postId })
        });

        const data = await response.json();
        if (data.success) {
            alert(`Post boosted! You have ${data.remaining} 💎 remaining.`);
            window.location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Error boosting post: ' + err.message);
    }
}

// War challenge functionality
async function challengeToWar(postId, userId) {
    if (!confirm('Challenge this player to a Boost War?')) return;

    try {
        const response = await fetch('/api/wars/challenge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                challengedUserId: userId,
                challengerPostId: postId
            })
        });

        const data = await response.json();
        if (data.success) {
            alert('War challenge sent! They will be notified.');
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Error sending war challenge: ' + err.message);
    }
}