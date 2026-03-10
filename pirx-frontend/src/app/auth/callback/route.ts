import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";

  if (code) {
    const supabase = await createClient();
    const { error, data } = await supabase.auth.exchangeCodeForSession(code);
    if (!error && data.session) {
      try {
        const res = await fetch(`${API_URL}/account/onboarding-status`, {
          headers: {
            Authorization: `Bearer ${data.session.access_token}`,
            "Content-Type": "application/json",
          },
        });
        if (res.ok) {
          const { onboarding_completed } = await res.json();
          if (!onboarding_completed) {
            return NextResponse.redirect(`${origin}/onboarding/1`);
          }
        }
      } catch {
        // If the check fails, fall through to dashboard
      }
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_callback_error`);
}
