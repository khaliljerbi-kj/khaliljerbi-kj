import type { ChatMessage, ChatResponse, SearchCriteria } from "./types";

const BASE = "/api/backend";

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `Erreur ${res.status}`;
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function sendChat(messages: ChatMessage[], criteria: SearchCriteria | null) {
  const res = await fetch(`${BASE}/chat`, {
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
  const res = await fetch(`${BASE}/health`);
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
