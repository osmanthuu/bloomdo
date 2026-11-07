const CACHE_NAME = 'pastel-blooms-v2';

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(keys.map(k => caches.delete(k)));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Always fetch fresh HTML navigation requests from network
  if (e.request.mode === 'navigate' || e.request.destination === 'document') {
    e.respondWith(fetch(e.request));
    return;
  }
  // API requests go straight to network
  if (e.request.url.includes('/api/')) {
    return;
  }
  // Cache other static assets with network fallback
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
