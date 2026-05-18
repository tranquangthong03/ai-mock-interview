// -----------------------------------------------------------------------
// Lightweight localStorage helpers for persisting IDs across refreshes
// -----------------------------------------------------------------------

const KEYS = {
  cvDocumentId: "mock-interviewer-cv-id",
  jdDocumentId: "mock-interviewer-jd-id",
  sessionId: "mock-interviewer-session-id",
} as const;

function get(key: string): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(key);
}

function set(key: string, value: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(key, value);
}

function remove(key: string) {
  if (typeof window === "undefined") return;
  localStorage.removeItem(key);
}

export function getCvDocumentId(): number | null {
  const v = get(KEYS.cvDocumentId);
  return v ? Number(v) : null;
}
export function setCvDocumentId(id: number) {
  set(KEYS.cvDocumentId, String(id));
}

export function getJdDocumentId(): number | null {
  const v = get(KEYS.jdDocumentId);
  return v ? Number(v) : null;
}
export function setJdDocumentId(id: number) {
  set(KEYS.jdDocumentId, String(id));
}

export function getSessionId(): number | null {
  const v = get(KEYS.sessionId);
  return v ? Number(v) : null;
}
export function setSessionId(id: number) {
  set(KEYS.sessionId, String(id));
}

export function clearAll() {
  remove(KEYS.cvDocumentId);
  remove(KEYS.jdDocumentId);
  remove(KEYS.sessionId);
}
