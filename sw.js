// 智能投顾 PWA Service Worker v1.0
const CACHE_NAME = 'wealth-advisor-v2';
const APP_SHELL = [
  './',
  './index.html',
  './manifest.json',
  './mobile.html',
];

// 安装：预缓存应用外壳
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[SW] 预缓存应用外壳');
      return cache.addAll(APP_SHELL);
    })
  );
  self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

// 请求策略：数据文件走网络优先，其他走缓存优先
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // daily.json / products.json 始终走网络（保证数据最新）
  if (url.pathname.endsWith('daily.json') || url.pathname.endsWith('products.json')) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // 应用外壳走缓存优先
  event.respondWith(cacheFirst(event.request));
});

// 缓存优先策略
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch (e) {
    // 离线时返回缓存
    const fallback = await caches.match(request);
    return fallback || new Response('离线状态下不可用', { status: 503 });
  }
}

// 网络优先策略（用于 data.json）
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch (e) {
    const cached = await caches.match(request);
    return cached || new Response('离线状态下不可用', { status: 503 });
  }
}
