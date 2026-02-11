import React, { useState, useEffect } from 'react';

/**
 * ThemeSwitcher Component
 * Permette di switchare tra il tema Daily (light) e Night (dark)
 */
const ThemeSwitcher = () => {
  const [theme, setTheme] = useState(() => {
    // Recupera il tema salvato o usa 'daily' come default
    return localStorage.getItem('app-theme') || 'daily';
  });

  useEffect(() => {
    // Applica il tema al DOM
    if (theme === 'night') {
      document.documentElement.setAttribute('data-theme', 'night');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    // Salva la preferenza
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'daily' ? 'night' : 'daily');
  };

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      zIndex: 1000
    }}>
      <button
        onClick={toggleTheme}
        className="btn btn-sm"
        style={{
          background: theme === 'night' ? '#1e3a5f' : '#007bff',
          color: 'white',
          border: theme === 'night' ? '2px solid #dc143c' : 'none',
          borderRadius: '24px',
          padding: '10px 20px',
          fontWeight: '600',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'all 0.3s ease'
        }}
        title={theme === 'night' ? 'Passa al tema Daily (chiaro)' : 'Passa al tema Night (scuro)'}
      >
        {theme === 'night' ? (
          <>
            <span style={{ fontSize: '16px' }}>☀️</span>
            <span style={{ fontSize: '12px' }}>Daily</span>
          </>
        ) : (
          <>
            <span style={{ fontSize: '16px' }}>🌙</span>
            <span style={{ fontSize: '12px' }}>Night</span>
          </>
        )}
      </button>
    </div>
  );
};

export default ThemeSwitcher;
