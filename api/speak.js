// Algevia: POST /api/speak -> natural-sounding speech (mp3) for one tutor step, using OpenAI text-to-speech.
// Vercel environment (same as tutor.js): OPENAI_API_KEY, KV_REST_API_URL, KV_REST_API_TOKEN.
// Optional: OPENAI_TTS_MODEL (default tts-1), OPENAI_TTS_VOICE_F (default nova), OPENAI_TTS_VOICE_M (default onyx), RATE_LIMIT_SALT.
// Own counters, separate from the tutor, hint and question endpoints. Costs real money per character, so limits are strict.
const crypto = require('crypto');
const MAX_BODY_BYTES = 4000;
const MAX_CHARS = 600;
const PER_MINUTE = 12, PER_DAY = 150, GLOBAL_DAY = 3000;
const MODEL = process.env.OPENAI_TTS_MODEL || 'tts-1';
const VOICE_F = process.env.OPENAI_TTS_VOICE_F || 'nova';
const VOICE_M = process.env.OPENAI_TTS_VOICE_M || 'onyx';

async function redisEval(script, keys, args) {
  const url = process.env.KV_REST_API_URL, token = process.env.KV_REST_API_TOKEN;
  if (!url || !token) throw Error('Redis is not configured');
  const response = await fetch(url.replace(/\/$/, '') + '/pipeline', {
    method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify([['EVAL', script, keys.length, ...keys, ...args.map(String)]]), signal: AbortSignal.timeout(4000)
  });
  if (!response.ok) throw Error('Redis request failed');
  const results = await response.json();
  if (!Array.isArray(results) || results.length !== 1 || results[0].error || !Array.isArray(results[0].result)) throw Error('Redis script failed');
  return results[0].result.map(Number);
}
const LIMIT_SCRIPT = `
local rolling = KEYS[1]
local daily = KEYS[2]
local global = KEYS[3]
local now = tonumber(ARGV[1])
local unique = ARGV[2]
local dailyttl = tonumber(ARGV[3])
local pm = tonumber(ARGV[4])
local pd = tonumber(ARGV[5])
local gd = tonumber(ARGV[6])
redis.call('ZREMRANGEBYSCORE', rolling, '-inf', now - 60000)
local perMinute = redis.call('ZCARD', rolling)
local perDay = tonumber(redis.call('GET', daily) or '0')
local totalDay = tonumber(redis.call('GET', global) or '0')
if perMinute >= pm then return {0, 60, 1} end
if perDay >= pd then return {0, 3600, 2} end
if totalDay >= gd then return {0, 3600, 3} end
redis.call('ZADD', rolling, now, unique)
redis.call('PEXPIRE', rolling, 61000)
redis.call('INCR', daily)
redis.call('EXPIRE', daily, dailyttl)
redis.call('INCR', global)
redis.call('EXPIRE', global, dailyttl)
return {1, 0, 0}
`;
const REFUND_SCRIPT = `
redis.call('ZREM', KEYS[1], ARGV[1])
if tonumber(redis.call('GET', KEYS[2]) or '0') > 0 then redis.call('DECR', KEYS[2]) end
if tonumber(redis.call('GET', KEYS[3]) or '0') > 0 then redis.call('DECR', KEYS[3]) end
return {1}
`;

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store'); res.setHeader('X-Content-Type-Options', 'nosniff');
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST required' });
  if (!process.env.OPENAI_API_KEY) return res.status(503).json({ error: 'AI is not configured' });
  if (!process.env.KV_REST_API_URL || !process.env.KV_REST_API_TOKEN) return res.status(503).json({ error: 'Security is not configured' });
  if (Number(req.headers['content-length'] || 0) > MAX_BODY_BYTES) return res.status(413).json({ error: 'Request too large' });
  const d = req.body;
  if (!d || typeof d !== 'object' || Array.isArray(d) || typeof d.text !== 'string') return res.status(400).json({ error: 'Invalid request' });
  const text = d.text.replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (text.length < 2 || text.length > MAX_CHARS) return res.status(400).json({ error: 'Invalid request' });
  const voice = d.voice === 'male' ? VOICE_M : VOICE_F;

  const fwd = req.headers['x-vercel-forwarded-for'] || req.headers['x-real-ip'] || req.headers['x-forwarded-for'];
  const ip = String(fwd || '').split(',')[0].trim();
  if (!ip || ip.length > 100) return res.status(503).json({ error: 'Client identity unavailable' });
  const id = crypto.createHash('sha256').update(ip + ':' + (process.env.RATE_LIMIT_SALT || 'algevia-v38')).digest('hex').slice(0, 24);
  const now = Date.now(), day = Math.floor(now / 86400000), ttl = Math.ceil(((day + 1) * 86400000 - now) / 1000) + 60;
  const keys = [`algevia:s1:rolling:${id}`, `algevia:s1:day:${id}:${day}`, `algevia:s1:global:${day}`];
  const uniq = `${now}:${crypto.randomUUID()}`;
  try {
    const [allow, retry, why] = await redisEval(LIMIT_SCRIPT, keys, [now, uniq, ttl, PER_MINUTE, PER_DAY, GLOBAL_DAY]);
    if (!allow) {
      res.setHeader('Retry-After', String(retry));
      return res.status(429).json({ error: why === 1 ? 'Too many voice requests in the last minute.' : why === 2 ? 'You have used all of today\'s natural-voice allowance.' : 'The natural voice is busy today.' });
    }
  } catch (e) { console.error('Speak limiter failure:', e.message); return res.status(503).json({ error: 'Temporarily unavailable: security check failed' }); }
  const refund = async () => { try { await redisEval(REFUND_SCRIPT, keys, [uniq]); } catch (e) { console.error('Refund failed:', e.message); } };

  const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 15000);
  try {
    const r = await fetch('https://api.openai.com/v1/audio/speech', {
      method: 'POST', signal: ctl.signal,
      headers: { Authorization: 'Bearer ' + process.env.OPENAI_API_KEY, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: MODEL, voice, input: text, response_format: 'mp3', speed: 0.95 })
    });
    if (!r.ok) { await refund(); return res.status(502).json({ error: 'Voice provider returned an error (' + r.status + ')' }); }
    const buf = Buffer.from(await r.arrayBuffer());
    if (!buf.length) { await refund(); return res.status(502).json({ error: 'Empty audio' }); }
    res.setHeader('Content-Type', 'audio/mpeg'); res.setHeader('Content-Length', String(buf.length));
    return res.status(200).send(buf);
  } catch (e) {
    await refund(); console.error('Speak failure:', e.message);
    return res.status(502).json({ error: 'Voice unavailable' });
  } finally { clearTimeout(timer); }
};
module.exports.config = { maxDuration: 20 };
