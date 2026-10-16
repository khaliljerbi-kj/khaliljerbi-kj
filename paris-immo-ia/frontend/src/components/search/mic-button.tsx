"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Mic, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getHealth, transcribe } from "@/lib/api";
import { cn } from "@/lib/utils";

type Mode = "server" | "browser" | "none";
type State = "idle" | "recording" | "transcribing";

// Web Speech API : non typée dans lib.dom, préfixée sous Chrome/Safari.
type Recognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  start(): void;
  stop(): void;
};

function speechRecognitionCtor(): (new () => Recognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => Recognition) | null;
}

/**
 * Dictée vocale : enregistre l'audio et l'envoie à /api/transcribe (Whisper) si le backend
 * le permet, sinon bascule sur la Web Speech API du navigateur.
 */
export function MicButton({
  onStart,
  onTranscript,
  onError,
  disabled,
}: {
  onStart: () => void;
  /** Appelé avec le texte complet de la dictée en cours (résultats intermédiaires puis final). */
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
  disabled?: boolean;
}) {
  const [mode, setMode] = useState<Mode>("none");
  const [state, setState] = useState<State>("idle");
  const recorder = useRef<MediaRecorder | null>(null);
  const recognition = useRef<Recognition | null>(null);

  useEffect(() => {
    const canRecord = typeof window !== "undefined" && "MediaRecorder" in window && !!navigator.mediaDevices;
    const browserMode: Mode = speechRecognitionCtor() ? "browser" : "none";
    getHealth()
      .then((h) => setMode(h.server_transcription && canRecord ? "server" : browserMode))
      .catch(() => setMode(browserMode));
  }, []);

  async function startServer() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const rec = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      setState("transcribing");
      try {
        const { text } = await transcribe(new Blob(chunks, { type: rec.mimeType }));
        onTranscript(text);
      } catch (e) {
        onError(e instanceof Error ? e.message : "Transcription impossible");
      } finally {
        setState("idle");
      }
    };
    rec.start();
    recorder.current = rec;
    setState("recording");
  }

  function startBrowser() {
    const Ctor = speechRecognitionCtor();
    if (!Ctor) return;
    const rec = new Ctor();
    rec.lang = "fr-FR";
    rec.interimResults = true;
    rec.continuous = true;
    rec.onresult = (e) =>
      onTranscript(
        Array.from(e.results)
          .map((r) => r[0].transcript.trim())
          .join(" "),
      );
    rec.onerror = (e) => onError(`Dictée interrompue (${e.error})`);
    rec.onend = () => setState("idle");
    rec.start();
    recognition.current = rec;
    setState("recording");
  }

  async function toggle() {
    if (state === "recording") {
      recorder.current?.stop();
      recognition.current?.stop();
      return;
    }
    onStart();
    try {
      if (mode === "server") await startServer();
      else if (mode === "browser") startBrowser();
    } catch {
      onError("Accès au micro refusé.");
      setState("idle");
    }
  }

  const unavailable = mode === "none";
  return (
    <Button
      type="button"
      size="icon"
      variant={state === "recording" ? "destructive" : "outline"}
      onClick={toggle}
      disabled={disabled || unavailable || state === "transcribing"}
      aria-label={state === "recording" ? "Arrêter la dictée" : "Dicter mes critères"}
      title={unavailable ? "Dictée non disponible sur ce navigateur" : "Dicter mes critères"}
      className={cn("rounded-full", state === "recording" && "animate-pulse")}
    >
      {state === "transcribing" ? <Loader2 className="animate-spin" /> : state === "recording" ? <Square /> : <Mic />}
    </Button>
  );
}
