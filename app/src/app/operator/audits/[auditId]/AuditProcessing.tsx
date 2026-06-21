"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, TriangleAlert } from "lucide-react";
import { advanceAuditProcessing, retryAuditProcessing } from "./actions";

const POLL_INTERVAL_MS = 2500;
const MAX_POLLS = 48; // ~2 minutes before we surface a "taking longer" message

export function AuditProcessing({ auditId, fileName }: { auditId: string; fileName?: string }) {
  const router = useRouter();
  const [phase, setPhase] = useState<"processing" | "failed">("processing");
  const [message, setMessage] = useState<string | undefined>();
  const pollsRef = useRef(0);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;
    let timer: ReturnType<typeof setTimeout>;

    async function tick() {
      if (stoppedRef.current) return;
      pollsRef.current += 1;
      const result = await advanceAuditProcessing(auditId).catch(() => ({ state: "processing" as const }));
      if (stoppedRef.current) return;
      if (result.state === "ready") {
        stoppedRef.current = true;
        router.refresh();
        return;
      }
      if (result.state === "failed") {
        stoppedRef.current = true;
        setMessage(result.message);
        setPhase("failed");
        return;
      }
      if (pollsRef.current >= MAX_POLLS) {
        stoppedRef.current = true;
        setMessage("This is taking longer than expected. You can keep waiting or try again.");
        setPhase("failed");
        return;
      }
      timer = setTimeout(tick, POLL_INTERVAL_MS);
    }

    void tick();
    return () => {
      stoppedRef.current = true;
      clearTimeout(timer);
    };
  }, [auditId, router]);

  async function handleRetry() {
    setPhase("processing");
    setMessage(undefined);
    pollsRef.current = 0;
    const result = await retryAuditProcessing(auditId).catch(() => ({ state: "processing" as const }));
    if (result.state === "ready") {
      router.refresh();
    } else if (result.state === "failed") {
      setMessage(result.message);
      setPhase("failed");
    }
    // "processing" → the effect's poll loop is still running and will continue.
  }

  return (
    <div className="audit-processing" role="status" aria-live="polite">
      {phase === "processing" ? (
        <>
          <Loader2 className="audit-processing-spinner" size={40} aria-hidden />
          <h2>Running your FSMA 204 audit…</h2>
          <p>{fileName ? `Checking ${fileName} against the approved rules.` : "Checking your workbook against the approved rules."} This usually takes a few seconds.</p>
        </>
      ) : (
        <>
          <TriangleAlert className="audit-processing-warn" size={40} aria-hidden />
          <h2>We couldn’t finish this audit automatically</h2>
          <p>{message ?? "Something interrupted processing."}</p>
          <button type="button" className="button" onClick={handleRetry}>
            Try again
          </button>
        </>
      )}
    </div>
  );
}
