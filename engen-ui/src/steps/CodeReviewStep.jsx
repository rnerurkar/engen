import { useState } from "react";
import { callOrchestrator } from "../api/orchestrator";
import Spinner from "../components/Spinner";

/**
 * CodeReviewStep — Step 4: show generated artifacts JSON, approve to GitHub.
 *
 * Props:
 *   codeData       – orchestrator result from phase2
 *   docData        – original doc data (for title)
 *   onApprove()    – called after code is approved
 *   onError(msg)   – called on failure
 */
export default function CodeReviewStep({ codeData, docData, onApprove, onError }) {
  const [loading, setLoading] = useState(false);
  const artifacts = codeData?.artifacts || {};

  const handleApprove = async () => {
    setLoading(true);
    try {
      await callOrchestrator("approve_code", {
        review_id: codeData.review_id,
        artifacts,
        title: docData.title,
      });
      onApprove();
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Spinner message="Publishing code to GitHub…" />;
  }

  return (
    <div className="step-code-review">
      <h2>💻 Review Artifacts</h2>

      <pre className="json-viewer">
        {JSON.stringify(artifacts, null, 2)}
      </pre>

      <button className="btn btn-primary" onClick={handleApprove}>
        Approve &amp; Publish to GitHub
      </button>
    </div>
  );
}
