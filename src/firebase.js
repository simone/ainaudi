/**
 * Firebase initialization for push notifications.
 *
 * Configure these values from your Firebase project console:
 * Project Settings → General → Your Apps → Web App
 */
import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage, isSupported } from 'firebase/messaging';

// Firebase config - these are public keys, safe to commit
// Replace with your actual Firebase project config
const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
    appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
};

const VAPID_KEY = import.meta.env.VITE_FCM_VAPID_KEY || '';

let app = null;
let messaging = null;

/**
 * Initialize Firebase app and messaging.
 * Returns null if Firebase is not configured or not supported.
 */
export async function initFirebase() {
    if (messaging) return messaging;

    // Check if Firebase is configured
    if (!firebaseConfig.apiKey || !firebaseConfig.projectId) {
        console.warn('Firebase not configured. Push notifications disabled.');
        return null;
    }

    // Check if messaging is supported in this browser
    const supported = await isSupported();
    if (!supported) {
        console.warn('Firebase Messaging not supported in this browser.');
        return null;
    }

    try {
        app = initializeApp(firebaseConfig);
        messaging = getMessaging(app);
        return messaging;
    } catch (error) {
        console.error('Failed to initialize Firebase:', error);
        return null;
    }
}

/**
 * Request notification permission and get FCM token.
 *
 * @returns {string|null} FCM token or null if permission denied/error
 */
export async function requestPushToken() {
    const msg = await initFirebase();
    if (!msg) return null;

    if (!VAPID_KEY) {
        console.warn('VAPID key not configured. Cannot get push token.');
        return null;
    }

    try {
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            console.log('Notification permission denied');
            return null;
        }

        // Ensure our Firebase SW is registered and use it explicitly
        let swReg = await navigator.serviceWorker.getRegistration('/firebase-messaging-sw.js');
        if (!swReg) {
            console.log('Registering Firebase messaging service worker...');
            swReg = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
            await navigator.serviceWorker.ready;
        }
        console.log('Using SW:', swReg.scope);

        const token = await getToken(msg, {
            vapidKey: VAPID_KEY,
            serviceWorkerRegistration: swReg,
        });

        console.log('FCM token obtained:', token?.substring(0, 20) + '...');
        return token;
    } catch (error) {
        console.error('Failed to get push token:', error);
        return null;
    }
}

/**
 * Register handler for foreground messages (when app is open).
 *
 * Initializes Firebase if needed, then registers the onMessage listener.
 *
 * @param {Function} callback - receives { title, body, data } for each message
 * @returns {Function} unsubscribe function
 */
export function onForegroundMessage(callback) {
    let unsubscribe = () => {};

    // Initialize async, then register listener
    initFirebase().then((msg) => {
        if (!msg) return;
        unsubscribe = onMessage(msg, (payload) => {
            console.log('Foreground message received:', payload);
            callback({
                title: payload.notification?.title || '',
                body: payload.notification?.body || '',
                data: payload.data || {},
            });
        });
        console.log('FCM foreground listener registered');
    });

    // Return a function that will unsubscribe once the listener is set
    return () => unsubscribe();
}
