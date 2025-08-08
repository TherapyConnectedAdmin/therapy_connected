

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

// Geolocation ZIP setter for homepage
function setZipFromGeolocation() {
  if (navigator.geolocation && !localStorage.getItem('zipSetFromGeolocation')) {
    navigator.geolocation.getCurrentPosition(function(position) {
      fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${position.coords.latitude}&lon=${position.coords.longitude}`)
        .then(response => response.json())
        .then(data => {
          if (data.address && data.address.postcode) {
            fetch(`/set_zip/?zip=${data.address.postcode}`)
              .then(() => {
                localStorage.setItem('zipSetFromGeolocation', '1');
                window.location.reload();
              });
          }
        });
    });
  }
}
window.addEventListener('DOMContentLoaded', setZipFromGeolocation);
