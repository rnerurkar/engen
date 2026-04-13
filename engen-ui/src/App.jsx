import { useState, useCallback } from "react";
import ProgressBar from "./components/ProgressBar";
import Sidebar from "./components/Sidebar";
import InputStep from "./steps/InputStep";
import DocReviewStep from "./steps/DocReviewStep";
import CodeGenStep from "./steps/CodeGenStep";
import CodeReviewStep from "./steps/CodeReviewStep";
import PublishStep from "./steps/PublishStep";

/**
 * App — root component implementing the 5-step wizard state machine:
 *   INPUT → DOC_REVIEW → CODE_GEN → CODE_REVIEW → PUBLISH
 */
export default function App() {
  const [step, setStep] = useState("INPUT");
  const [docData, setDocData] = useState(null);
  const [codeData, setCodeData] = useState(null);
  const [error, setError] = useState(null);

  // ─── Reset ───────────────────────────────────────────────
  const handleReset = useCallback(() => {
    setStep("INPUT");
    setDocData(null);
    setCodeData(null);
    setError(null);
  }, []);

  // ─── Step transitions ────────────────────────────────────
  const handleDocGenComplete = useCallback((data) => {
    setDocData(data);
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

  // ─── Step renderer ───────────────────────────────────────
  const renderStep = () => {
    switch (step) {
      case "INPUT":
        return (
          <InputStep onComplete={handleDocGenComplete} onError={handleError} />
        );
      case "DOC_REVIEW":
        return (
          <DocReviewStep
            docData={docData}
            onApprove={handleDocsApproved}
            onError={handleError}
          />
        );
      case "CODE_GEN":
        return (
          <CodeGenStep
            docData={docData}
            onComplete={handleCodeGenComplete}
            onError={handleError}
          />
        );
      case "CODE_REVIEW":
        return (
          <CodeReviewStep
            codeData={codeData}
            docData={docData}
            onApprove={handleCodeApproved}
            onError={handleError}
          />
        );
      case "PUBLISH":
        return <PublishStep docData={docData} codeData={codeData} />;
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
