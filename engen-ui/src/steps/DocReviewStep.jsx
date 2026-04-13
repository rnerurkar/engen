import { useState } from "react";
import ReactMarkdown from "react-markdown";
import Collapsible from "../components/Collapsible";
import Spinner from "../components/Spinner";
import { callOrchestrator } from "../api/orchestrator";

/**
 * DocReviewStep — Step 2: display generated docs, allow approval.
 *
 * Props:
 *   docData           – orchestrator result from phase1
 *   onApprove()       – called after docs are approved
 *   onError(msg)      – called on failure
 */
export default function DocReviewStep({ docData, onApprove, onError }) {
  const [loading, setLoading] = useState(false);

  const sections = docData?.sections || {};
  const hadr = sections["HA/DR"] || "";

  const handleApprove = async () => {
    setLoading(true);
    try {
      await callOrchestrator("approve_docs", {
        review_id: docData.review_id,
        title: docData.title,
        sections: docData.sections,
        donor_context: docData.donor_context,
      });
      onApprove();
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Spinner message="Publishing docs to SharePoint…" />;
  }

  return (
    <div className="step-doc-review">
      <h2>📝 Review Documentation</h2>

      {/* Main pattern sections (excluding HA/DR) */}
      <Collapsible title="Pattern Documentation" defaultOpen>
        {Object.entries(sections)
          .filter(([key]) => key !== "HA/DR")
          .map(([key, val]) => (
            <div key={key} className="doc-section">
              <ReactMarkdown>{`# ${key}\n${val}`}</ReactMarkdown>
            </div>
          ))}
      </Collapsible>

      {/* HA/DR section */}
      {hadr ? (
        <Collapsible title="🛡️ HA/DR Documentation" defaultOpen>
          <ReactMarkdown>{hadr}</ReactMarkdown>
        </Collapsible>
      ) : (
        <div className="info-box">
          No HA/DR sections were generated for this pattern.
        </div>
      )}

      <div className="two-col" style={{ marginTop: "1rem" }}>
        <div className="col">
          <button className="btn btn-primary" onClick={handleApprove}>
            Approve &amp; Publish to SharePoint
          </button>
        </div>
        <div className="col">
          <div className="warning-box">
            Editing function not implemented in this demo.
          </div>
        </div>
      </div>
    </div>
  );
}
