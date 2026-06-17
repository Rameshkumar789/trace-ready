import { cookies } from "next/headers";
import { parseSessionCookie, TRACEREADY_SESSION_COOKIE } from "./session-cookie";
import type { TraceReadySession } from "./session-cookie";

export async function getTraceReadySession(): Promise<TraceReadySession | undefined> {
  const cookieStore = await cookies();
  return parseSessionCookie(cookieStore.get(TRACEREADY_SESSION_COOKIE)?.value);
}

export const getPilotSession = getTraceReadySession;
