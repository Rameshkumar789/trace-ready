import { NextResponse } from "next/server";
import { TRACEREADY_SESSION_COOKIE } from "@/lib/auth/session-cookie";

// POST only: logout mutates state (clears the session cookie), so it must NOT be a GET — Next.js
// prefetches GET links, which would silently log the user out the instant the dashboard renders.
export function POST(request: Request) {
  const response = NextResponse.redirect(new URL("/", request.url), 303);
  response.cookies.set(TRACEREADY_SESSION_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0
  });
  return response;
}
