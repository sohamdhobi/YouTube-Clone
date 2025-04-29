/**
 * Report Button Functionality
 * Handles the report content button interactions
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize report buttons
  initReportButtons();
});

/**
 * Initialize all report buttons on the page
 */
function initReportButtons() {
  const reportLinks = document.querySelectorAll('.report-content-link');
  
  reportLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      const url = this.getAttribute('href');
      
      // Navigate to the report page
      window.location.href = url;
    });
  });
} 