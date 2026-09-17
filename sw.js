// Harness Executive OS - Universal Unified Service Worker (v4.5)
const CACHE_NAME = 'harness-unified-v4.5';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.png',
  '/apple-touch-icon.png',
  '/icon-192.png',
  '/icon-512.png',
  '/css/app.css?v=4.5',
  '/js/api_bridge.js?v=4.5',
  '/js/metro.js?v=4.5',
  '/js/dashboard.js?v=4.5',
  '/js/today.js?v=4.5',
  '/js/tum.js?v=4.5',
  '/js/projects.js?v=4.5',
  '/js/body.js?v=4.5',
  '/js/knowledge.js?v=4.5',
  '/js/focus_timer.js?v=4.5',
  '/js/command_palette.js?v=4.5',
  '/js/kill_list.js?v=4.5',
  '/js/app.js?v=4.5'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[SW] Cache prefetch notice:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW] Purging outdated cache:', key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // Never cache API or RPC mutations
  if (url.includes('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(JSON.stringify({ error: 'Network offline (cached)' }), {
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }

  // Network-first for HTML pages and app scripts to guarantee freshness
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200 && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
