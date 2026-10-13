// Vercel Edge Middleware – Clerk-munkamenet nélkül minden oldal a /belepes.html-re irányít.
// Beállítás: CLERK_SECRET_KEY és NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY környezeti változók a Vercelen.
import { createClerkClient } from '@clerk/backend';

export const config = { matcher: ['/((?!belepes\\.html|theme\\.css|favicon\\.svg|img/|_vercel).*)'] };

export default async function middleware(req) {
  const secretKey = process.env.CLERK_SECRET_KEY;
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!secretKey || !publishableKey) return new Response('Clerk kulcsok hiányoznak (CLERK_SECRET_KEY, NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY).', { status: 500 });
  const clerk = createClerkClient({ secretKey, publishableKey });
  const url = new URL(req.url);
  const state = await clerk.authenticateRequest(req, { authorizedParties: [url.origin] });
  if (state.status === 'handshake') {               // Clerk a session-süti frissítését kéri (átirányítás)
    return new Response(null, { status: 307, headers: state.headers });
  }
  if (state.isSignedIn) return;                      // tovább a statikus oldalra
  const to = new URL('/belepes.html', url);
  if (url.pathname !== '/') to.searchParams.set('next', url.pathname + url.search);
  return Response.redirect(to, 302);
}
