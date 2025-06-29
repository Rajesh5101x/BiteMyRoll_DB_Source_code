
function toggleMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    const card = document.getElementById('userMenu');

    menu.classList.toggle('show');

    if (card.style.display === 'block') {
        card.style.display = 'none';
    }
}

function showUser() {
    const card = document.getElementById('userMenu');

    if (card.style.display === 'none' || card.style.display === '') {
        card.style.display = 'block';
    } else {
        card.style.display = 'none';
    }
}



//for location

function openLocationPopup() {
    const locationData = JSON.parse(document.getElementById("location-data-json").textContent);

    document.getElementById('street').value     = locationData.street_road || '';
    document.getElementById('ward').value       = locationData.ward || '';
    document.getElementById('city').value       = locationData.area || '';
    document.getElementById('pincode').value    = locationData.pincode || '';
    document.getElementById('state').value      = locationData.state || '';
    document.getElementById('country').value    = locationData.country || '';
    document.getElementById('pickupPoint').value = locationData.pickup_point || '';

    document.getElementById('locationPopup').style.display = 'flex';
}




function closeLocationPopup() {
    document.getElementById('locationPopup').style.display = 'none';
}

    function submitLocation() {
    const street = document.getElementById('street').value.trim();
    const ward = document.getElementById('ward').value.trim();
    const city = document.getElementById('city').value.trim();
    const pincode = document.getElementById('pincode').value.trim();
    const state = document.getElementById('state').value.trim();
    const country = document.getElementById('country').value.trim();
    const pickup = document.getElementById('pickupPoint').value.trim();

    if (!street || !city || !pincode) {
        alert("Please fill in at least street, city, and pincode.");
        return;
    }

    const locationData = {
        street_road: street,
        ward: ward,
        area: city,
        pincode: pincode,
        state: state,
        country: country,
        pickup_point: pickup
    };

    fetch("/set_location", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(locationData)
    })
    .then(response => response.json())
    .then(updated => {
        // ✅ Update the hidden JSON data block
        document.getElementById("location-data-json").textContent = JSON.stringify(updated);
        closeLocationPopup();

        // ✅ Refresh the page to show updated data
        location.reload();
    })
    .catch(error => {
        console.error("Error saving location:", error);
        alert("Something went wrong.");
    });
}




    async function getLocationFromGPS() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(async position => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                try {
                    const response = await fetch(`https://api.opencagedata.com/geocode/v1/json?q=${lat}+${lon}&key=a188a60bf0f1417baf6a706018e0b242`);
                    const data = await response.json();

                    if (data.results && data.results.length > 0) {
                        const components = data.results[0].components;

                        document.getElementById('street').value = components.road || "";
                        document.getElementById('ward').value = components.suburb || components.neighbourhood || "";
                        document.getElementById('city').value = components.city || components.town || components.village || "";
                        document.getElementById('pincode').value = components.postcode || "";
                        document.getElementById('state').value = components.state || "";
                        document.getElementById('country').value = components.country || "";
                    } else {
                        alert("Unable to fetch address. Please enter manually.");
                    }
                } catch (error) {
                    console.error("Geocoding error:", error);
                    alert("Error fetching address.");
                }
            }, () => {
                alert("Failed to get location. Please allow location access.");
            });
        } else {
            alert("Geolocation is not supported by this browser.");
        }
    }






  //video playback

  document.addEventListener('DOMContentLoaded', () => {
  const container = document.querySelector('.video-container');
  const video = container.querySelector('.hover-video');
  const eyesOverlay = container.querySelector('.eye-overlay');

  // Ensure the first frame is shown
  video.pause();
  video.currentTime = 0;

  container.addEventListener('mouseenter', () => {
    eyesOverlay.style.opacity = '0';     // Hide eyes
    video.play().catch(err => console.log("Autoplay error:", err));
  });

  container.addEventListener('mouseleave', () => {
    video.pause();
    setTimeout(() => {
      video.currentTime = 0;
    }, 50);
    eyesOverlay.style.opacity = '1';     // Show eyes
  });
});







//eye tracking
const eyes = document.querySelectorAll('.eye');

  document.querySelector('body').addEventListener('mousemove', (e) => {
    eyes.forEach(eye => {
      const pupil = eye.querySelector('.pupil');
      const eyeRect = eye.getBoundingClientRect();
      const eyeCenterX = eyeRect.left + eyeRect.width / 2;
      const eyeCenterY = eyeRect.top + eyeRect.height / 2;

      const dx = e.clientX - eyeCenterX;
      const dy = e.clientY - eyeCenterY;

      const angle = Math.atan2(dy, dx);
      const radius = 3; // how far the pupil can move (in px)

      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;

      pupil.style.left = `${3 + x}px`; // 3 is the center offset
      pupil.style.top = `${3 + y}px`;
    });
  });