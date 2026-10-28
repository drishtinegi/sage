const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

let memoryId = null;
function learnerId() {
  try {
    let id = localStorage.getItem("eb_learner");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("eb_learner", id);
    }
    return id;
  } catch {
    memoryId = memoryId || crypto.randomUUID();
    return memoryId;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API}${path}`, {
      headers: { "Content-Type": "application/json", "X-Learner": learnerId() },
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

const inflight = new Map();
function once(key, fn) {
  if (!inflight.has(key)) {
    inflight.set(key, fn().finally(() => setTimeout(() => inflight.delete(key), 1000)));
  }
  return inflight.get(key);
}

export const api = {
  listTopics: () => request("/topics"),
  createTopic: (title, notes) => post("/topics", { title, notes: notes || null }),
  createSession: (topicId) => post("/sessions", { topic_id: topicId }),
  sendTurn: (sessionId, text) => post(`/sessions/${sessionId}/turns`, { text }),
  finish: (sessionId) => post(`/sessions/${sessionId}/finish`),
  getReport: (sessionId) => request(`/sessions/${sessionId}/report`),
  getSession: (sessionId) => request(`/sessions/${sessionId}`),
  getPlan: (sessionId) => once(`plan-${sessionId}`, () => request(`/sessions/${sessionId}/plan`)),
  history: () => request("/history"),
};