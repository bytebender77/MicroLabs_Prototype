import React, { useState, useEffect } from 'react';
import './MedicationReminder.css';

const MedicationReminder = ({ sessionId, onReminderCreated }) => {
  const [showForm, setShowForm] = useState(false);
  const [reminders, setReminders] = useState([]);
  const [frequencyOptions, setFrequencyOptions] = useState([]);
  const [formData, setFormData] = useState({
    medication_name: '',
    dosage: '',
    frequency: 'daily',
    duration_days: 3,
    notes: ''
  });

  useEffect(() => {
    if (sessionId) {
      loadReminders();
      loadFrequencyOptions();
    }
  }, [sessionId]);

  const loadFrequencyOptions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/medication/frequency-options');
      const data = await response.json();
      setFrequencyOptions(data.options || []);
    } catch (error) {
      console.error('Error loading frequency options:', error);
    }
  };

  const loadReminders = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/medication/reminders/${sessionId}`);
      const data = await response.json();
      setReminders(data.reminders || []);
    } catch (error) {
      console.error('Error loading reminders:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/api/medication/reminder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          ...formData
        })
      });
      const data = await response.json();
      setReminders([...reminders, data]);
      setFormData({
        medication_name: '',
        dosage: '',
        frequency: 'daily',
        duration_days: 3,
        notes: ''
      });
      setShowForm(false);
      if (onReminderCreated) onReminderCreated(data);
    } catch (error) {
      console.error('Error creating reminder:', error);
      alert('Failed to create reminder. Please try again.');
    }
  };

  const handleStopReminder = async (reminderId) => {
    try {
      await fetch(`http://localhost:8000/api/medication/reminder/${reminderId}`, {
        method: 'DELETE'
      });
      loadReminders();
    } catch (error) {
      console.error('Error stopping reminder:', error);
    }
  };

  if (!sessionId) return null;

  return (
    <div className="medication-reminder-container">
      <div className="medication-header">
        <h3>💊 Medication Reminders</h3>
        <button onClick={() => setShowForm(!showForm)} className="add-reminder-btn">
          {showForm ? 'Cancel' : '+ Add Reminder'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="reminder-form">
          <div className="form-group">
            <label>Medication Name *</label>
            <input
              type="text"
              value={formData.medication_name}
              onChange={(e) => setFormData({ ...formData, medication_name: e.target.value })}
              placeholder="e.g., Paracetamol"
              required
            />
          </div>

          <div className="form-group">
            <label>Dosage *</label>
            <input
              type="text"
              value={formData.dosage}
              onChange={(e) => setFormData({ ...formData, dosage: e.target.value })}
              placeholder="e.g., 500mg"
              required
            />
          </div>

          <div className="form-group">
            <label>Frequency *</label>
            <select
              value={formData.frequency}
              onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
              required
            >
              {frequencyOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Duration (days) *</label>
            <input
              type="number"
              min="1"
              max="30"
              value={formData.duration_days}
              onChange={(e) => setFormData({ ...formData, duration_days: parseInt(e.target.value) })}
              required
            />
          </div>

          <div className="form-group">
            <label>Notes (optional)</label>
            <input
              type="text"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="e.g., Take after food"
            />
          </div>

          <button type="submit" className="submit-btn">Create Reminder</button>
        </form>
      )}

      <div className="reminders-list">
        {reminders.length === 0 ? (
          <p className="no-reminders">No active reminders. Add one to get started!</p>
        ) : (
          reminders.map((reminder) => (
            <div key={reminder.id} className="reminder-card">
              <div className="reminder-header">
                <h4>{reminder.medication_name}</h4>
                <button
                  onClick={() => handleStopReminder(reminder.id)}
                  className="stop-btn"
                >
                  Stop
                </button>
              </div>
              <div className="reminder-details">
                <p><strong>Dosage:</strong> {reminder.dosage}</p>
                <p><strong>Frequency:</strong> {reminder.frequency_label}</p>
                <p><strong>Duration:</strong> {reminder.duration_days} days</p>
                {reminder.notes && <p><strong>Notes:</strong> {reminder.notes}</p>}
                {reminder.next_dose && (
                  <p className="next-dose">
                    <strong>Next dose:</strong> {new Date(reminder.next_dose.scheduled_time).toLocaleString()}
                  </p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default MedicationReminder;

