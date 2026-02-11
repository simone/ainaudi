import React, { useState, useEffect } from 'react';

/**
 * ThemeSwitcher Component
 * Permette di switchare tra il tema Daily (light) e Night (dark)
 * Rileva automaticamente le preferenze di sistema (prefers-color-scheme)
 */
const ThemeSwitcher = () => {
  // Funzione per rilevare la preferenza di sistema
  const getSystemTheme = () => {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'night';
    }
    return 'daily';
  };

  const [theme, setTheme] = useState(() => {
    // 1. Controlla se c'è una preferenza manuale salvata
    const savedTheme = localStorage.getItem('app-theme');
    if (savedTheme) {
      return savedTheme;
    }
    
    // 2. Altrimenti usa le preferenze di sistema
    return getSystemTheme();
  });

  useEffect(() => {
    // Applica il tema al DOM
    if (theme === 'night') {
      document.documentElement.setAttribute('data-theme', 'night');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    // Salva la preferenza (override manuale)
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  useEffect(() => {
    // Listener per cambiamenti nelle preferenze di sistema
    // (solo se l'utente NON ha fatto override manuale)
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e) => {
      // Se l'utente ha già fatto una scelta manuale, non sovrascrivere
      const savedTheme = localStorage.getItem('app-theme');
      if (!savedTheme) {
        setTheme(e.matches ? 'night' : 'daily');
      }
    };

    // Aggiungi listener (supporta sia il metodo moderno che quello vecchio)
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else {
      mediaQuery.addListener(handleChange); // Fallback per browser vecchi
    }

    // Cleanup
    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange);
      } else {
        mediaQuery.removeListener(handleChange);
      }
    };
  }, []);

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
