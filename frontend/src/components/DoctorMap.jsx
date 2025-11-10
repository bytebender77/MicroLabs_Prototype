import React, { useEffect } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DoctorMap = ({ lat, lon }) => {
  useEffect(() => {
    if (!lat || !lon) return;

    // Initialize the map
    const map = L.map('doctor-map').setView([lat, lon], 14);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    // Add a marker for user's current location
    const userMarker = L.marker([lat, lon])
      .addTo(map)
      .bindPopup('<b>You are here 📍</b>')
      .openPopup();

    // Fetch nearby clinics from backend
    const fetchClinics = async () => {
      try {
        const res = await axios.post(`${API_BASE_URL}/find_doctor`, {
          lat,
          lon,
        });
        const clinics = res.data?.clinics || [];

        if (clinics.length === 0) {
          L.popup()
            .setLatLng([lat, lon])
            .setContent('⚠️ No clinics found nearby.')
            .openOn(map);
          return;
        }

        // Add markers for each clinic
        clinics.forEach((clinic) => {
          const cLat = parseFloat(clinic.lat);
          const cLon = parseFloat(clinic.lon);
          if (!isNaN(cLat) && !isNaN(cLon)) {
            L.marker([cLat, cLon])
              .addTo(map)
              .bindPopup(
                `<b>${clinic.name}</b><br>${clinic.address}<br><a href="https://www.google.com/maps?q=${cLat},${cLon}" target="_blank">📍 Open in Maps</a>`
              );
          }
        });
      } catch (error) {
        console.error('Error fetching clinics:', error);
        L.popup()
          .setLatLng([lat, lon])
          .setContent('❌ Unable to load nearby clinics.')
          .openOn(map);
      }
    };

    fetchClinics();

    // Cleanup on unmount
    return () => {
      map.remove();
    };
  }, [lat, lon]);

  return (
    <div>
      <h3 style={{ textAlign: 'center', marginBottom: '8px' }}>Nearby Clinics & Hospitals 🏥</h3>
      <div id="doctor-map" style={{ height: '400px', width: '100%', borderRadius: '8px' }}></div>
    </div>
  );
};

export default DoctorMap;
