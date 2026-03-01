import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
 
const PUBLIC_PATHS = ['/auth', '/setup', '/api/auth', '/api/setup'];
const GUEST_PATHS = ['/auth/login', '/auth/register'];

export async function middleware(request: NextRequest) {
  // Bypass middleware for API routes and public paths
  const pathname = request.nextUrl.pathname;
  if (pathname.startsWith('/api') || PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  try {
    // Check setup status
    const setupStatus = await (await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/setup/status`
    )).json();

    if (!setupStatus.completed && !pathname.startsWith('/setup')) {
      const url = request.nextUrl.clone();
      url.pathname = '/setup';
      return NextResponse.redirect(url);
    }

    // If setup is complete but user not logged in, redirect to login
    if (setupStatus.completed && GUEST_PATHS.includes(pathname)) {
      const url = request.nextUrl.clone();
      url.pathname = '/auth/login';
      return NextResponse.redirect(url);
    }

    return NextResponse.next();
  } catch (error) {
    console.error('Middleware error:', error);
    return NextResponse.next();
  }
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
