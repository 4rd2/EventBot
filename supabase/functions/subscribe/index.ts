// Supabase Edge Function: POST /subscribe
//
// Adds a phone subscriber to the `subscribers` table. This is the single
// signup API — any future frontend (web form, Discord bot, etc.) calls this.
// Runs with the service-role key Supabase injects, so the table needs no
// anon insert policy and phone numbers are never readable publicly.
//
// Deploy:  supabase functions deploy subscribe --no-verify-jwt
// Test:    curl -X POST https://<project>.supabase.co/functions/v1/subscribe \
//            -H "Content-Type: application/json" \
//            -d '{"phone_number": "+16145551234", "name": "Test"}'

import { createClient } from "npm:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

// Normalize to E.164; bare 10-digit numbers are assumed US (+1)
function normalizePhone(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  let s = raw.replace(/[\s\-().]/g, "");
  if (/^\d{10}$/.test(s)) s = "+1" + s;
  else if (/^1\d{10}$/.test(s)) s = "+" + s;
  return /^\+[1-9]\d{6,14}$/.test(s) ? s : null;
}

function toTextArray(v: unknown): string[] {
  return Array.isArray(v) ? v.map(String) : [];
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "method not allowed" }, 405);

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json({ error: "invalid JSON body" }, 400);
  }

  const phone = normalizePhone(body.phone_number);
  if (!phone) {
    return json({ error: "invalid phone_number — use E.164 format like +16145551234" }, 400);
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  const { data: existing, error: lookupError } = await supabase
    .from("subscribers")
    .select("id, active")
    .eq("phone_number", phone)
    .maybeSingle();
  if (lookupError) return json({ error: lookupError.message }, 500);

  if (existing) {
    if (!existing.active) {
      const { error } = await supabase
        .from("subscribers")
        .update({ active: true })
        .eq("id", existing.id);
      if (error) return json({ error: error.message }, 500);
      return json({ status: "resubscribed", id: existing.id });
    }
    return json({ status: "already_subscribed", id: existing.id });
  }

  const { data, error } = await supabase
    .from("subscribers")
    .insert({
      phone_number: phone,
      name: typeof body.name === "string" ? body.name : null,
      companies: toTextArray(body.companies),
      categories: toTextArray(body.categories),
    })
    .select("id")
    .single();
  if (error) return json({ error: error.message }, 500);

  return json({ status: "subscribed", id: data.id }, 201);
});
