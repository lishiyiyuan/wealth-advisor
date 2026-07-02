// Self-destruct Service Worker
// This SW unregisters itself and clears all caches
self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(names.map(function(name) { return caches.delete(name); }));
    }).then(function() {
      // Self-unregister
      return self.registration.unregister();
    }).then(function() {
      return clients.claim();
    })
  );
});

// Don't cache anything - let all requests through
self.addEventListener('fetch', function(event) {
  event.respondWith(fetch(event.request));
});
