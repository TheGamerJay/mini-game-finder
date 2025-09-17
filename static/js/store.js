// Store page functionality - Credit purchasing with Stripe integration

async function buyCredits(packageKey) {
    const button = event.target;
    const originalText = button.textContent;

    try {
        // Show loading state
        button.textContent = 'Processing...';
        button.disabled = true;

        console.log('Creating checkout session for package:', packageKey);

        // Create Stripe checkout session
        const response = await fetch('/purchase/create-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ package: packageKey })
        });

        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);

        if (!response.ok) {
            console.log('Response not ok, status:', response.status);
        }

        const data = await response.json();
        console.log('Response data:', data);

        if (response.ok && data.checkout_url) {
            console.log('Redirecting to checkout:', data.checkout_url);
            // Mark that we're going to payment to prevent auto-logout
            window.goingToPayment = true;
            // Redirect to Stripe checkout
            window.location.href = data.checkout_url;
        } else if (response.status === 401) {
            // User not authenticated, redirect to login
            console.log('User not authenticated, redirecting to login');
            alert('Please log in to make a purchase');
            window.location.href = '/login';
            return;
        } else {
            // Handle specific errors
            if (data.error && data.error.includes('Welcome Pack can only be purchased once')) {
                alert('Welcome Pack can only be purchased once per account.');
                // Hide the welcome pack from UI
                const welcomePackCard = document.querySelector('.store-welcome-pack');
                if (welcomePackCard) {
                    welcomePackCard.style.display = 'none';
                }
                return;
            }
            throw new Error(data.error || 'Failed to create checkout session');
        }
    } catch (error) {
        console.error('Payment error:', error);
        alert('Payment failed: ' + error.message);

        // Reset button state
        button.textContent = originalText;
        button.disabled = false;
    }
}

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners to buy buttons
    const buyButtons = document.querySelectorAll('[data-package]');
    buyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const packageType = this.getAttribute('data-package');
            buyCredits(packageType);
        });
    });
});

// Reset button states when returning to the page (e.g., back button from payment)
window.addEventListener('pageshow', function(event) {
    // Reset all processing buttons when page is shown
    document.querySelectorAll('button').forEach(button => {
        if (button.textContent === 'Processing...') {
            button.textContent = 'Buy Now';
            button.disabled = false;
        }
    });

    // Clear the payment flag
    window.goingToPayment = false;
});

// Also reset when page gains focus (alternative approach)
window.addEventListener('focus', function(event) {
    document.querySelectorAll('button').forEach(button => {
        if (button.textContent === 'Processing...') {
            button.textContent = 'Buy Now';
            button.disabled = false;
        }
    });
});