/**
 * Orchestrator API Client
 * -------------------------------------------------------
 * Mirrors the Streamlit `call_orchestrator(task, payload)` helper.
 *
 * During local dev the Vite dev-server proxies `/api` → `http://localhost:9000`
 * (see vite.config.js).  In production `VITE_API_BASE_URL` should point to the
 * deployed Orchestrator endpoint.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

/**
 * POST to the Orchestrator Agent's /invoke endpoint.
 *
 * @param {string} task   — one of phase1_generate_docs | approve_docs |
 *                           phase2_generate_code | approve_code |
 *                           get_publish_status
 * @param {Object} payload — task-specific data
 * @returns {Promise<any>}  The `result` field from the Orchestrator response.
 * @throws {Error}          On non-200 status or network failure.
 */
export async function callOrchestrator(task, payload) {
  const url = `${BASE_URL}/invoke`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, payload }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Orchestrator error (${response.status}): ${text}`);
  }

  const data = await response.json();
  return data.result;
}

/**
 * Convert a File object to a base64-encoded string (data portion only).
 *
 * @param {File} file
 * @returns {Promise<string>}
 */
export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      // strip the data:…;base64, prefix
      const base64 = reader.result.split(",")[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
