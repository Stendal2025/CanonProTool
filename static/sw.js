const CACHE_NAME = "canon-pro-tool-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/manifest.json",
  "https://cdn-icons-png.flaticon.com/512/2983/2983796.png",
  "https://openweathermap.org/img/wn/01d@2x.png",
  "https://openweathermap.org/img/wn/02d@2x.png",
  "https://openweathermap.org/img/wn/03d@2x.png",
  "https://openweathermap.org/img/wn/04d@2x.png",
  "https://openweathermap.org/img/wn/09d@2x.png",
  "https://openweathermap.org/img/wn/10d@2x.png",
  "https://openweathermap.org/img/wn/11d@2x.png",
  "https://openweathermap.org/img/wn/13d@2x.png",
  "https://openweathermap.org/img/wn/50d@2x.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(cached => {
      const fetchPromise = fetch(event.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
