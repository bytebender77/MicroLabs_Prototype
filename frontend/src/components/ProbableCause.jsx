import React from 'react';
import './ProbableCause.css';

const ProbableCause = ({ probableCauses, homeCare, medications }) => {
  return (
    <div className="probable-cause-container">
      <h3>🔍 Probable Causes Based on Your Symptoms</h3>
      
      {/* Disease Matches */}
      <div className="disease-matches">
        {probableCauses.map((cause, index) => (
          <div key={index} className={`disease-card priority-${index + 1}`}>
            <div className="disease-header">
              <span className="disease-name">{cause.disease}</span>
              <span className="match-score">{cause.match_score}% match</span>
            </div>
            
            <div className="disease-severity">
              <span className={`severity-badge ${cause.severity}`}>
                {cause.severity.replace('_', ' ')}
              </span>
            </div>
            
            <div className="matching-symptoms">
              <strong>Matching symptoms:</strong>
              <ul>
                {cause.matching_symptoms.map((symptom, i) => (
                  <li key={i}>✓ {symptom.replace('_', ' ')}</li>
                ))}
              </ul>
            </div>
            
            {/* Home Care */}
            {index === 0 && cause.home_care && (
              <div className="home-care-section">
                <h4>🏠 Home Care Recommendations:</h4>
                <ul>
                  {cause.home_care.map((tip, i) => (
                    <li key={i} className={tip.includes('⚠️') ? 'warning' : ''}>
                      {tip}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Diagnostic Tests */}
            {cause.diagnostic_tests && cause.diagnostic_tests.length > 0 && (
              <div className="diagnostic-tests">
                <h4>📋 Recommended Tests:</h4>
                <ul>
                  {cause.diagnostic_tests.map((test, i) => (
                    <li key={i}>{test}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* When to See Doctor */}
            {cause.when_to_see_doctor && (
              <div className="doctor-warning">
                <h4>⚠️ See a Doctor If:</h4>
                <ul>
                  {cause.when_to_see_doctor.map((condition, i) => (
                    <li key={i}>{condition}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
      
      {/* Medications */}
      {medications && medications.general && (
        <div className="medication-section">
          <h3>💊 Safe Medication Guidance</h3>
          <div className="medication-card">
            {medications.general.fever_reducer && (
              <div className="med-item">
                <strong>{medications.general.fever_reducer.name}</strong>
                <p>Adult: {medications.general.fever_reducer.dosage_adult}</p>
                <p>Child: {medications.general.fever_reducer.dosage_child}</p>
                <p className="med-note">{medications.general.fever_reducer.notes}</p>
              </div>
            )}
            
            {medications.specific && medications.specific.avoid && (
              <div className="avoid-meds">
                <strong>❌ Avoid:</strong> {Array.isArray(medications.specific.avoid) ? medications.specific.avoid.join(', ') : medications.specific.avoid}
                {medications.specific.reason && (
                  <p><em>{medications.specific.reason}</em></p>
                )}
              </div>
            )}
            
            {medications.disclaimer && (
              <div className="disclaimer-box">
                {medications.disclaimer}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProbableCause;