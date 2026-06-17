import { NextResponse, type NextRequest } from "next/server";
import { canAccessPath, loginPathForTarget, parseSessionCookie, TRACEREADY_SESSION_COOKIE } from "@/lib/auth/session-cookie";

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

  const session = await parseSessionCookie(request.cookies.get(TRACEREADY_SESSION_COOKIE)?.value);

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
