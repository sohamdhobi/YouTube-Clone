// Script to handle email verification and signup form

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the signup page
    const signupForm = document.getElementById('signup_form');
    if (signupForm) {
        // If we have an email field, check if it should be readonly
        const emailField = document.getElementById('id_email');
        if (emailField) {
            // If the email verification session flag is set, make email readonly
            const isEmailVerified = document.querySelector('.alert-success') !== null;
            
            if (isEmailVerified) {
                // Make email field readonly and add verified styling
                emailField.setAttribute('readonly', 'readonly');
                emailField.classList.add('bg-light');
                
                // Create verified badge
                const badge = document.createElement('span');
                badge.classList.add('badge', 'bg-success', 'ms-2');
                badge.textContent = 'Verified';
                
                // Find the email field label and append the badge
                const emailLabel = document.querySelector('label[for="id_email"]');
                if (emailLabel) {
                    emailLabel.appendChild(badge);
                }
            }
        }
    }
}); 