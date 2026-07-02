/**
 * Cloudflare Worker — Bing RSS 搜索代理
 * 部署后访问: https://<your-worker>.workers.dev/search?q=xxx&count=5
 *
 * 部署步骤:
 * 1. npm install -g wrangler  (或 npx wrangler)
 * 2. wrangler login
 * 3. wrangler deploy
 *
 * 免费额度: 100,000 请求/天, 足够个人使用
 */

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const q = url.searchParams.get('q');
    const count = Math.min(parseInt(url.searchParams.get('count')) || 5, 15);

    // CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET',
          'Access-Control-Max-Age': '86400',
        }
      });
    }

    if (!q || q.trim().length < 1) {
      return json({ error: '缺少 q 参数' }, 400);
    }

    try {
      const bingUrl = `https://cn.bing.com/search?format=rss&q=${encodeURIComponent(q)}&count=${count}`;
      const resp = await fetch(bingUrl, {
        headers: { 'User-Agent': 'Mozilla/5.0 (compatible; SearchProxy/1.0)' }
      });

      if (!resp.ok) {
        return json({ error: `Bing 搜索失败: HTTP ${resp.status}` }, 502);
      }

      const xml = await resp.text();
      const results = parseRSS(xml, count);

      return json({ results, source: 'bing', count: results.length });
    } catch (e) {
      return json({ error: e.message || '搜索异常' }, 500);
    }
  }
};

/** 简易 RSS XML → JSON 解析（无外部依赖） */
function parseRSS(xml, max) {
  const items = [];
  // 匹配每个 <item>...</item>
  const itemRe = /<item>([\s\S]*?)<\/item>/gi;
  let match;
  while ((match = itemRe.exec(xml)) !== null && items.length < max) {
    const block = match[1];
    items.push({
      title:   extractTag(block, 'title'),
      link:    extractTag(block, 'link'),
      desc:    stripHtml(extractTag(block, 'description')).slice(0, 300),
      date:    extractTag(block, 'pubDate'),
    });
  }
  return items;
}

function extractTag(xml, tag) {
  const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'i');
  const m = xml.match(re);
  return m ? m[1].trim() : '';
}

function stripHtml(html) {
  return html.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=60',
    }
  });
}
