import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/auth', '/setup', '/_next', '/favicon.ico'];

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Bypass for static assets and already-public paths
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Use internal backend URL for server-side fetch (not the browser-facing /api)
  const internalApi = process.env.INTERNAL_API_URL || 'http://backend:8000';

  try {
    const res = await fetch(`${internalApi}/api/setup/status`, {
      next: { revalidate: 30 },
    });
    if (res.ok) {
      const status = await res.json() as { completed: boolean };
      if (!status.completed && !pathname.startsWith('/setup')) {
        const url = request.nextUrl.clone();
        url.pathname = '/setup';
        return NextResponse.redirect(url);
      }
    }
  } catch {
    // Backend not reachable (e.g. cold start) — allow through
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api/).*)'],
};
