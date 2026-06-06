/* Service Worker —— 离线壳（R-07：农村信号差时也能看）。
 *
 * 策略（network-first 为主，避免开发期/测试期被旧缓存坑）：
 *  - 导航/静态资源：先走网络，成功则更新缓存；失败回退缓存。
 *  - 只读 API（今日农事、预警）：先走网络，失败回退上次缓存。
 *  - 其他（POST /api/diagnose、/api/chat、/api/tts 等）：直连，不缓存。
 */
const CACHE = 'ai-nong-v1';
const SHELL = ['/', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png'];
const CACHEABLE_API = ['/api/calendar/today', '/api/alerts'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return; // POST 等不拦截

  const url = new URL(req.url);
  const isApi = url.pathname.startsWith('/api/');
  const cacheableApi = CACHEABLE_API.some((p) => url.pathname.startsWith(p));

  // 不可缓存的 API（诊断/问答/TTS）直连
  if (isApi && !cacheableApi) return;

  // network-first
  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.status === 200 && (cacheableApi || !isApi)) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then((hit) => hit || caches.match('/'))
      )
  );
});
