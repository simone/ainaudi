import React, { useState, useEffect } from 'react';

/**
 * ThemeSwitcher Component
 * Permette di switchare tra il tema standard e il tema "VOTA NO" della campagna referendum
 */
const ThemeSwitcher = () => {
  const [theme, setTheme] = useState(() => {
    // Recupera il tema salvato o usa 'standard' come default
    return localStorage.getItem('app-theme') || 'standard';
  });

  useEffect(() => {
    // Applica il tema al DOM
    if (theme === 'referendum-no') {
      document.documentElement.setAttribute('data-theme', 'referendum-no');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    // Salva la preferenza
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'standard' ? 'referendum-no' : 'standard');
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
          background: theme === 'referendum-no' ? '#dc143c' : '#007bff',
          color: 'white',
          border: 'none',
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
        title={theme === 'referendum-no' ? 'Passa al tema standard' : 'Passa al tema VOTA NO'}
      >
        {theme === 'referendum-no' ? (
          <>
            <span style={{ fontSize: '16px' }}>💼</span>
            <span style={{ fontSize: '12px' }}>Tema Standard</span>
          </>
        ) : (
          <>
            <span style={{ fontSize: '16px' }}>🗳️</span>
            <span style={{ fontSize: '12px' }}>Tema VOTA NO</span>
          </>
        )}
      </button>
    </div>
  );
};

export default ThemeSwitcher;
