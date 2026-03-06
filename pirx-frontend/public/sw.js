// PIRX Service Worker for Push Notifications & Offline Caching
const CACHE_NAME = "pirx-v2";
const API_CACHE = "pirx-api-v1";

const STALE_WHILE_REVALIDATE_ROUTES = [
  "/projection",
  "/drivers",
  "/readiness",
  "/features/zones",
  "/metrics/weekly",
];

const OFFLINE_FALLBACK = new Response(
  JSON.stringify({ offline: true, message: "You are offline. Data will refresh when connectivity returns." }),
  { headers: { "Content-Type": "application/json" } }
);

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(["/", "/dashboard", "/offline"])
    ).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  const KEEP = [CACHE_NAME, API_CACHE];
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => !KEEP.includes(k)).map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

function shouldCacheApiRoute(pathname) {
  return STALE_WHILE_REVALIDATE_ROUTES.some((route) => pathname.includes(route));
}

function staleWhileRevalidate(request) {
  return caches.open(API_CACHE).then((cache) =>
    cache.match(request).then((cached) => {
      const networkFetch = fetch(request)
        .then((response) => {
          if (response.ok) {
            cache.put(request, response.clone());
          }
          return response;
        })
        .catch(() => cached || OFFLINE_FALLBACK.clone());

      return cached || networkFetch;
    })
  );
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (event.request.method !== "GET") return;

  if (shouldCacheApiRoute(url.pathname)) {
    event.respondWith(staleWhileRevalidate(event.request));
    return;
  }

  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(event.request).then((cached) =>
        cached || fetch(event.request).catch(() => {
          if (event.request.mode === "navigate") {
            return caches.match("/offline") || OFFLINE_FALLBACK.clone();
          }
          return OFFLINE_FALLBACK.clone();
        })
      )
    );
    return;
  }
});

self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  const title = data.title || "PIRX Update";
  const options = {
    body: data.body || "",
    icon: "/icon-192.png",
    badge: "/icon-72.png",
    tag: data.notification_type || "pirx",
    data: { deep_link: data.deep_link || "/" },
    vibrate: [100, 50, 100],
    actions: [{ action: "open", title: "View" }],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const deepLink = event.notification.data?.deep_link || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          client.navigate(deepLink);
          return client.focus();
        }
      }
      return self.clients.openWindow(deepLink);
    })
  );
});
