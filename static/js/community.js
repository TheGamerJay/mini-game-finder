// Community page functionality

function removeImage() {
    const imagePreview = document.getElementById('imagePreview');
    const imageInput = document.getElementById('imageInput');
    if (imagePreview) {
        imagePreview.style.display = 'none';
    }
    if (imageInput) {
        imageInput.value = '';
    }
}

function reportPost(postId) {
    if (confirm('Are you sure you want to report this post?')) {
        // TODO: Implement report functionality
        console.log('Reporting post:', postId);
        alert('Report functionality not yet implemented');
    }
}

function openImageModal(imageUrl) {
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImg');
    if (modal && modalImg) {
        modalImg.src = imageUrl;
        modal.style.display = 'flex';
    }
}

function closeImageModal() {
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function toggleReaction(postId) {
    // TODO: Implement reaction toggle
    console.log('Toggling reaction for post:', postId);
    alert('Reaction functionality not yet implemented');
}

function boostPost(postId) {
    // TODO: Implement post boost
    console.log('Boosting post:', postId);
    alert('Boost functionality not yet implemented');
}

function challengeToWar(postId, userId) {
    if (confirm('Challenge this user to a word war?')) {
        // TODO: Implement war challenge
        console.log('Challenging to war:', postId, 'user:', userId);
        alert('War challenge functionality not yet implemented');
    }
}

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Remove image button
    const removeBtn = document.querySelector('[data-action="remove-image"]');
    if (removeBtn) {
        removeBtn.addEventListener('click', removeImage);
    }

    // Report buttons
    document.querySelectorAll('[data-action="report"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.getAttribute('data-post-id');
            reportPost(postId);
        });
    });

    // Image click handlers for modal
    document.querySelectorAll('[data-action="open-modal"]').forEach(img => {
        img.addEventListener('click', function() {
            const imageUrl = this.getAttribute('data-image-url');
            openImageModal(imageUrl);
        });
    });

    // Reaction buttons
    document.querySelectorAll('[data-action="toggle-reaction"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.getAttribute('data-post-id');
            toggleReaction(postId);
        });
    });

    // Boost buttons
    document.querySelectorAll('[data-action="boost"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.getAttribute('data-post-id');
            boostPost(postId);
        });
    });

    // War challenge buttons
    document.querySelectorAll('[data-action="challenge-war"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.getAttribute('data-post-id');
            const userId = this.getAttribute('data-user-id');
            challengeToWar(postId, userId);
        });
    });

    // Modal close handlers
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeImageModal();
            }
        });
    }

    const closeBtn = document.querySelector('[data-action="close-modal"]');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeImageModal);
    }
});