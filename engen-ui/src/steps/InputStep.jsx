import { useState, useRef } from "react";
import { callOrchestrator, fileToBase64 } from "../api/orchestrator";
import Spinner from "../components/Spinner";

/**
 * InputStep — Step 1: pattern name + diagram upload → phase1_generate_docs.
 *
 * Props:
 *   onComplete(docData) – called with the orchestrator result
 *   onError(msg)        – called on failure
 */
export default function InputStep({ onComplete, onError, workflowId }) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef();

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const handleSubmit = async () => {
    if (!title || !file) return;
    setLoading(true);
    try {
      const imgBase64 = await fileToBase64(file);
      const result = await callOrchestrator("phase1_generate_docs", {
        title,
        image_base64: imgBase64,
        workflow_id: workflowId || undefined,
        user_id: localStorage.getItem("engen_user_id") || "anonymous",
      });
      if (result) {
        result.title = result.title || title;
        onComplete(result);
      } else {
        onError("Orchestrator returned an empty result.");
      }
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Spinner message="Analyzing diagram and generating documentation…" />;
  }

  return (
    <div className="step-input">
      <div className="two-col">
        {/* Left column */}
        <div className="col">
          <label htmlFor="patternName">Pattern Name</label>
          <input
            id="patternName"
            type="text"
            placeholder="e.g. Rate Limiting Service"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          <label htmlFor="diagramUpload">Upload Diagram</label>
          <input
            id="diagramUpload"
            ref={inputRef}
            type="file"
            accept=".png,.jpg,.jpeg"
            onChange={handleFileChange}
          />

          {preview && (
            <img
              src={preview}
              alt="Diagram preview"
              className="img-preview"
            />
          )}
        </div>

        {/* Right column */}
        <div className="col">
          <div className="info-box">Ready to begin analysis.</div>
          <button
            className="btn btn-primary"
            disabled={!title || !file}
            onClick={handleSubmit}
          >
            Start Analysis &amp; Doc Gen
          </button>
        </div>
      </div>
    </div>
  );
}
