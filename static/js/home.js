// Home page JavaScript - CSP compliant

function toggleDropdown(blockName) {
  // Close all dropdowns first
  document.querySelectorAll('[id$="-dropdown"]').forEach(dropdown => {
    if (dropdown.id !== blockName + '-dropdown') {
      dropdown.style.display = 'none';
    }
  });

  // Toggle the clicked dropdown
  const dropdown = document.getElementById(blockName + '-dropdown');
  dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
}

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
  if (!event.target.closest('.menu-block') && !event.target.closest('[id$="-dropdown"]')) {
    document.querySelectorAll('[id$="-dropdown"]').forEach(dropdown => {
      dropdown.style.display = 'none';
    });
  }
});

// Add click and hover effects
document.addEventListener('DOMContentLoaded', function() {
  const blocks = document.querySelectorAll('.menu-block');
  blocks.forEach(block => {
    // Add click event listeners for dropdown toggles
    const toggleType = block.getAttribute('data-toggle');
    if (toggleType) {
      block.addEventListener('click', function() {
        toggleDropdown(toggleType);
      });
    }

    // Add hover effects
    block.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-5px) scale(1.02)';
    });
    block.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
    });
  });
});