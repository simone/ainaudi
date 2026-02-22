// AuthContext.js
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const AuthContext = createContext(null);

// Use empty string to leverage Vite proxy in development (vite.config.js)
// In production, use empty string for same-origin requests
const SERVER_API = '';

// Token storage keys
const ACCESS_TOKEN_KEY = 'rdl_access_token';
const REFRESH_TOKEN_KEY = 'rdl_refresh_token';
const USER_KEY = 'rdl_user';
// Original user tokens (for impersonation)
const ORIGINAL_ACCESS_TOKEN_KEY = 'rdl_original_access_token';
const ORIGINAL_REFRESH_TOKEN_KEY = 'rdl_original_refresh_token';
const ORIGINAL_USER_KEY = 'rdl_original_user';

/**
 * Decode JWT payload to read exp claim.
 * Returns expiry as Unix timestamp (seconds) or 0 if unreadable.
 */
const getTokenExpiry = (token) => {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.exp || 0;
    } catch {
        return 0;
    }
};

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [accessToken, setAccessToken] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isImpersonating, setIsImpersonating] = useState(false);
    const [originalUser, setOriginalUser] = useState(null);
    const refreshTimerRef = useRef(null);

    // Load stored auth on mount
    useEffect(() => {
        const storedToken = localStorage.getItem(ACCESS_TOKEN_KEY);
        const storedUser = localStorage.getItem(USER_KEY);
        const storedOriginalUser = localStorage.getItem(ORIGINAL_USER_KEY);

        if (storedToken && storedUser) {
            setAccessToken(storedToken);
            setUser(JSON.parse(storedUser));

            // Check if we're impersonating
            if (storedOriginalUser) {
                setIsImpersonating(true);
                setOriginalUser(JSON.parse(storedOriginalUser));
            }

            // Verify token is still valid
            verifyToken(storedToken).then(valid => {
                if (!valid) {
                    // Try refresh
                    refreshToken().catch(() => {
                        logout();
                    });
                }
                setLoading(false);
            });
        } else {
            setLoading(false);
        }
    }, []);

    // Auto-refresh token 10 seconds before expiry
    useEffect(() => {
        if (refreshTimerRef.current) {
            clearTimeout(refreshTimerRef.current);
            refreshTimerRef.current = null;
        }

        if (!accessToken) return;

        const exp = getTokenExpiry(accessToken);
        if (!exp) return;

        const now = Math.floor(Date.now() / 1000);
        const timeUntilRefresh = (exp - now - 10) * 1000; // 10s before expiry, in ms

        if (timeUntilRefresh <= 0) {
            // Token already expired or about to, refresh now
            refreshToken().catch(() => { /* logout handled inside */ });
            return;
        }

        refreshTimerRef.current = setTimeout(() => {
            refreshToken().catch(() => { /* logout handled inside */ });
        }, timeUntilRefresh);

        return () => {
            if (refreshTimerRef.current) {
                clearTimeout(refreshTimerRef.current);
            }
        };
    }, [accessToken]);

    // Verify token with backend
    const verifyToken = async (token) => {
        try {
            const response = await fetch(`${SERVER_API}/api/auth/token/verify/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            });
            return response.ok;
        } catch {
            return false;
        }
    };

    // Refresh access token
    const refreshToken = async () => {
        const refresh = localStorage.getItem(REFRESH_TOKEN_KEY);
        if (!refresh) throw new Error('No refresh token');

        const response = await fetch(`${SERVER_API}/api/auth/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh })
        });

        if (!response.ok) throw new Error('Refresh failed');

        const data = await response.json();
        localStorage.setItem(ACCESS_TOKEN_KEY, data.access);
        setAccessToken(data.access);
        return data.access;
    };

    // Request magic link
    const requestMagicLink = async (email) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${SERVER_API}/api/auth/magic-link/request/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }

            setLoading(false);
            return data;
        } catch (err) {
            setError(err.message);
            setLoading(false);
            throw err;
        }
    };

    // Verify magic link token or OTP code
    const verifyMagicLink = async (tokenOrOtp, email = null) => {
        setLoading(true);
        setError(null);

        const payload = email
            ? { otp: tokenOrOtp, email }
            : { token: tokenOrOtp };

        try {
            const response = await fetch(`${SERVER_API}/api/auth/magic-link/verify/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Verification failed');
            }

            const data = await response.json();

            // Store tokens
            localStorage.setItem(ACCESS_TOKEN_KEY, data.access);
            localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh);
            localStorage.setItem(USER_KEY, JSON.stringify(data.user));

            setAccessToken(data.access);
            setUser(data.user);
            setLoading(false);

            return data;
        } catch (err) {
            setError(err.message);
            setLoading(false);
            throw err;
        }
    };

    // Logout
    const logout = useCallback(() => {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        // Also clear impersonation data
        localStorage.removeItem(ORIGINAL_ACCESS_TOKEN_KEY);
        localStorage.removeItem(ORIGINAL_REFRESH_TOKEN_KEY);
        localStorage.removeItem(ORIGINAL_USER_KEY);
        setAccessToken(null);
        setUser(null);
        setError(null);
        setIsImpersonating(false);
        setOriginalUser(null);
    }, []);

    // Impersonate another user (superuser only)
    const impersonate = async (email) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${SERVER_API}/api/auth/impersonate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({ email })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Impersonation failed');
            }

            const data = await response.json();

            // Save original user tokens BEFORE switching (only if not already impersonating)
            if (!isImpersonating) {
                localStorage.setItem(ORIGINAL_ACCESS_TOKEN_KEY, accessToken);
                localStorage.setItem(ORIGINAL_REFRESH_TOKEN_KEY, localStorage.getItem(REFRESH_TOKEN_KEY));
                localStorage.setItem(ORIGINAL_USER_KEY, JSON.stringify(user));
                setOriginalUser(user);
            }

            // Store new tokens for impersonated user
            localStorage.setItem(ACCESS_TOKEN_KEY, data.access);
            localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh);
            localStorage.setItem(USER_KEY, JSON.stringify(data.user));

            setAccessToken(data.access);
            setUser(data.user);
            setIsImpersonating(true);
            setLoading(false);

            return data;
        } catch (err) {
            setError(err.message);
            setLoading(false);
            throw err;
        }
    };

    // Stop impersonating and return to original user
    const stopImpersonating = useCallback(() => {
        const originalAccessToken = localStorage.getItem(ORIGINAL_ACCESS_TOKEN_KEY);
        const originalRefreshToken = localStorage.getItem(ORIGINAL_REFRESH_TOKEN_KEY);
        const originalUserData = localStorage.getItem(ORIGINAL_USER_KEY);

        if (!originalAccessToken || !originalUserData) {
            setError('No original user data found');
            return;
        }

        // Restore original user tokens
        localStorage.setItem(ACCESS_TOKEN_KEY, originalAccessToken);
        if (originalRefreshToken) {
            localStorage.setItem(REFRESH_TOKEN_KEY, originalRefreshToken);
        }
        localStorage.setItem(USER_KEY, originalUserData);

        // Clear original user storage
        localStorage.removeItem(ORIGINAL_ACCESS_TOKEN_KEY);
        localStorage.removeItem(ORIGINAL_REFRESH_TOKEN_KEY);
        localStorage.removeItem(ORIGINAL_USER_KEY);

        // Update state
        setAccessToken(originalAccessToken);
        setUser(JSON.parse(originalUserData));
        setIsImpersonating(false);
        setOriginalUser(null);
    }, []);

    // Get valid token (refresh if needed) - used on app startup
    const getValidToken = useCallback(async () => {
        if (!accessToken) return null;

        const valid = await verifyToken(accessToken);
        if (valid) return accessToken;

        try {
            return await refreshToken();
        } catch {
            logout();
            return null;
        }
    }, [accessToken, logout]);

    // Refresh access token directly (no verify round-trip) - used by API client
    const refreshAccessToken = useCallback(async () => {
        try {
            return await refreshToken();
        } catch {
            logout();
            return null;
        }
    }, [logout]);

    const value = {
        user,
        accessToken,
        loading,
        error,
        isAuthenticated: !!accessToken && !!user,
        isImpersonating,
        originalUser,
        requestMagicLink,
        verifyMagicLink,
        logout,
        getValidToken,
        refreshAccessToken,
        setError,
        impersonate,
        stopImpersonating,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

export default AuthContext;
