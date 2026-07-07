# Thursday Demo Runbook (2026-07-10, local machine)

Everything below assumes the repo at the latest `claude/fsma-204-traceability-validation-jd4ohn`.

## 0. One-time prep (Wednesday)

```bash
# Backend deps
cd backend
python -m pip install -e .

# Put the key in backend/.env (already gitignored):
#   ANTHROPIC_API_KEY=sk-ant-...

# Dress rehearsal: regenerates all AI perception via the LIVE model, verifies every
# expected Sea Eagle finding, and fails loudly on any fallback:
python scripts/demo/run_dress_rehearsal.py \
    --workbook /path/to/SeaEgle010125011025.xlsx \
    --regenerate-perception

# On GO: commit the refreshed cache so the live demo is cache-hit-only
git add ../data/llm-cache && git commit -m "Warm perception caches for demo" 
```

The rehearsal script's exit status is the go/no-go. A `NO-GO` means an AI path fell back or
an expected finding vanished — fix before Thursday, don't demo through it.

## 1. Start the stack (Thursday morning, before the call)

Terminal 1 — Python engine:

```bash
cd backend
uvicorn bellwether_backend.api.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — app (uses your existing `app/.env` with the Supabase keys and
`BELLWETHER_PYTHON_API_URL=http://127.0.0.1:8000`):

```bash
cd app
npm run dev
```

Sanity ping (expects `{"status":"ok"}`):

```bash
curl -s -H "x-bellwether-internal-token: $BELLWETHER_INTERNAL_API_TOKEN" \
    http://127.0.0.1:8000/internal/ping
```

## 2. Demo storyline (mirrors Jim's feedback, in his order)

1. **"Any export, no template"** — upload the **Sea Eagle workbook** (their own ENSESO4Food
   export!) through the operator dashboard. Talking point: nothing in the engine knows this
   template; the AI mapping layer profiled the sheets, mapped every column to the canonical
   FSMA schema, and the verifier pinned it to the real registry. Show the
   `workbookMappingPlan` artifact if asked.
2. **"The checks nobody runs"** — walk the findings, most severe first:
   - empty traceability plan + lot-assignment procedure (21 CFR 1.1315),
   - all 64 landing records missing harvest KDEs (systemic finding, one card not 64),
   - orphan shipped lots flagged as **"records predate the export window — request them"**
     (not a false "broken chain": the engine read the date out of their own lot-code format),
   - 40 transformation lots sharing one TLC across two products (recall ambiguity,
     needs-review with the multi-SKU carve-out),
   - the 372 lb vs 322 lb **mass-balance breach**, and the lot **shipped before its own
     lot date**,
   - the two shrimp SKUs **declared "General products" but classified on-FTL** — the
     "ham sandwich" tier, live on their data: definite / suspicious / definitely-not.
3. **"Point it at the trading partners"** — open the **partner scorecard** artifact: 29
   external partners, quality bands, per-partner missing KDEs (phone/email everywhere), the
   unknown-counterparty bucket. "Here's the list of people who don't give you the data."
4. **"Don't ship me what I can't accept"** — pre-receipt bounce, live:

   ```bash
   python - <<'EOF'
   import base64, json, os, urllib.request
   body = {
       "file_name": "sample-asn-856.edi",
       "content_base64": base64.b64encode(open("data/samples/inbound/sample-asn-856.edi","rb").read()).decode(),
   }
   req = urllib.request.Request(
       "http://127.0.0.1:8000/internal/inbound/validate",
       data=json.dumps(body).encode(),
       headers={"content-type": "application/json",
                "x-bellwether-internal-token": os.environ["BELLWETHER_INTERNAL_API_TOKEN"]})
   print(json.dumps(json.load(urllib.request.urlopen(req)), indent=1))
   EOF
   ```

   Line 1 (complete) **accepts**; line 2 (no lot code) **holds with the citation**; line 3's
   lot is unknown to the system. Same engine, pointed forward.
5. **"What comes through the door vs what's in the ERP"** — the audit run with the ASN
   attached shows `inbound_erp_mismatch`: the supplier sends phone/email on the ASN that the
   system drops, and one ASN lot was never recorded at all. (CLI:
   `python scripts/intelligence/build_phase10_customer_evidence.py --input-file <seaegle> --inbound-file ../data/samples/inbound/sample-asn-856.edi`)
6. **"You just scoped my FSMA project"** — close on the **scoping report** narrative +
   stats: products by FTL tier, partners by band, KDE coverage, window covered.
7. If Walmart comes up: the GS1 overlay findings carry `requirement_source =
   customer_requirement` — retailer rules are data cards (`bundled_rules/retailer-overlays/`),
   Kroger/Albertsons drop in with zero code.

## 3. Safety nets

- All AI results are **cache-hit** after the rehearsal — the demo works with the network
  down or the API slow; nothing recomputes.
- If the app upload path misbehaves, the CLI produces every artifact:
  `backend/scripts/intelligence/build_phase10_customer_evidence.py --input-file ... --output-dir /tmp/demo-artifacts`.
- The old demo workbook still produces its exact original findings (regression-checked) —
  safe to show first if you want the familiar flow.

## 4. Known limits (don't get caught claiming otherwise)

- BOL PDFs that are pure scans (no text layer) return "unreadable document — OCR needed",
  by design.
- The Supabase-persisted path (app upload) with ~15k-evidence workbooks uploads a ~40 MB
  obligation-mapping artifact; first run on the Sea Eagle file through the APP may take a
  couple of minutes. The CLI path is instant-feeling; rehearse the app path Wednesday and
  decide which to lead with.
- EDI: 856 is first-class; other transaction sets parse structurally but aren't mapped yet.
- Date parsing prefers US MM/DD/YYYY when a value is ambiguous.
