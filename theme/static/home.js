

// Alpine.js modal logic for profile modal
document.addEventListener('alpine:init', () => {
  Alpine.store('modal', {
    showProfileModal: false,
    therapist: { profile_photo_url: '', name: '', license_type: '', license_type_description: '', credentials: '', personal_statement_q1: '', personal_statement_q2: '', personal_statement_q3: '', gallery_images: [] }
  });

  // Listen for custom 'open-modal' events and update Alpine store
  document.addEventListener('open-modal', function(e) {
    Alpine.store('modal').therapist = e.detail;
    Alpine.store('modal').showProfileModal = true;
  });
});

// Geolocation ZIP setter (auto on load, can be forced by user click)
function setZipFromGeolocation(force = false) {
  if (!navigator.geolocation) {
    return;
  }
  // Skip if already set unless forced by explicit user action
  if (!force && localStorage.getItem('zipSetFromGeolocation')) {
    return;
  }
  navigator.geolocation.getCurrentPosition(function(position) {
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${position.coords.latitude}&lon=${position.coords.longitude}`)
      .then(response => response.json())
      .then(data => {
        const zip = data && data.address && data.address.postcode;
        if (zip && /^\d{5}$/.test(zip)) {
          fetch(`/set_zip/?zip=${zip}`)
            .then(r => r.json())
            .then(() => {
              localStorage.setItem('zipSetFromGeolocation', '1');
              window.location.reload();
            });
        }
      }).catch(() => {/* ignore */});
  }, function() { /* user denied or error */ });
}
// Auto attempt (non-forced) on initial load
window.addEventListener('DOMContentLoaded', () => setZipFromGeolocation(false));
// Expose globally
window.setZipFromGeolocation = setZipFromGeolocation;
