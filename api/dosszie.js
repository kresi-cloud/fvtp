// Dosszié-kérés a honlapról → GitHub issue az fvtp repóban (címke: dosszie-keres).
// Az ütemezett Claude-feladat a nyitott issue-kat dolgozza fel, és kész dossziéként publikálja.
// Env: GITHUB_TOKEN (finomhangolt PAT, Issues: Read and write az fvtp repóra), GITHUB_REPO (pl. kresi-cloud/fvtp)
import { createClerkClient } from '@clerk/backend';
export const config = { runtime: 'nodejs' };

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();
  const clerk = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY, publishableKey: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY });
  const origin = `https://${req.headers.host}`;
  const state = await clerk.authenticateRequest(new Request(origin + req.url, { method: 'POST', headers: new Headers(req.headers) }), { authorizedParties: [origin] });
  if (!state.isSignedIn) return res.status(401).json({ error: 'nincs bejelentkezve' });
  const me = await clerk.users.getUser(state.toAuth().userId);
  const email = me.primaryEmailAddress?.emailAddress || '';
  const name = [me.firstName, me.lastName].filter(Boolean).join(' ') || email;
  const role = me.publicMetadata?.role || '';

  const b = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
  const t = String(b.t || '').trim().slice(0, 200);
  if (!t) return res.status(400).json({ error: 'hiányzó tárgy' });
  const dontes = String(b.dontes || '').trim().slice(0, 2000);
  const kor = String(b.kor || '').trim().slice(0, 200);
  const hatar = /^\d{4}-\d{2}-\d{2}$/.test(b.hatar || '') ? b.hatar : '';
  const storyline = String(b.storyline || '').trim().slice(0, 100);
  const id = 'd-' + Date.now().toString(36);

  const token = process.env.GITHUB_TOKEN, repo = process.env.GITHUB_REPO || 'kresi-cloud/fvtp';
  if (!token) return res.status(500).json({ error: 'GITHUB_TOKEN hiányzik' });
  const payload = { id, t, dontes, kor, hatar, storyline, kero: name, email, role, date: new Date().toISOString().slice(0, 10) };
  const body = [
    `**Kérte:** ${name} (${email}${role ? ', ' + role : ''})`,
    `**Tárgy:** ${t}`, dontes ? `**Előkészítendő döntés:** ${dontes}` : '', kor ? `**Kör:** ${kor}` : '',
    hatar ? `**Kész legyen:** ${hatar}` : '', storyline ? `**Storyline:** ${storyline}` : '',
    '', '```json', JSON.stringify(payload, null, 2), '```',
  ].filter(l => l !== '').join('\n');
  const r = await fetch(`https://api.github.com/repos/${repo}/issues`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'Content-Type': 'application/json', 'User-Agent': 'fvtp' },
    body: JSON.stringify({ title: `Dosszié-kérés: ${t}`, body, labels: ['dosszie-keres'] }),
  });
  if (!r.ok) return res.status(502).json({ error: 'GitHub: ' + r.status + ' ' + (await r.text()).slice(0, 200) });
  const issue = await r.json();
  return res.json({ ok: true, id, issue: issue.number, url: issue.html_url });
}
