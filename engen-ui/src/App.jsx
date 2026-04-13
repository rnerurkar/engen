import { useState, useEffect, useCallback } from "react";
import ProgressBar from "./components/ProgressBar";
import Sidebar from "./components/Sidebar";
import InputStep from "./steps/InputStep";
import DocReviewStep from "./steps/DocReviewStep";
import CodeGenStep from "./steps/CodeGenStep";
import CodeReviewStep from "./steps/CodeReviewStep";
import PublishStep from "./steps/PublishStep";
import Spinner from "./components/Spinner";
import { callOrchestrator } from "./api/orchestrator";

/**
 * App — root component implementing the 5-step wizard state machine:
 *   INPUT → DOC_REVIEW → CODE_GEN → CODE_REVIEW → PUBLISH
 *
 * On mount the app checks localStorage for a saved workflow_id and
 * calls resume_workflow to restore state from CloudSQL.
 */
export default function App() {
  const [step, setStep] = useState("INPUT");
  const [docData, setDocData] = useState(null);
  const [codeData, setCodeData] = useState(null);
  const [error, setError] = useState(null);
  const [workflowId, setWorkflowId] = useState(null);
  const [resuming, setResuming] = useState(true); // true on first mount

  // ─── On mount: attempt to resume a previous workflow ─────
  useEffect(() => {
    const savedId = localStorage.getItem("engen_workflow_id");
    if (!savedId) {
      setResuming(false);
      return;
    }

    (async () => {
      try {
        const res = await callOrchestrator("resume_workflow", {
          workflow_id: savedId,
        });
        if (res?.found) {
          setWorkflowId(res.workflow_id);
          setStep(res.step || "INPUT");
          if (res.doc_data) setDocData(res.doc_data);
          if (res.code_data) setCodeData(res.code_data);
        } else {
          localStorage.removeItem("engen_workflow_id");
        }
      } catch {
        localStorage.removeItem("engen_workflow_id");
      } finally {
        setResuming(false);
      }
    })();
  }, []);

  // ─── Persist workflowId to localStorage ──────────────────
  useEffect(() => {
    if (workflowId) {
      localStorage.setItem("engen_workflow_id", workflowId);
    }
  }, [workflowId]);

  // ─── Reset ───────────────────────────────────────────────
  const handleReset = useCallback(() => {
    setStep("INPUT");
    setDocData(null);
    setCodeData(null);
    setError(null);
    setWorkflowId(null);
    localStorage.removeItem("engen_workflow_id");
  }, []);

  // ─── Step transitions ────────────────────────────────────
  const handleDocGenComplete = useCallback((data) => {
    setDocData(data);
    if (data?.workflow_id) setWorkflowId(data.workflow_id);
    setStep("DOC_REVIEW");
    setError(null);
  }, []);

  const handleDocsApproved = useCallback(() => {
    setStep("CODE_GEN");
    setError(null);
  }, []);

  const handleCodeGenComplete = useCallback((data) => {
    setCodeData(data);
    setStep("CODE_REVIEW");
    setError(null);
  }, []);

  const handleCodeApproved = useCallback(() => {
    setStep("PUBLISH");
    setError(null);
  }, []);

  const handleError = useCallback((msg) => {
    setError(msg);
  }, []);

  // ─── Loading screen while checking for saved workflow ────
  if (resuming) {
    return (
      <div className="app-layout">
        <main className="main-content" style={{ textAlign: "center", paddingTop: "6rem" }}>
          <Spinner message="Checking for in-progress workflows…" />
        </main>
      </div>
    );
  }

  // ─── Step renderer ───────────────────────────────────────
  const renderStep = () => {
    switch (step) {
      case "INPUT":
        return (
          <InputStep
            onComplete={handleDocGenComplete}
            onError={handleError}
            workflowId={workflowId}
          />
        );
      case "DOC_REVIEW":
        return (
          <DocReviewStep
            docData={docData}
            onApprove={handleDocsApproved}
            onError={handleError}
            workflowId={workflowId}
          />
        );
      case "CODE_GEN":
        return (
          <CodeGenStep
            docData={docData}
            onComplete={handleCodeGenComplete}
            onError={handleError}
            workflowId={workflowId}
          />
        );
      case "CODE_REVIEW":
        return (
          <CodeReviewStep
            codeData={codeData}
            docData={docData}
            onApprove={handleCodeApproved}
            onError={handleError}
            workflowId={workflowId}
          />
        );
      case "PUBLISH":
        return (
          <PublishStep
            docData={docData}
            codeData={codeData}
            workflowId={workflowId}
            onComplete={() => localStorage.removeItem("engen_workflow_id")}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="app-layout">
      <Sidebar onReset={handleReset} />

      <main className="main-content">
        <h1>🏗️ Pattern Factory: One-Shot Pattern Generator</h1>
        <ProgressBar currentStep={step} />

        {error && (
          <div className="error-box">
            <strong>Error:</strong> {error}
            <button className="btn-dismiss" onClick={() => setError(null)}>
              ✕
            </button>
          </div>
        )}

        {renderStep()}
      </main>
    </div>
  );
}
