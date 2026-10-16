import Link from "next/link";
import { Building2, MessageSquareText, Mic, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

const STEPS = [
  { icon: Mic, title: "Dites-le comme vous le pensez", text: "À l'écrit ou à l'oral : « calme mais proche de bars sympas, à 30 min de mon école »." },
  { icon: MessageSquareText, title: "L'IA connaît Paris", text: "Batignolles, Butte-aux-Cailles, Montorgueil… ou les quartiers qui collent à votre style de vie." },
  { icon: Sparkles, title: "3 biens, pas 300", text: "Uniquement vos Perfect Matches, chacun expliqué : pourquoi ce bien est fait pour vous." },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-16 sm:py-24">
      <p className="text-sm font-medium text-ai-foreground">Location à Paris intra-muros</p>
      <h1 className="mt-3 max-w-3xl font-serif text-4xl font-semibold tracking-tight sm:text-6xl">
        Décrivez votre vie parisienne. On trouve l&apos;appartement.
      </h1>
      <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
        Un assistant qui comprend les micro-quartiers, calcule vos temps de trajet et ne vous montre que les
        trois biens qui vous correspondent vraiment.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button asChild size="lg">
          <Link href="/search">
            <Sparkles /> Lancer ma recherche
          </Link>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link href="/proprietaire">
            <Building2 /> Publier une annonce
          </Link>
        </Button>
      </div>
      <div className="mt-20 grid gap-6 sm:grid-cols-3">
        {STEPS.map(({ icon: Icon, title, text }) => (
          <div key={title} className="rounded-xl border bg-card p-6">
            <Icon className="size-5 text-ai-foreground" />
            <h2 className="mt-4 font-medium">{title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{text}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
