import { NextResponse } from "next/server";
import { TRACEREADY_SESSION_COOKIE } from "@/lib/auth/session-cookie";

export function GET(request: Request) {
  const response = NextResponse.redirect(new URL("/", request.url));
  response.cookies.set(TRACEREADY_SESSION_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0
  });
  return response;
}
