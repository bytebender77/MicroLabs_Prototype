import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './NearbyProviders.css';

// Fix Leaflet default icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom icons for different provider types
const hospitalIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const clinicIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const pharmacyIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const RecenterMap = ({ lat, lng }) => {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], 13);
  }, [lat, lng, map]);
  return null;
};

const NearbyProviders = ({ userLocation, onClose, smartFindData }) => {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [viewMode, setViewMode] = useState('grid');
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [emergencyNumbers, setEmergencyNumbers] = useState(null);
  const [smartResponse, setSmartResponse] = useState(null);

  useEffect(() => {
    if (smartFindData) {
      setProviders(smartFindData.providers || []);
      setAssessment(smartFindData.assessment);
      setEmergencyNumbers(smartFindData.emergency_numbers);
      setSmartResponse(smartFindData.smart_response);
      setLoading(false);
    } else if (userLocation) {
      fetchProviders();
    }
  }, [userLocation, smartFindData]);

  const fetchProviders = async () => {
    setLoading(true);
    setError(null);

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const sessionId = localStorage.getItem('healthguide_session_id');
      const triageLevel = localStorage.getItem('healthguide_triage_level');
      const symptoms = JSON.parse(localStorage.getItem('healthguide_symptoms') || '[]');
      
      const response = await fetch(`${API_BASE_URL}/api/providers/smart-find`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: userLocation?.latitude || userLocation?.lat,
          longitude: userLocation?.longitude || userLocation?.lon,
          radius_km: 10,
          provider_type: filter === 'all' ? 'hospital' : filter,
          limit: 20,
          session_id: sessionId || null,
          triage_level: triageLevel || null,
          symptoms: symptoms || []
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch providers' }));
        throw new Error(errorData.detail || 'Failed to fetch providers');
      }

      const data = await response.json();
      setProviders(data.providers || []);
      setAssessment(data.assessment);
      setEmergencyNumbers(data.emergency_numbers);
      setSmartResponse(data.smart_response);
    } catch (err) {
      console.error('Error fetching providers:', err);
      setError(err.message || 'Failed to load healthcare providers. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userLocation && !smartFindData) {
      fetchProviders();
    }
  }, [filter]);

  const handleCallAmbulance = (number) => {
    if (number) {
      window.location.href = `tel:${number.replace(/\D/g, '')}`;
    }
  };

  const getProviderIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'hospital': return hospitalIcon;
      case 'clinic': return clinicIcon;
      case 'pharmacy': return pharmacyIcon;
      default: return hospitalIcon;
    }
  };

  const openInGoogleMaps = (provider) => {
    const lat = userLocation?.latitude || userLocation?.lat;
    const lon = userLocation?.longitude || userLocation?.lon;
    if (provider.latitude && provider.longitude && lat && lon) {
      const url = `https://www.google.com/maps/dir/?api=1&origin=${lat},${lon}&destination=${provider.latitude},${provider.longitude}`;
      window.open(url, '_blank');
    } else if (provider.google_maps_url) {
      window.open(provider.google_maps_url, '_blank');
    }
  };

  const callProvider = (phone) => {
    if (phone) {
      const cleanPhone = phone.replace(/\D/g, '');
      window.location.href = `tel:${cleanPhone}`;
    }
  };

  const filteredProviders = filter === 'all' 
    ? providers 
    : providers.filter(p => p.type?.toLowerCase() === filter.toLowerCase());

  const getProviderTypeLabel = (type) => {
    const typeMap = {
      'hospital': '🏥 Hospital',
      'clinic': '🏥 Clinic',
      'pharmacy': '💊 Pharmacy',
      'doctor': '👨‍⚕️ Doctor'
    };
    return typeMap[type?.toLowerCase()] || '🏥 Healthcare';
  };

  return (
    <div className="nearby-providers-page">
      {/* Header Section */}
      <div className="providers-page-header">
        <div className="header-main">
          <div className="header-title-section">
            <h1 className="page-title">
              <span className="title-icon">🏥</span>
              Nearby Healthcare Providers
            </h1>
            <p className="page-subtitle">Find hospitals, clinics, and pharmacies near you</p>
          </div>
          {onClose && (
            <button className="close-page-btn" onClick={onClose} aria-label="Close">
              <span>×</span>
            </button>
          )}
        </div>

        {/* Quick Stats */}
        <div className="quick-stats">
          <div className="stat-card">
            <div className="stat-icon">📍</div>
            <div className="stat-content">
              <div className="stat-value">{filteredProviders.length}</div>
              <div className="stat-label">Providers Found</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🚑</div>
            <div className="stat-content">
              <div className="stat-value">{emergencyNumbers ? Object.keys(emergencyNumbers).length : 0}</div>
              <div className="stat-label">Emergency Contacts</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">⏱️</div>
            <div className="stat-content">
              <div className="stat-value">{assessment?.estimated_response_time || 'N/A'}</div>
              <div className="stat-label">Response Time</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area - Two Column Layout */}
      <div className="providers-main-content">
        {/* Left Column - Controls & Emergency Info */}
        <div className="left-column">
          {/* Ambulance Assessment Alert */}
          {assessment && assessment.needs_ambulance && (
            <div className="info-box ambulance-box">
              <div className="box-header">
                <span className="box-icon">🚨</span>
                <h3>Ambulance May Be Required</h3>
              </div>
              <p className="box-content">{assessment.recommendation}</p>
              {emergencyNumbers && (
                <div className="emergency-actions">
                  {emergencyNumbers.ambulance && (
                    <button
                      className="emergency-btn ambulance-btn"
                      onClick={() => handleCallAmbulance(emergencyNumbers.ambulance)}
                    >
                      <span className="btn-icon">🚑</span>
                      Call Ambulance: {emergencyNumbers.ambulance}
                    </button>
                  )}
                  {emergencyNumbers.emergency && (
                    <button
                      className="emergency-btn emergency-btn-primary"
                      onClick={() => handleCallAmbulance(emergencyNumbers.emergency)}
                    >
                      <span className="btn-icon">📞</span>
                      Emergency: {emergencyNumbers.emergency}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Smart Response */}
          {smartResponse && !assessment?.needs_ambulance && (
            <div className="info-box smart-response-box">
              <div className="box-header">
                <span className="box-icon">💡</span>
                <h3>Recommendations</h3>
              </div>
              <p className="box-content">{smartResponse}</p>
            </div>
          )}

          {/* Emergency Numbers */}
          {emergencyNumbers && !assessment?.needs_ambulance && (
            <div className="info-box emergency-box">
              <div className="box-header">
                <span className="box-icon">📞</span>
                <h3>Emergency Contacts</h3>
              </div>
              <div className="emergency-numbers-grid">
                {Object.entries(emergencyNumbers).map(([key, value]) => (
                  <button
                    key={key}
                    className="emergency-number-btn"
                    onClick={() => handleCallAmbulance(value)}
                  >
                    <span className="emergency-label">{key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' ')}</span>
                    <span className="emergency-value">{value}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Assessment Info */}
          {assessment && (
            <div className="info-box assessment-box">
              <div className="box-header">
                <span className="box-icon">📊</span>
                <h3>Assessment</h3>
              </div>
              <div className="assessment-details">
                <div className="assessment-item">
                  <span className="assessment-label">Urgency Level:</span>
                  <span className={`assessment-badge ${assessment.urgency_level}`}>
                    {assessment.urgency_level?.toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>
                <div className="assessment-item">
                  <span className="assessment-label">Ambulance Needed:</span>
                  <span className={assessment.needs_ambulance ? 'assessment-yes' : 'assessment-no'}>
                    {assessment.needs_ambulance ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Providers List & Map */}
        <div className="right-column">
          {/* Controls */}
          <div className="controls-section">
            <div className="filter-section">
              <h3 className="section-title">Filter by Type</h3>
              <div className="filter-buttons">
                <button
                  className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                  onClick={() => setFilter('all')}
                >
                  All
                </button>
                <button
                  className={`filter-btn ${filter === 'hospital' ? 'active' : ''}`}
                  onClick={() => setFilter('hospital')}
                >
                  🏥 Hospitals
                </button>
                <button
                  className={`filter-btn ${filter === 'clinic' ? 'active' : ''}`}
                  onClick={() => setFilter('clinic')}
                >
                  🏥 Clinics
                </button>
                <button
                  className={`filter-btn ${filter === 'pharmacy' ? 'active' : ''}`}
                  onClick={() => setFilter('pharmacy')}
                >
                  💊 Pharmacies
                </button>
              </div>
            </div>

            <div className="view-toggle-section">
              <h3 className="section-title">View Mode</h3>
              <div className="view-toggle">
                <button
                  className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                  onClick={() => setViewMode('grid')}
                >
                  <span>📋</span> Grid
                </button>
                <button
                  className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
                  onClick={() => setViewMode('list')}
                >
                  <span>📄</span> List
                </button>
                <button
                  className={`view-btn ${viewMode === 'map' ? 'active' : ''}`}
                  onClick={() => setViewMode('map')}
                >
                  <span>🗺️</span> Map
                </button>
              </div>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Finding healthcare providers near you...</p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="error-state">
              <div className="error-icon">⚠️</div>
              <h3>Unable to load providers</h3>
              <p>{error}</p>
              <button className="retry-btn" onClick={fetchProviders}>
                Try Again
              </button>
            </div>
          )}

          {/* Providers Grid/List View */}
          {!loading && !error && viewMode !== 'map' && (
            <div className="providers-section">
              {filteredProviders.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon">🔍</span>
                  <h3>No providers found</h3>
                  <p>Try expanding your search radius or check a different location.</p>
                </div>
              ) : (
                <div className={viewMode === 'grid' ? 'providers-grid-view' : 'providers-list-view'}>
                  {filteredProviders.map((provider, index) => (
                    <div key={provider.place_id || provider.name || index} className="provider-card">
                      <div className="provider-card-top">
                        <div className="provider-type-badge">
                          {getProviderTypeLabel(provider.type)}
                        </div>
                        {provider.open_now !== undefined && (
                          <span className={`status-badge ${provider.open_now ? 'open' : 'closed'}`}>
                            {provider.open_now ? '✅ Open' : '❌ Closed'}
                          </span>
                        )}
                      </div>
                      
                      <h3 className="provider-name">{provider.name}</h3>
                      <p className="provider-address">{provider.address}</p>

                      {provider.phone && (
                        <div className="provider-phone-box">
                          <div className="phone-header">
                            <span className="phone-icon">📞</span>
                            <span className="phone-label">Contact</span>
                          </div>
                          <a
                            href={`tel:${provider.phone.replace(/\D/g, '')}`}
                            className="provider-phone-link"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {provider.phone}
                          </a>
                        </div>
                      )}

                      <div className="provider-metrics">
                        <div className="metric">
                          <span className="metric-icon">📍</span>
                          <span className="metric-value">{provider.distance_km?.toFixed(1) || 'N/A'} km</span>
                        </div>
                        {provider.rating && (
                          <div className="metric">
                            <span className="metric-icon">⭐</span>
                            <span className="metric-value">{provider.rating} ({provider.total_ratings || 0})</span>
                          </div>
                        )}
                      </div>

                      <div className="provider-actions">
                        {provider.phone && (
                          <button
                            className="action-btn primary call-btn"
                            onClick={() => callProvider(provider.phone)}
                          >
                            <span>📞</span> Call
                          </button>
                        )}
                        <button
                          className="action-btn secondary"
                          onClick={() => openInGoogleMaps(provider)}
                        >
                          <span>🗺️</span> Directions
                        </button>
                        {provider.website && (
                          <button
                            className="action-btn secondary"
                            onClick={() => window.open(provider.website, '_blank')}
                          >
                            <span>🌐</span> Website
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Map View */}
          {!loading && !error && viewMode === 'map' && userLocation && (
            <div className="map-section">
              <div className="map-container-full">
                <MapContainer
                  center={[userLocation.latitude || userLocation.lat, userLocation.longitude || userLocation.lon]}
                  zoom={13}
                  style={{ height: '100%', width: '100%', borderRadius: '12px' }}
                >
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  />
                  
                  <Marker position={[userLocation.latitude || userLocation.lat, userLocation.longitude || userLocation.lon]}>
                    <Popup>
                      <strong>📍 Your Location</strong>
                    </Popup>
                  </Marker>

                  {filteredProviders.map((provider, index) => (
                    <Marker
                      key={provider.place_id || provider.name || index}
                      position={[provider.latitude, provider.longitude]}
                      icon={getProviderIcon(provider.type)}
                      eventHandlers={{
                        click: () => setSelectedProvider(provider)
                      }}
                    >
                      <Popup>
                        <div className="map-popup">
                          <h4>{provider.name}</h4>
                          <p>{provider.address}</p>
                          <p><strong>{provider.distance_km?.toFixed(1) || 'N/A'} km away</strong></p>
                          {provider.phone && (
                            <>
                              <p>📞 {provider.phone}</p>
                              <button
                                className="popup-btn"
                                onClick={() => callProvider(provider.phone)}
                                style={{ marginRight: '8px' }}
                              >
                                Call
                              </button>
                            </>
                          )}
                          <button
                            className="popup-btn"
                            onClick={() => openInGoogleMaps(provider)}
                          >
                            Directions
                          </button>
                        </div>
                      </Popup>
                    </Marker>
                  ))}

                  <RecenterMap 
                    lat={userLocation.latitude || userLocation.lat} 
                    lng={userLocation.longitude || userLocation.lon} 
                  />
                </MapContainer>
              </div>

              {selectedProvider && (
                <div className="selected-provider-info">
                  <button className="close-info-btn" onClick={() => setSelectedProvider(null)}>×</button>
                  <h3>{selectedProvider.name}</h3>
                  <p className="provider-address">{selectedProvider.address}</p>
                  {selectedProvider.distance_km && (
                    <p className="provider-distance"><strong>Distance: {selectedProvider.distance_km.toFixed(1)} km</strong></p>
                  )}
                  {selectedProvider.phone && (
                    <div className="provider-phone-box">
                      <strong>📞 Hospital Contact:</strong>
                      <a
                        href={`tel:${selectedProvider.phone.replace(/\D/g, '')}`}
                        className="provider-phone-link"
                      >
                        {selectedProvider.phone}
                      </a>
                    </div>
                  )}
                  <div className="provider-actions">
                    <button onClick={() => openInGoogleMaps(selectedProvider)}>
                      🗺️ Get Directions
                    </button>
                    {selectedProvider.phone && (
                      <button 
                        onClick={() => callProvider(selectedProvider.phone)}
                        className="call-action-btn"
                      >
                        📞 Call Hospital
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NearbyProviders;
