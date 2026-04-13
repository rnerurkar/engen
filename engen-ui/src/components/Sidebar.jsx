/**
 * Sidebar — "Process Controls" panel with Reset button.
 *
 * Props:
 *   onReset  – callback to clear all workflow state
 */

export default function Sidebar({ onReset }) {
  return (
    <aside className="sidebar">
      <h2>Process Controls</h2>
      <button className="btn btn-danger" onClick={onReset}>
        Reset Workflow
      </button>
    </aside>
  );
}
