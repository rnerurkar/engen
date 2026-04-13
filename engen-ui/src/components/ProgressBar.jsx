/**
 * ProgressBar — horizontal stepper that mirrors the Streamlit progress bar.
 *
 * Props:
 *   currentStep  – one of INPUT | DOC_REVIEW | CODE_GEN | CODE_REVIEW | PUBLISH
 */

const LABELS = [
  "Upload",
  "Generate Docs",
  "Approve Docs",
  "Generate Code",
  "Approve Code",
  "Publishing",
];

const STEP_INDEX = {
  INPUT: 0,
  DOC_REVIEW: 2,
  CODE_GEN: 3,
  CODE_REVIEW: 4,
  PUBLISH: 5,
};

export default function ProgressBar({ currentStep }) {
  const idx = STEP_INDEX[currentStep] ?? 0;
  const pct = (idx / 5) * 100;

  return (
    <div className="progress-container">
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="progress-labels">
        {LABELS.map((label, i) => (
          <span
            key={label}
            className={`progress-label ${i <= idx ? "active" : ""}`}
          >
            {label}
          </span>
        ))}
      </div>
      <p className="progress-caption">Current Step: {currentStep}</p>
    </div>
  );
}
