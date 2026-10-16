import type { ChatMessage, ChatResponse, SearchCriteria } from "./types";

const BASE = "/api/backend";

// L'offre gratuite de Render met le backend en veille : la première requête peut
// échouer (502/503/504) le temps du réveil. On réessaie quelques fois.
const WAKING = new Set([502, 503, 504]);

async function fetchWaking(url: string, init?: RequestInit, attempts = 4): Promise<Response> {
  for (let i = 1; ; i++) {
    try {
      const res = await fetch(url, init);
      if (!WAKING.has(res.status) || i === attempts) return res;
    } catch (error) {
      if (i === attempts) throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
}

/** Réveille le backend dès l'ouverture de la page, sans bloquer l'interface. */
export function warmUpBackend() {
  fetchWaking(`${BASE}/health`).catch(() => {});
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `Erreur ${res.status}`;
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function sendChat(messages: ChatMessage[], criteria: SearchCriteria | null) {
  const res = await fetchWaking(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, criteria }),
  });
  return parse<ChatResponse>(res);
}

export async function transcribe(audio: Blob) {
  const form = new FormData();
  const ext = audio.type.includes("mp4") ? "mp4" : audio.type.includes("ogg") ? "ogg" : "webm";
  form.append("audio", audio, `dictee.${ext}`);
  const res = await fetch(`${BASE}/transcribe`, { method: "POST", body: form });
  return parse<{ text: string }>(res);
}

export async function getHealth() {
  const res = await fetchWaking(`${BASE}/health`);
  return parse<{ status: string; llm_provider: string; server_transcription: boolean }>(res);
}

export async function createAlert(email: string, query: string, criteria: SearchCriteria) {
  const res = await fetch(`${BASE}/alerts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, query, criteria }),
  });
  return parse<{ id: string; email: string; min_score: number }>(res);
}
