import { useEffect, useRef, useState } from "react";
import { callOrchestrator } from "../api/orchestrator";
import Spinner from "../components/Spinner";

/**
 * PublishStep — Step 5: poll orchestrator for publishing status.
 *
 * Props:
 *   docData   – contains review_id for docs
 *   codeData  – contains review_id for code
 */
export default function PublishStep({ docData, codeData }) {
  const [docStatus, setDocStatus] = useState(null);
  const [codeStatus, setCodeStatus] = useState(null);
  const [polling, setPolling] = useState(true);
  const attemptRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      const rids = [docData.review_id, codeData.review_id];

      while (!cancelled && attemptRef.current < 60) {
        attemptRef.current += 1;
        try {
          const statusMap = await callOrchestrator("get_publish_status", {
            review_ids: rids,
          });

          if (!cancelled && statusMap) {
            setDocStatus(statusMap[rids[0]] || {});
            setCodeStatus(statusMap[rids[1]] || {});

            // Auto-stop when both are DONE / PUBLISHED
            const ds = statusMap[rids[0]]?.doc_status || "";
            const cs = statusMap[rids[1]]?.code_status || "";
            if (
              ["DONE", "PUBLISHED", "COMPLETE"].includes(ds.toUpperCase()) &&
              ["DONE", "PUBLISHED", "COMPLETE"].includes(cs.toUpperCase())
            ) {
              setPolling(false);
              return;
            }
          }
        } catch {
          // swallow polling errors and retry
        }
        // wait 3 seconds
        await new Promise((r) => setTimeout(r, 3000));
      }
      if (!cancelled) setPolling(false);
    };

    poll();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="step-publish">
      <h2>🚀 Publishing Status</h2>

      {polling && <Spinner message="Polling for publish status…" />}

      <div className="status-card">
        <p>
          <strong>SharePoint Docs:</strong>{" "}
          <code>{docStatus?.doc_status || "UNKNOWN"}</code>
        </p>
        {docStatus?.doc_url && (
          <a
            className="success-link"
            href={docStatus.doc_url}
            target="_blank"
            rel="noreferrer"
          >
            Open in SharePoint ↗
          </a>
        )}
      </div>

      <div className="status-card">
        <p>
          <strong>GitHub Code:</strong>{" "}
          <code>{codeStatus?.code_status || "UNKNOWN"}</code>
        </p>
        {codeStatus?.code_url && (
          <a
            className="success-link"
            href={codeStatus.code_url}
            target="_blank"
            rel="noreferrer"
          >
            Open in GitHub ↗
          </a>
        )}
      </div>
    </div>
  );
}
