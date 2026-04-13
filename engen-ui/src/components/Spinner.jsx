/**
 * Spinner — inline loading indicator.
 *
 * Props:
 *   message – text displayed beside the spinner
 */

export default function Spinner({ message = "Loading..." }) {
  return (
    <div className="spinner-container">
      <div className="spinner" />
      <span className="spinner-text">{message}</span>
    </div>
  );
}
