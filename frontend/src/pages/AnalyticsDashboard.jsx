import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './AnalyticsDashboard.css';

const AnalyticsDashboard = () => {
  const [stats, setStats] = useState(null);
  const [geographicTrends, setGeographicTrends] = useState([]);
  const [diseaseDistribution, setDiseaseDistribution] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [outbreaks, setOutbreaks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(7);

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [statsRes, geoRes, diseaseRes, timeSeriesRes, outbreaksRes] = await Promise.all([
        fetch(`http://localhost:8000/api/analytics/summary?days=${timeRange}`),
        fetch(`http://localhost:8000/api/analytics/geographic?days=${timeRange}`),
        fetch(`http://localhost:8000/api/analytics/disease-distribution?days=${timeRange}`),
        fetch(`http://localhost:8000/api/analytics/time-series?days=${timeRange}`),
        fetch('http://localhost:8000/api/analytics/outbreaks')
      ]);

      setStats(await statsRes.json());
      setGeographicTrends(await geoRes.json());
      setDiseaseDistribution(await diseaseRes.json());
      setTimeSeriesData(await timeSeriesRes.json());
      setOutbreaks(await outbreaksRes.json());
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4'];

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading Analytics...</p>
      </div>
    );
  }

  return (
    <div className="analytics-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-content">
          <h1>📊 Fever Trend Analytics</h1>
          <p>Real-time monitoring and outbreak detection</p>
        </div>
        <div className="time-range-selector">
          <button
            className={timeRange === 7 ? 'active' : ''}
            onClick={() => setTimeRange(7)}
          >
            7 Days
          </button>
          <button
            className={timeRange === 30 ? 'active' : ''}
            onClick={() => setTimeRange(30)}
          >
            30 Days
          </button>
          <button
            className={timeRange === 90 ? 'active' : ''}
            onClick={() => setTimeRange(90)}
          >
            90 Days
          </button>
        </div>
      </div>

      {/* Outbreak Alerts */}
      {outbreaks && outbreaks.length > 0 && (
        <div className="outbreak-alerts">
          <h2>🚨 Potential Outbreak Alerts</h2>
          <div className="alerts-grid">
            {outbreaks.map((outbreak, index) => (
              <div key={index} className={`alert-card ${outbreak.severity}`}>
                <div className="alert-header">
                  <span className="alert-icon">
                    {outbreak.severity === 'critical' ? '🔴' : '⚠️'}
                  </span>
                  <span className="alert-title">{outbreak.disease}</span>
                </div>
                <div className="alert-location">📍 {outbreak.region}</div>
                <div className="alert-stats">
                  <div className="stat-item">
                    <span className="stat-label">Recent Cases:</span>
                    <span className="stat-value">{outbreak.recent_cases}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Increase:</span>
                    <span className="stat-value increase">
                      +{outbreak.increase_percentage}%
                    </span>
                  </div>
                </div>
                <p className="alert-message">{outbreak.alert_message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary Stats */}
      {stats && (
        <div className="summary-stats">
          <div className="stat-card">
            <div className="stat-icon">📈</div>
            <div className="stat-content">
              <div className="stat-number">{stats.total_cases}</div>
              <div className="stat-label">Total Cases</div>
            </div>
          </div>
          <div className="stat-card emergency">
            <div className="stat-icon">🚨</div>
            <div className="stat-content">
              <div className="stat-number">{stats.emergency_cases}</div>
              <div className="stat-label">Emergency Cases</div>
              <div className="stat-subtitle">{stats.emergency_rate}% of total</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📍</div>
            <div className="stat-content">
              <div className="stat-number">{stats.regions_affected}</div>
              <div className="stat-label">Regions Affected</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🦠</div>
            <div className="stat-content">
              <div className="stat-number">{stats.most_common_disease}</div>
              <div className="stat-label">Most Common</div>
            </div>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Time Series Chart */}
        <div className="chart-card full-width">
          <h3>📈 Fever Cases Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={timeSeriesData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="cases" stroke="#2196F3" strokeWidth={2} name="Total Cases" />
              <Line type="monotone" dataKey="emergencies" stroke="#F44336" strokeWidth={2} name="Emergencies" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Disease Distribution Pie Chart */}
        {diseaseDistribution && (
          <div className="chart-card">
            <h3>🦠 Disease Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={diseaseDistribution.distribution}
                  dataKey="count"
                  nameKey="disease"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={(entry) => `${entry.disease}: ${entry.percentage}%`}
                >
                  {diseaseDistribution.distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="disease-list">
              {diseaseDistribution.distribution.map((disease, index) => (
                <div key={index} className="disease-item">
                  <span className="disease-color" style={{ background: COLORS[index % COLORS.length] }}></span>
                  <span className="disease-name">{disease.disease}</span>
                  <span className="disease-count">{disease.count} cases</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Disease Bar Chart */}
        {diseaseDistribution && (
          <div className="chart-card">
            <h3>📊 Cases by Disease</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={diseaseDistribution.distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="disease" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#2196F3" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Geographic Heatmap */}
        <div className="chart-card full-width">
          <h3>🗺️ Geographic Distribution</h3>
          <div className="map-wrapper">
            <MapContainer
              center={[20.5937, 78.9629]} // India center
              zoom={5}
              style={{ height: '400px', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; OpenStreetMap contributors'
              />
              {geographicTrends.map((trend, index) => (
                trend.latitude && trend.longitude && (
                  <CircleMarker
                    key={index}
                    center={[trend.latitude, trend.longitude]}
                    radius={Math.min(trend.case_count * 2, 30)}
                    fillColor={
                      trend.severity === 'high' ? '#F44336' :
                      trend.severity === 'medium' ? '#FF9800' : '#4CAF50'
                    }
                    color="#fff"
                    weight={1}
                    opacity={0.8}
                    fillOpacity={0.6}
                  >
                    <Popup>
                      <div className="map-popup">
                        <strong>{trend.city}, {trend.region}</strong>
                        <p>Cases: {trend.case_count}</p>
                        {trend.emergency_count > 0 && (
                          <p className="emergency-text">
                            Emergencies: {trend.emergency_count}
                          </p>
                        )}
                      </div>
                    </Popup>
                  </CircleMarker>
                )
              ))}
            </MapContainer>
          </div>
          <div className="map-legend">
            <div className="legend-item">
              <span className="legend-dot high"></span>
              <span>High Activity (&gt;10 cases)</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot medium"></span>
              <span>Medium Activity (5-10 cases)</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot low"></span>
              <span>Low Activity (&lt;5 cases)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Data Export */}
      <div className="export-section">
        <h3>📥 Export Data</h3>
        <div className="export-buttons">
          <button className="export-btn">
            📄 Export as CSV
          </button>
          <button className="export-btn">
            📊 Export as Excel
          </button>
          <button className="export-btn">
            📋 Generate Report
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;