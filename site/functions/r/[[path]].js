/**
 * AI Recommend report page logging function.
 * Logs report views to D1 without storing IP addresses.
 *
 * Bindings required in wrangler.toml or Pages dashboard:
 *   [[d1_databases]]
 *   binding = "DB"
 *   database_name = "airecommend-log"
 *   database_id = "<your-database-id>"
 *
 * D1 schema (run once via wrangler d1 execute):
 *   CREATE TABLE IF NOT EXISTS hits (
 *     id INTEGER PRIMARY KEY AUTOINCREMENT,
 *     ts TEXT NOT NULL,
 *     slug TEXT NOT NULL,
 *     path TEXT NOT NULL,
 *     country TEXT,
 *     user_agent TEXT,
 *     asn INTEGER
 *   );
 *   CREATE INDEX IF NOT EXISTS idx_hits_slug ON hits(slug);
 *   CREATE INDEX IF NOT EXISTS idx_hits_ts ON hits(ts);
 */

export async function onRequest(context) {
  const { request, env, next, params } = context;

  // Extract slug from path (first segment after /r/)
  const pathParts = params.path || [];
  const slug = pathParts[0] || 'unknown';
  const fullPath = '/r/' + pathParts.join('/');

  // Get request metadata (no IP stored)
  const cf = request.cf || {};
  const country = cf.country || null;
  const asn = cf.asn || null;
  const userAgent = request.headers.get('user-agent') || null;
  const ts = new Date().toISOString();

  // Log to D1 if binding exists (non-blocking)
  if (env.DB) {
    try {
      await env.DB.prepare(
        'INSERT INTO hits (ts, slug, path, country, user_agent, asn) VALUES (?, ?, ?, ?, ?, ?)'
      ).bind(ts, slug, fullPath, country, userAgent, asn).run();
    } catch (err) {
      // Log but don't fail the request
      console.error('D1 logging error:', err.message);
    }
  }

  // Serve the static page
  return next();
}
