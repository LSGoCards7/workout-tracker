const CACHE_NAME = 'ironlog-cache-v1';
const ASSETS = [
  './',
  './iron_log.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

// Font URLs to cache (Google Fonts)
const FONT_URLS = [
  'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // Cache local assets
      await cache.addAll(ASSETS);
      // Cache fonts (best-effort — don't fail install if fonts are unavailable)
      for (const url of FONT_URLS) {
        try {
          const resp = await fetch(url);
          if (resp.ok) {
            await cache.put(url, resp.clone());
            // Parse CSS to find woff2 URLs and cache them too
            const css = await resp.text();
            const woff2Urls = css.match(/url\((https:\/\/fonts\.gstatic\.com\/[^)]+)\)/g);
            if (woff2Urls) {
              for (const match of woff2Urls) {
                const fontUrl = match.slice(4, -1);
                try {
                  const fontResp = await fetch(fontUrl);
                  if (fontResp.ok) await cache.put(fontUrl, fontResp);
                } catch (_) { /* font file cache miss is OK */ }
              }
            }
          }
        } catch (_) { /* font cache miss is OK — falls back to monospace */ }
      }
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never cache sync API calls (Cloudflare Worker URLs)
  if (url.pathname.includes('/sync')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Cache-first for everything else
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        // Cache successful GET responses for fonts
        if (event.request.method === 'GET' && response.ok &&
            (url.origin === 'https://fonts.googleapis.com' || url.origin === 'https://fonts.gstatic.com')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    }).catch(() => {
      // Offline fallback — serve the cached app shell
      if (event.request.mode === 'navigate') {
        return caches.match('./iron_log.html');
      }
    })
  );
});
