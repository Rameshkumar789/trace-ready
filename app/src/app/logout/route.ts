import { NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";

// POST only: logout mutates state (clears the Supabase auth cookie), so it must NOT
// be a GET — Next.js prefetches GET links, which would silently sign the user out.
export async function POST(request: Request) {
  try {
    const supabase = await createServerSupabaseClient();
    await supabase.auth.signOut();
  } catch {
    // Already signed out / Supabase unavailable — fall through to the redirect.
  }
  return NextResponse.redirect(new URL("/", request.url), 303);
}
