import React from 'react';
import './HomeCareCard.css';

const HomeCareCard = ({ homeCareTips, diseaseName }) => {
  if (!homeCareTips || homeCareTips.length === 0) {
    return null;
  }

  return (
    <div className="home-care-card">
      <div className="home-care-header">
        <h3>🏠 Home Care Recommendations</h3>
        {diseaseName && <span className="disease-badge">{diseaseName}</span>}
      </div>
      <div className="home-care-content">
        <ul className="home-care-list">
          {homeCareTips.map((tip, index) => (
            <li
              key={index}
              className={tip.includes('⚠️') || tip.includes('❌') ? 'warning-tip' : 'normal-tip'}
            >
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default HomeCareCard;

