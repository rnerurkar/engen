import { useEffect, useRef } from "react";
import Spinner from "../components/Spinner";
import { callOrchestrator } from "../api/orchestrator";

/**
 * CodeGenStep — Step 3: auto-triggered code generation.
 *
 * Props:
 *   docData             – full doc data (needs `full_doc` field)
 *   onComplete(codeData)– called with orchestrator result
 *   onError(msg)        – called on failure
 */
export default function CodeGenStep({ docData, onComplete, onError, workflowId }) {
  const triggered = useRef(false);

  useEffect(() => {
    if (triggered.current) return;
    triggered.current = true;

    (async () => {
      try {
        const result = await callOrchestrator("phase2_generate_code", {
          full_doc: docData.full_doc,
          workflow_id: workflowId || docData.workflow_id,
        });
        if (result) {
          onComplete(result);
        } else {
          onError("Orchestrator returned an empty result for code generation.");
        }
      } catch (err) {
        onError(err.message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="step-code-gen">
      <div className="info-box">
        Generating Implementation Artifacts (Terraform + Code)…
      </div>
      <Spinner message="This may take a minute…" />
    </div>
  );
}
