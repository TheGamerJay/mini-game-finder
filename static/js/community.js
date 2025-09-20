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

    const postImage = document.getElementById('postImage');
    if (postImage) {
        postImage.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('previewImg').src = e.target.result;
                    document.getElementById('imagePreview').classList.remove('image-preview');
                    document.getElementById('imagePreview').classList.add('image-preview-visible');
                };
                reader.readAsDataURL(file);
            }
        });
    }

    const postForm = document.getElementById('postForm');
    if (postForm) {
        postForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData();
            const body = document.getElementById('postBody').value.trim();
            const image = document.getElementById('postImage').files[0];

            if (!body && !image) {
                alert('Please add some content to your post!');
                return;
            }

            if (body) formData.append('body', body);
            if (image) formData.append('image', image);

            try {
                const response = await fetch('/community/post', {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });

                if (response.ok) {
                    window.location.reload();
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
});

function removeImage() {
    document.getElementById('postImage').value = '';
    document.getElementById('imagePreview').classList.remove('image-preview-visible');
    document.getElementById('imagePreview').classList.add('image-preview');
}

// Reaction functionality
async function toggleReaction(postId) {
    try {
        const response = await fetch(`/community/react/${postId}`, {
            method: 'POST',
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            const btn = document.querySelector(`[data-post-id="${postId}"]`);
            const heartIcon = btn.querySelector('span:first-child');
            const countSpan = btn.querySelector('.reaction-count');

            if (data.user_reacted) {
                btn.classList.add('reaction-active');
                btn.classList.remove('reaction-inactive');
                heartIcon.textContent = '💚';
            } else {
                btn.classList.add('reaction-inactive');
                btn.classList.remove('reaction-active');
                heartIcon.textContent = '🤍';
            }

            countSpan.textContent = data.reaction_count;
        }
    } catch (err) {
        console.error('Error toggling reaction:', err);
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