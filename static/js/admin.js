// Admin page functionality

function refundPurchase(purchaseId, credits) {
    if (confirm(`Are you sure you want to refund ${credits} credits for purchase #${purchaseId}?`)) {
        // TODO: Implement refund logic
        console.log('Refunding purchase:', purchaseId, 'credits:', credits);
        alert('Refund functionality not yet implemented');
    }
}

function adjustCredits(userId) {
    const newCredits = prompt('Enter new credit amount:');
    if (newCredits !== null && !isNaN(newCredits)) {
        // TODO: Implement credit adjustment logic
        console.log('Adjusting credits for user:', userId, 'to:', newCredits);
        alert('Credit adjustment functionality not yet implemented');
    }
}

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners to admin buttons
    const refundButtons = document.querySelectorAll('[data-action="refund"]');
    refundButtons.forEach(button => {
        button.addEventListener('click', function() {
            const purchaseId = this.getAttribute('data-purchase-id');
            const credits = this.getAttribute('data-credits');
            refundPurchase(purchaseId, credits);
        });
    });

    const adjustButtons = document.querySelectorAll('[data-action="adjust"]');
    adjustButtons.forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            adjustCredits(userId);
        });
    });
});