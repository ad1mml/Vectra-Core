// VectraCore service worker
// Kept intentionally minimal: its main job is to make the site installable
// as a PWA. It also caches the static "app shell" (HTML/CSS/icons) so the
// app opens even on a flaky connection — it never caches API calls, so
// chart analysis, login, and everything else always hits the live server.

const CACHE_NAME = "vectracore-shell-v2";

const APP_SHELL = [
  "/",
  "/index.html",
  "/work.html",
  "/pricing.html",
  "/about-us.html",
  "/contact-us.html",
  "/privacy-policy.html",
  "/refund-policy.html",
  "/logo.jpeg",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Only handle simple same-origin GET requests. Everything else
  // (POST /api/analyze-chart, /api/verify-email, etc.) passes straight
  // through to the network untouched.
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) {
    return;
  }

  // Never cache API routes — those must always be live.
  if (new URL(request.url).pathname.startsWith("/api/")) {
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => cached);

      // Cache-first for instant loads, refreshed in the background.
      return cached || network;
    })
  );
});
