export default {
  async fetch(request, env) {
    // CORS headers for cross-origin requests from GitHub Pages
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, PUT, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    const url = new URL(request.url);
    const path = url.pathname;
    const rawKey = url.searchParams.get('key');

    // Validate sync key
    if (!rawKey || rawKey.length < 8) {
      return jsonResponse({ error: 'Sync key must be at least 8 characters' }, 400, corsHeaders);
    }

    // Hash the key with SHA-256
    const keyHash = await hashKey(rawKey);

    try {
      // GET /sync — retrieve current data
      if (path === '/sync' && request.method === 'GET') {
        const stored = await env.IRONLOG_DATA.get(keyHash, { type: 'json' });
        if (!stored) {
          return jsonResponse({ exists: false }, 200, corsHeaders);
        }
        return jsonResponse({ exists: true, data: stored.data, serverUpdatedAt: stored.serverUpdatedAt }, 200, corsHeaders);
      }

      // PUT /sync — store data
      if (path === '/sync' && request.method === 'PUT') {
        const body = await request.json();

        // Validate payload
        if (!body || typeof body !== 'object') {
          return jsonResponse({ error: 'Invalid JSON payload' }, 400, corsHeaders);
        }
        if (!body.version || !body.history) {
          return jsonResponse({ error: 'Missing required fields: version, history' }, 400, corsHeaders);
        }

        // Check size (5MB limit)
        const size = JSON.stringify(body).length;
        if (size > 5 * 1024 * 1024) {
          return jsonResponse({ error: 'Payload too large (max 5MB)' }, 413, corsHeaders);
        }

        // Move current to previous (safety net)
        const current = await env.IRONLOG_DATA.get(keyHash, { type: 'json' });
        if (current) {
          await env.IRONLOG_DATA.put(`${keyHash}:previous`, JSON.stringify(current));
        }

        // Store new data with server timestamp
        const stored = {
          data: body,
          serverUpdatedAt: new Date().toISOString(),
        };
        await env.IRONLOG_DATA.put(keyHash, JSON.stringify(stored));

        return jsonResponse({ ok: true, serverUpdatedAt: stored.serverUpdatedAt }, 200, corsHeaders);
      }

      // GET /sync/previous — emergency recovery
      if (path === '/sync/previous' && request.method === 'GET') {
        const previous = await env.IRONLOG_DATA.get(`${keyHash}:previous`, { type: 'json' });
        if (!previous) {
          return jsonResponse({ exists: false }, 200, corsHeaders);
        }
        return jsonResponse({ exists: true, data: previous.data, serverUpdatedAt: previous.serverUpdatedAt }, 200, corsHeaders);
      }

      return jsonResponse({ error: 'Not found' }, 404, corsHeaders);
    } catch (err) {
      return jsonResponse({ error: 'Internal server error' }, 500, corsHeaders);
    }
  },
};

async function hashKey(key) {
  const encoder = new TextEncoder();
  const data = encoder.encode(key);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
}

function jsonResponse(body, status, corsHeaders) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders },
  });
}
