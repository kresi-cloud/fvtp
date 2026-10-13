// Meghívások kezelése – csak adminnak (publicMetadata.admin === true vagy ADMIN_EMAILS listán szereplő e-mail).
// GET    /api/invitations            → függő meghívók + bejelentkezett tagok listája
// POST   /api/invitations {email, role}   → meghívó küldése (role: dekan|dh_tud|dh_okt|intezet|hivatal, admin:boolean opcionális)
// DELETE /api/invitations?id=inv_... → meghívó visszavonása;  ?user=user_... → tag eltávolítása
import { createClerkClient } from '@clerk/backend';
export const config = { runtime: 'nodejs' };

const ROLES = ['dekan', 'dh_tud', 'dh_okt', 'intezet', 'hivatal'];

export default async function handler(req, res) {
  const clerk = createClerkClient({ secretKey: process.env.CLERK_SECRET_KEY, publishableKey: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY });
  const origin = `https://${req.headers.host}`;
  const webReq = new Request(origin + req.url, { method: req.method, headers: new Headers(req.headers) });
  const state = await clerk.authenticateRequest(webReq, { authorizedParties: [origin] });
  if (!state.isSignedIn) return res.status(401).json({ error: 'nincs bejelentkezve' });
  const { userId } = state.toAuth();
  const me = await clerk.users.getUser(userId);
  const myEmail = (me.primaryEmailAddress && me.primaryEmailAddress.emailAddress || '').toLowerCase();
  const adminList = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
  const isAdmin = me.publicMetadata?.admin === true || adminList.includes(myEmail);
  if (!isAdmin) return res.status(403).json({ error: 'nincs jogosultság' });

  try {
    if (req.method === 'GET') {
      const [inv, users] = await Promise.all([
        clerk.invitations.getInvitationList({ status: 'pending', limit: 100 }),
        clerk.users.getUserList({ limit: 200, orderBy: '-created_at' }),
      ]);
      return res.json({
        me: myEmail,
        invitations: (inv.data || inv).map(i => ({ id: i.id, email: i.emailAddress, role: i.publicMetadata?.role || '', admin: !!i.publicMetadata?.admin, created: i.createdAt })),
        users: (users.data || users).map(u => ({ id: u.id, email: u.primaryEmailAddress?.emailAddress || '', name: [u.firstName, u.lastName].filter(Boolean).join(' '),
                 role: u.publicMetadata?.role || '', admin: u.publicMetadata?.admin === true || adminList.includes((u.primaryEmailAddress?.emailAddress || '').toLowerCase()),
                 lastSignIn: u.lastSignInAt })),
      });
    }
    if (req.method === 'POST') {
      const b = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
      const email = String(b.email || '').trim().toLowerCase();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return res.status(400).json({ error: 'hibás e-mail' });
      const role = ROLES.includes(b.role) ? b.role : 'dekan';
      const i = await clerk.invitations.createInvitation({ emailAddress: email, publicMetadata: { role, admin: b.admin === true },
                                                           redirectUrl: origin + '/belepes.html', notify: true, ignoreExisting: true });
      return res.json({ ok: true, id: i.id });
    }
    if (req.method === 'DELETE') {
      const q = new URL(origin + req.url).searchParams;
      if (q.get('id')) { await clerk.invitations.revokeInvitation(q.get('id')); return res.json({ ok: true }); }
      if (q.get('user')) {
        if (q.get('user') === userId) return res.status(400).json({ error: 'saját fiók nem törölhető' });
        await clerk.users.deleteUser(q.get('user')); return res.json({ ok: true });
      }
      return res.status(400).json({ error: 'id vagy user szükséges' });
    }
    return res.status(405).end();
  } catch (e) {
    return res.status(500).json({ error: e.errors?.[0]?.longMessage || e.message || String(e) });
  }
}
