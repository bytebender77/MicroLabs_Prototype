import React, { useState } from 'react';
import './LocationPermission.css';

const LocationPermission = ({ onLocationGranted }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [manualLocation, setManualLocation] = useState({
    city: '',
    pincode: ''
  });

  const requestGeolocation = () => {
    setLoading(true);
    setError(null);

    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser');
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        onLocationGranted({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          method: 'gps'
        });
        setLoading(false);
      },
      (error) => {
        let errorMessage = 'Unable to retrieve location';
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Location permission denied. Please enable location access.';
            break;
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Location information unavailable.';
            break;
          case error.TIMEOUT:
            errorMessage = 'Location request timed out.';
            break;
        }
        setError(errorMessage);
        setLoading(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    );
  };

  const handleManualSubmit = async () => {
    if (!manualLocation.city && !manualLocation.pincode) {
      setError('Please enter city or pincode');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Geocode city/pincode using Nominatim
      const query = manualLocation.pincode || manualLocation.city;
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`
      );
      const data = await response.json();

      if (data && data.length > 0) {
        onLocationGranted({
          latitude: parseFloat(data[0].lat),
          longitude: parseFloat(data[0].lon),
          city: manualLocation.city,
          pincode: manualLocation.pincode,
          method: 'manual'
        });
      } else {
        setError('Location not found. Please check your input.');
      }
    } catch (err) {
      setError('Failed to find location. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="location-permission">
      <div className="location-icon">📍</div>
      <h3>Find Healthcare Near You</h3>
      <p className="location-description">
        To show nearby hospitals, clinics, and pharmacies, we need your location.
      </p>

      <div className="location-options">
        {/* GPS Option */}
        <div className="location-option">
          <h4>🛰️ Use GPS (Recommended)</h4>
          <p>Get precise results based on your current location</p>
          <button
            className="btn-primary"
            onClick={requestGeolocation}
            disabled={loading}
          >
            {loading ? 'Getting Location...' : '📍 Allow Location Access'}
          </button>
        </div>

        <div className="option-divider">OR</div>

        {/* Manual Entry */}
        <div className="location-option">
          <h4>✍️ Enter Manually</h4>
          <p>Enter your city or pincode</p>
          <div className="manual-inputs">
            <input
              type="text"
              placeholder="City (e.g., Mumbai)"
              value={manualLocation.city}
              onChange={(e) => setManualLocation({ ...manualLocation, city: e.target.value })}
            />
            <input
              type="text"
              placeholder="Pincode (e.g., 400001)"
              value={manualLocation.pincode}
              onChange={(e) => setManualLocation({ ...manualLocation, pincode: e.target.value })}
            />
          </div>
          <button
            className="btn-secondary"
            onClick={handleManualSubmit}
            disabled={loading}
          >
            Search Location
          </button>
        </div>
      </div>

      {error && (
        <div className="error-box">
          <span className="error-icon">⚠️</span>
          {error}
        </div>
      )}

      <div className="privacy-note">
        🔒 <strong>Privacy:</strong> Your location is only used to find nearby providers 
        and is not stored permanently.
      </div>
    </div>
  );
};

export default LocationPermission;