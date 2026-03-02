import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [number, setNumber] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recent, setRecent] = useState([]);
  const [apiUrl] = useState(window.env.REACT_APP_API_URL || 'https://phone-trace-api.onrender.com');

  const lookupNumber = async () => {
    if (!number.trim()) return;
    setLoading(true);
    
    try {
      const response = await fetch(`${apiUrl}/api/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ number: number.trim() })
      });
      
      const data = await response.json();
      if (data.success) {
        setResult(data);
        // Add to recent searches
        const newRecent = [{
          number: data.phone.formatted,
          risk: data.risk_assessment.level,
          timestamp: new Date().toLocaleString()
        }, ...recent.slice(0, 4)];
        setRecent(newRecent);
        localStorage.setItem('recent', JSON.stringify(newRecent));
      } else {
        setResult({ error: data.error || 'Lookup failed' });
      }
    } catch (error) {
      setResult({ error: 'Network error. Check API URL.' });
    }
    setLoading(false);
  };

  useEffect(() => {
    // Load recent searches
    const saved = localStorage.getItem('recent');
    if (saved) setRecent(JSON.parse(saved));
  }, []);

  const formatRisk = (risk) => {
    const levels = {
      LOW: { color: '#28a745', bg: '#d4edda' },
      MEDIUM: { color: '#ffc107', bg: '#fff3cd' },
      HIGH: { color: '#dc3545', bg: '#f8d7da' }
    };
    return levels[risk?.level] || { color: '#6c757d', bg: '#f8f9fa' };
  };

  const ResultDisplay = ({ result }) => (
    <div className="result" style={{ animation: 'fadeIn 0.5s' }}>
      <div className="result-header">
        <h2>{result.phone.formatted}</h2>
        <div className={`risk-badge`} style={{
          backgroundColor: formatRisk(result.risk_assessment).bg,
          color: formatRisk(result.risk_assessment).color
        }}>
          {formatRisk(result.risk_assessment).color === '#ffc107' ? '⚠️ ' : ''}
          {formatRisk(result.risk_assessment).color === '#dc3545' ? '🚨 ' : ''}
          {result.risk_assessment.level} Risk
        </div>
      </div>

      <div className="info-grid">
        <div className="info-card">
          <h4>📍 Location</h4>
          <p>{result.phone.country}</p>
          <small>{result.phone.timezone[0] || 'N/A'}</small>
        </div>
        <div className="info-card">
          <h4>📞 Carrier</h4>
          <p>{result.phone.carrier}</p>
          {result.enrichment.numverify.line_type && (
            <span className="tag">{result.enrichment.numverify.line_type}</span>
          )}
        </div>
        {result.risk_assessment.reasons.length > 0 && (
          <div className="info-card risk-details">
            <h4>⚠️ Risk Factors</h4>
            <ul>
              {result.risk_assessment.reasons.map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="social-section">
        <h4>🔗 Social Profiles</h4>
        <div className="social-links">
          {Object.entries(result.social_profiles).map(([platform, data]) => (
            <a key={platform} href={data.url} target="_blank" rel="noopener noreferrer" 
               className="social-link">
              {platform.toUpperCase()}
            </a>
          ))}
        </div>
      </div>
    </div>
  );

  return (
    <div className="app">
      <header>
        <h1>📱 PhoneTrace</h1>
        <p>Phone Number Intelligence & Risk Assessment</p>
      </header>

      <div className="search-container">
        <div className="input-group">
          <input
            type="tel"
            value={number}
            onChange={(e) => setNumber(e.target.value)}
            placeholder="+1 555-123-4567 or 5551234567"
            className="phone-input"
            onKeyPress={(e) => e.key === 'Enter' && lookupNumber()}
          />
          <button 
            onClick={lookupNumber} 
            disabled={loading || !number.trim()}
            className="search-btn"
          >
            {loading ? '🔍 Searching...' : '🔍 Trace Number'}
          </button>
        </div>
      </div>

      {recent.length > 0 && (
        <div className="recent-section">
          <h3>Recent Searches</h3>
          <div className="recent-grid">
            {recent.map((item, idx) => (
              <div key={idx} className="recent-item" 
                   onClick={() => setNumber(item.number.split(' ')[0])}>
                <strong>{item.number}</strong>
                <span className={`risk-tag ${item.risk.toLowerCase()}`}>
                  {item.risk}
                </span>
                <small>{item.timestamp}</small>
              </div>
            ))}
          </div>
        </div>
      )}

      {result && !result.error ? (
        <ResultDisplay result={result} />
      ) : result?.error && (
        <div className="error-card">
          <h3>❌ Error</h3>
          <p>{result.error}</p>
          <button onClick={() => setResult(null)} className="clear-btn">Clear</button>
        </div>
      )}
    </div>
  );
}

export default App;
