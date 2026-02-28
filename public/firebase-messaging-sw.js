/**
 * Firebase Cloud Messaging Service Worker
 *
 * Handles background push notifications when the app is not in focus.
 * Also handles notification click events for deep linking.
 *
 * Configuration: edit public/firebase-config.js with your Firebase project values.
 */

/* eslint-disable no-undef */
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');
importScripts('/firebase-config.js');

// Initialize using config from firebase-config.js
firebase.initializeApp(FIREBASE_CONFIG);

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
    console.log('[SW] Background message received:', payload);

    const notificationTitle = payload.data?.title || 'AInaudi';
    const notificationOptions = {
        body: payload.data?.body || '',
        icon: '/icon-192.png',
        badge: '/icon-192.png',
        data: payload.data || {},
        tag: payload.data?.notification_id || 'default',
        vibrate: [200, 100, 200],
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click → deep link to the app
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification click:', event);

    event.notification.close();

    const deepLink = event.notification.data?.deep_link || '/';
    const urlToOpen = new URL(deepLink, self.location.origin).href;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Try to focus an existing window
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        client.postMessage({
                            type: 'NOTIFICATION_CLICK',
                            deep_link: deepLink,
                        });
                        return client.focus();
                    }
                }
                // Open a new window if none exists
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});
