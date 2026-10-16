"use client";

import { useState } from "react";
import { BellRing, Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createAlert } from "@/lib/api";
import type { SearchCriteria } from "@/lib/types";

export function AlertForm({ criteria, query }: { criteria: SearchCriteria; query: string }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    try {
      await createAlert(email, query, criteria);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
      setStatus("error");
    }
  }

  if (status === "done") {
    return (
      <p className="flex items-center gap-2 rounded-xl border bg-card p-4 text-sm">
        <Check className="size-4 text-emerald-600" /> Alerte créée : nous vous écrivons dès qu&apos;un nouveau bien
        dépasse 90 % de correspondance.
      </p>
    );
  }
  return (
    <form onSubmit={submit} className="rounded-xl border bg-card p-4">
      <p className="flex items-center gap-2 text-sm font-medium">
        <BellRing className="size-4 text-ai-foreground" /> Soyez prévenu en premier
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Un email dès qu&apos;un nouveau bien correspond à plus de 90 % à cette recherche.
      </p>
      <div className="mt-3 flex gap-2">
        <Input
          type="email"
          required
          placeholder="vous@exemple.fr"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          aria-label="Votre email"
        />
        <Button type="submit" disabled={status === "loading"}>
          {status === "loading" && <Loader2 className="animate-spin" />} Créer l&apos;alerte
        </Button>
      </div>
      {status === "error" && <p className="mt-2 text-sm text-destructive">{error}</p>}
    </form>
  );
}
