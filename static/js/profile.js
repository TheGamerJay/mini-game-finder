// Profile page JavaScript - CSP compliant

document.addEventListener('DOMContentLoaded', function() {
  // Handle profile action buttons
  document.querySelectorAll('[data-action]').forEach(button => {
    button.addEventListener('click', function() {
      const action = this.dataset.action;
      switch(action) {
        case 'show-change-name':
          showChangeNameForm();
          break;
        case 'show-image-upload':
          showImageUpload();
          break;
        case 'show-change-password':
          showChangePasswordForm();
          break;
      }
    });
  });

  // Handle cancel buttons
  document.querySelectorAll('[data-cancel]').forEach(button => {
    button.addEventListener('click', function() {
      const form = this.dataset.cancel;
      switch(form) {
        case 'name-form':
          hideChangeNameForm();
          break;
        case 'image-form':
          hideImageUpload();
          break;
        case 'password-form':
          hideChangePasswordForm();
          break;
      }
    });
  });

  // Handle form submissions
  const nameForm = document.getElementById('nameForm');
  if (nameForm) {
    nameForm.addEventListener('submit', handleNameFormSubmit);
  }

  const imageForm = document.getElementById('imageForm');
  if (imageForm) {
    imageForm.addEventListener('submit', handleImageFormSubmit);
  }

  const passwordForm = document.getElementById('passwordForm');
  if (passwordForm) {
    passwordForm.addEventListener('submit', handlePasswordFormSubmit);
  }
});

function showChangeNameForm() {
  document.getElementById('changeNameForm').style.display = 'block';
}

function hideChangeNameForm() {
  document.getElementById('changeNameForm').style.display = 'none';
}

function showImageUpload() {
  document.getElementById('imageUploadForm').style.display = 'block';
}

function hideImageUpload() {
  document.getElementById('imageUploadForm').style.display = 'none';
}

function showChangePasswordForm() {
  document.getElementById('changePasswordForm').style.display = 'block';
}

function hideChangePasswordForm() {
  document.getElementById('changePasswordForm').style.display = 'none';
}

let countdownInterval = null;

function startCountdown(remainingSeconds) {
  if (countdownInterval) clearInterval(countdownInterval);

  const updateCountdown = () => {
    if (remainingSeconds <= 0) {
      clearInterval(countdownInterval);
      document.getElementById('cooldownMessage').style.display = 'none';
      return;
    }

    const hours = Math.floor(remainingSeconds / 3600);
    const minutes = Math.floor((remainingSeconds % 3600) / 60);
    const seconds = remainingSeconds % 60;

    document.getElementById('cooldownMessage').innerHTML =
      `⏰ Cooldown: ${hours}h ${minutes}m ${seconds}s remaining`;
    document.getElementById('cooldownMessage').style.display = 'block';

    remainingSeconds--;
  };

  updateCountdown();
  countdownInterval = setInterval(updateCountdown, 1000);
}

async function handleNameFormSubmit(e) {
  e.preventDefault();
  const newName = document.getElementById('newName').value.trim();
  if (!newName) return;

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  const response = await fetch('/api/profile/change-name', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken
    },
    credentials: 'include',
    body: JSON.stringify({name: newName})
  });

  const result = await response.json();
  if (response.ok) {
    alert('Name changed successfully!');
    location.reload();
  } else {
    if (result.cooldown && result.remaining_seconds) {
      startCountdown(result.remaining_seconds);
    }
    alert(result.error || 'Error changing name');
  }
}

async function handleImageFormSubmit(e) {
  e.preventDefault();
  const fileInput = document.getElementById('imageFile');
  const file = fileInput.files[0];

  if (!file) {
    alert('Please select an image file');
    return;
  }

  const formData = new FormData();
  formData.append('image', file);

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

  const response = await fetch('/api/profile/set-image', {
    method: 'POST',
    headers: {
      'X-CSRF-Token': csrfToken
    },
    credentials: 'include',
    body: formData
  });

  const result = await response.json();
  if (response.ok) {
    alert('Profile image updated!');
    location.reload();
  } else {
    alert(result.error || 'Error uploading image');
  }
}

async function handlePasswordFormSubmit(e) {
  e.preventDefault();
  const currentPassword = document.getElementById('currentPassword').value;
  const newPassword = document.getElementById('newPassword').value;
  const confirmPassword = document.getElementById('confirmPassword').value;

  if (!currentPassword || !newPassword || !confirmPassword) {
    alert('Please fill in all password fields');
    return;
  }

  if (newPassword !== confirmPassword) {
    alert('New passwords do not match');
    return;
  }

  if (newPassword.length < 8) {
    alert('New password must be at least 8 characters long');
    return;
  }

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  const response = await fetch('/api/profile/change-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken
    },
    credentials: 'include',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword
    })
  });

  const result = await response.json();
  if (response.ok) {
    alert('Password changed successfully!');
    hideChangePasswordForm();
    // Clear the form
    document.getElementById('currentPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
  } else {
    alert(result.error || 'Error changing password');
  }
}