import { useState } from "react";

/**
 * Collapsible — an expander / accordion panel.
 *
 * Props:
 *   title       – header text
 *   defaultOpen – whether it starts expanded (default true)
 *   children    – content
 */

export default function Collapsible({ title, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`collapsible ${open ? "open" : ""}`}>
      <button
        className="collapsible-header"
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="collapsible-arrow">{open ? "▼" : "▶"}</span>
        <span>{title}</span>
      </button>
      {open && <div className="collapsible-body">{children}</div>}
    </div>
  );
}
