export default {
  async fetch(request) {
    const url = new URL(request.url);
    const q = url.searchParams.get('q') || '';
    const count = url.searchParams.get('count') || '5';
    const country = url.searchParams.get('country') || 'CN';
    const searchLang = url.searchParams.get('search_lang') || 'zh-hans';

    // 健康检查
    if (!q) {
      return new Response(JSON.stringify({ error: 'missing q parameter' }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    }

    const params = new URLSearchParams({ q, count, country, search_lang });
    const braveUrl = `https://api.search.brave.com/res/v1/web/search?${params}`;

    try {
      const resp = await fetch(braveUrl, {
        headers: {
          'Accept': 'application/json',
          'X-Subscription-Token': 'BSAEc7j1_i2PtwCRHjXYnRhlUZZjULK'
        }
      });

      const data = await resp.json();

      // 只返回 web results，减少传输量
      const slim = {
        results: (data.web?.results || []).map(r => ({
          title: r.title,
          url: r.url,
          description: r.description
        }))
      };

      return new Response(JSON.stringify(slim), {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Cache-Control': 'public, max-age=60'
        }
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    }
  }
};
