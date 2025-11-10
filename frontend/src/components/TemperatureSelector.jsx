import React, { useState } from 'react';
import './TemperatureSelector.css';

const TemperatureSelector = ({ onSubmit }) => {
  const [mode, setMode] = useState('descriptive'); // 'descriptive' or 'numeric'
  const [numericTemp, setNumericTemp] = useState('');
  const [unit, setUnit] = useState('C');
  const [selectedDesc, setSelectedDesc] = useState('');

  const descriptiveOptions = [
    { value: 'feeling_normal', label: 'Feeling normal', emoji: '😊', color: '#4CAF50' },
    { value: 'slightly_warm', label: 'Slightly warm', emoji: '😐', color: '#FFC107' },
    { value: 'hot_to_touch', label: 'Hot to touch, sweating a bit', emoji: '🥵', color: '#FF9800' },
    { value: 'very_hot_sweating', label: 'Very hot, sweating heavily', emoji: '😰', color: '#FF5722' },
    { value: 'burning_up', label: 'Burning up, very uncomfortable', emoji: '🔥', color: '#F44336' },
    { value: 'extreme_heat_confusion', label: 'Extreme heat, feeling confused', emoji: '🚨', color: '#B71C1C' }
  ];

  const handleSubmit = (e) => {
    e?.preventDefault();
    
    if (mode === 'numeric' && numericTemp) {
      const tempValue = parseFloat(numericTemp);
      if (isNaN(tempValue)) {
        alert('Please enter a valid temperature reading.');
        return;
      }
      onSubmit({
        type: 'numeric',
        value: tempValue,
        unit: unit
      });
    } else if (mode === 'descriptive' && selectedDesc) {
      onSubmit({
        type: 'descriptive',
        value: selectedDesc
      });
    } else {
      alert('Please select or enter your temperature reading.');
    }
  };

  return (
    <div className="temperature-selector">
      <h3>📊 How to Check Your Temperature</h3>
      
      {/* Mode Toggle */}
      <div className="mode-toggle">
        <button 
          className={mode === 'descriptive' ? 'active' : ''}
          onClick={() => setMode('descriptive')}
        >
          🤚 I Don't Have a Thermometer
        </button>
        <button 
          className={mode === 'numeric' ? 'active' : ''}
          onClick={() => setMode('numeric')}
        >
          🌡️ I Have a Reading
        </button>
      </div>

      {/* Descriptive Mode */}
      {mode === 'descriptive' && (
        <div className="descriptive-mode">
          <p className="helper-text">
            No thermometer? No problem! Tell us how your body feels:
          </p>
          <div className="temp-options">
            {descriptiveOptions.map((option) => (
              <div
                key={option.value}
                className={`temp-option ${selectedDesc === option.value ? 'selected' : ''}`}
                style={{ borderColor: selectedDesc === option.value ? option.color : '#ddd' }}
                onClick={() => setSelectedDesc(option.value)}
              >
                <div className="temp-emoji" style={{ fontSize: '2rem' }}>
                  {option.emoji}
                </div>
                <div className="temp-label">{option.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Numeric Mode */}
      {mode === 'numeric' && (
        <div className="numeric-mode">
          <p className="helper-text">Enter your temperature reading:</p>
          <div className="numeric-input">
            <input
              type="number"
              step="0.1"
              placeholder={unit === 'C' ? '37.0' : '98.6'}
              value={numericTemp}
              onChange={(e) => setNumericTemp(e.target.value)}
            />
            <div className="unit-toggle">
              <button
                className={unit === 'C' ? 'active' : ''}
                onClick={() => setUnit('C')}
              >
                °C
              </button>
              <button
                className={unit === 'F' ? 'active' : ''}
                onClick={() => setUnit('F')}
              >
                °F
              </button>
            </div>
          </div>
          <div className="temp-reference">
            <small>
              Normal: 36.1-37.2°C (97-99°F) | 
              Fever: &gt;38°C (100.4°F)
            </small>
          </div>
        </div>
      )}

      <button 
        type="button"
        className="submit-temp-btn"
        onClick={handleSubmit}
        disabled={(mode === 'numeric' && (!numericTemp || isNaN(parseFloat(numericTemp)))) || (mode === 'descriptive' && !selectedDesc)}
      >
        Continue →
      </button>
    </div>
  );
};

export default TemperatureSelector;