import { NextResponse, type NextRequest } from "next/server";
import { canAccessPath, decodeSessionCookieUnverified, loginPathForTarget, TRACEREADY_SESSION_COOKIE } from "@/lib/auth/session-cookie";

export async function proxy(request: NextRequest) {
  const protectedPath =
    request.nextUrl.pathname.startsWith("/operator") ||
    request.nextUrl.pathname.startsWith("/reviewer") ||
    request.nextUrl.pathname.startsWith("/admin") ||
    request.nextUrl.pathname.startsWith("/upload") ||
    request.nextUrl.pathname.startsWith("/audits");

  if (!protectedPath) {
    return NextResponse.next();
  }

  // Optimistic, secret-free routing check (Edge runtime). The HMAC signature is verified
  // server-side in getPilotSession when a protected page actually renders.
  const rawCookie = request.cookies.get(TRACEREADY_SESSION_COOKIE)?.value;
  const session = decodeSessionCookieUnverified(rawCookie);

  if (canAccessPath(session, request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  if (session) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    url.searchParams.set("auth", "forbidden");
    return NextResponse.redirect(url);
  }

  const url = request.nextUrl.clone();
  url.pathname = loginPathForTarget(request.nextUrl.pathname);
  url.searchParams.set("auth", "required");
  url.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/operator/:path*", "/operator", "/reviewer/:path*", "/reviewer", "/admin/:path*", "/upload", "/audits/:path*"]
};
