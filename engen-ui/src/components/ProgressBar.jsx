/**
 * ProgressBar — chevron-style stepper.
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

  return (
    <div className="chevron-container">
      {LABELS.map((label, i) => {
        let state = "inactive";
        if (i === idx) state = "active";
        else if (i < idx) state = "completed";

        return (
          <div key={label} className={`chevron chevron--${state}`}>
            <span className="chevron-number">{i + 1}</span>
            <span className="chevron-label">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
