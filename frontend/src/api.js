const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    const e = new Error("Cannot reach the server. Is it running?");
    e.status = 0;
    throw e;
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail)
      ? "Please check your input."
      : body.detail || "Something went wrong.";
    const e = new Error(detail);
    e.status = res.status;
    throw e;
  }
  return res.json();
}

const post = (path, data) =>
  request(path, { method: "POST", body: data ? JSON.stringify(data) : undefined });

export const api = {
  listTopics: () => request("/topics"),
  createTopic: (title, notes) => post("/topics", { title, notes: notes || null }),
  createSession: (topicId) => post("/sessions", { topic_id: topicId }),
  sendTurn: (sessionId, text) => post(`/sessions/${sessionId}/turns`, { text }),
  finish: (sessionId) => post(`/sessions/${sessionId}/finish`),
  getReport: (sessionId) => request(`/sessions/${sessionId}/report`),
};