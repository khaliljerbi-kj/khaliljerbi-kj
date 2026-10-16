"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowUp, Home, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { sendChat } from "@/lib/api";
import type { ChatMessage, ChatResponse, SearchCriteria } from "@/lib/types";
import { cn } from "@/lib/utils";

import { AlertForm } from "./alert-form";
import { CriteriaChips } from "./criteria-chips";
import { MicButton } from "./mic-button";
import { PropertyCard } from "./property-card";

const GREETING: ChatMessage = {
  role: "assistant",
  content:
    "Bonjour ! Décrivez-moi le logement de vos rêves comme vous le diriez à un ami : budget, quartier ou ambiance, trajet quotidien… Vous pouvez aussi utiliser le micro.",
};

const EXAMPLES = [
  "Je cherche un truc calme mais proche de bars sympas, à moins de 30 min en métro de Télécom Paris, avec la fibre.",
  "Un 2 pièces meublé aux Batignolles ou à Montorgueil, 1 500 € max.",
  "Je ne connais pas Paris : quartier familial avec des parcs, 3 pièces, 2 200 €.",
];

export function SearchExperience() {
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [input, setInput] = useState("");
  const [criteria, setCriteria] = useState<SearchCriteria | null>(null);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dictationBase = useRef("");
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function submit(text: string) {
    const content = text.trim();
    if (!content || loading) return;
    const next = [...messages, { role: "user" as const, content }];
    setMessages(next);
    setInput("");
    setError(null);
    setLoading(true);
    try {
      // Le message d'accueil est purement visuel : on ne l'envoie pas au LLM.
      const res = await sendChat(next.slice(1), criteria);
      setMessages([...next, { role: "assistant", content: res.reply }]);
      setCriteria(res.criteria);
      if (res.ready_to_search) setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Le service est momentanément indisponible.");
    } finally {
      setLoading(false);
    }
  }

  const userQuery = messages
    .filter((m) => m.role === "user")
    .map((m) => m.content)
    .join(" ");

  return (
    <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:h-[calc(100dvh-3.5rem)] lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      {/* Chat */}
      <section className="flex min-h-[70dvh] flex-col overflow-hidden rounded-2xl border bg-card lg:min-h-0">
        <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          {messages.map((m, i) => (
            <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
              <div
                className={cn(
                  "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                  m.role === "user" ? "rounded-br-sm bg-primary text-primary-foreground" : "rounded-bl-sm bg-muted",
                )}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Analyse de vos critères et recherche des biens…
            </div>
          )}
          {messages.length === 1 && (
            <div className="space-y-2 pt-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Exemples</p>
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => submit(ex)}
                  className="block w-full rounded-xl border px-4 py-2.5 text-left text-sm transition-colors hover:bg-accent"
                >
                  {ex}
                </button>
              ))}
            </div>
          )}
        </div>

        {criteria && (
          <div className="border-t bg-muted/40 px-4 py-3">
            <CriteriaChips criteria={criteria} />
          </div>
        )}

        <form
          className="flex items-end gap-2 border-t p-3"
          onSubmit={(e) => {
            e.preventDefault();
            submit(input);
          }}
        >
          <MicButton
            disabled={loading}
            onStart={() => (dictationBase.current = input.trim() ? `${input.trim()} ` : "")}
            onTranscript={(text) => setInput(`${dictationBase.current}${text}`)}
            onError={setError}
          />
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(input);
              }
            }}
            rows={1}
            placeholder="Ex. : calme, proche de bars, 30 min max de mon école…"
            className="max-h-40 min-h-9 resize-none"
          />
          <Button type="submit" size="icon" className="rounded-full" disabled={loading || !input.trim()} aria-label="Envoyer">
            <ArrowUp />
          </Button>
        </form>
        {error && <p className="px-4 pb-3 text-sm text-destructive">{error}</p>}
      </section>

      {/* Résultats */}
      <section className="space-y-4 lg:overflow-y-auto lg:pr-1">
        <div className="flex items-baseline justify-between gap-4">
          <h1 className="font-serif text-2xl font-semibold">Vos Perfect Matches</h1>
          {result?.matches.length ? (
            <span className="text-xs text-muted-foreground">
              {result.used_external_sources ? "Notre base + portails partenaires" : "100 % issus de nos propriétaires"}
            </span>
          ) : null}
        </div>

        {result?.notes.map((note) => (
          <p key={note} className="flex gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" /> {note}
          </p>
        ))}

        {loading ? (
          <div className="grid gap-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-96 rounded-xl" />
            ))}
          </div>
        ) : result?.matches.length ? (
          <>
            <div className="grid gap-4">
              {result.matches.map((p, i) => (
                <PropertyCard key={p.id} property={p} rank={i + 1} />
              ))}
            </div>
            <AlertForm criteria={result.criteria} query={userQuery} />
          </>
        ) : (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed p-12 text-center text-muted-foreground">
            {result ? <Home className="size-8" /> : <Sparkles className="size-8" />}
            <p className="mt-3 max-w-sm text-sm">
              {result
                ? "Aucun bien ne passe vos critères éliminatoires. Essayez d'assouplir le budget ou les équipements."
                : "Vos 3 biens idéaux apparaîtront ici, chacun avec une explication personnalisée."}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
