const CACHE_NAME = 'pastel-blooms-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon.svg',
  '/static/css/themes.css',
  '/static/css/style.css',
  '/static/css/animations.css',
  '/static/js/sound.js',
  '/static/js/flower-cursor.js',
  '/static/js/smart-parser.js',
  '/static/js/mascot.js',
  '/static/js/garden.js',
  '/static/js/app.js'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).catch(err => console.log('SW cache error during install:', err))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Let API requests go directly to network
  if (e.request.url.includes('/api/')) {
    return;
  }
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      return cachedResponse || fetch(e.request).catch(() => {
        if (e.request.destination === 'document') {
          return caches.match('/');
        }
      });
    })
  );
});

