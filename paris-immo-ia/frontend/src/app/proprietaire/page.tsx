import type { Metadata } from "next";
import { BellRing, Building2, KeyRound } from "lucide-react";

import { PropertyForm } from "@/components/landlord/property-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { prisma } from "@/lib/prisma";
import { quartierBySlug } from "@/lib/quartiers";
import { euros } from "@/lib/utils";

import { setPropertyStatus } from "./actions";

export const metadata: Metadata = { title: "Espace propriétaire · Paris Immo IA" };
export const dynamic = "force-dynamic";

export default async function LandlordDashboard() {
  // MVP sans authentification : toutes les annonces sont listées.
  const [properties, activeCount, alertCount] = await Promise.all([
    prisma.property.findMany({
      orderBy: { createdAt: "desc" },
      take: 30,
      include: { owner: { select: { email: true } } },
    }),
    prisma.property.count({ where: { status: "ACTIVE" } }),
    prisma.searchAlert.count({ where: { active: true } }),
  ]);

  const stats = [
    { icon: Building2, label: "Annonces actives", value: activeCount },
    { icon: BellRing, label: "Locataires en alerte", value: alertCount },
    { icon: KeyRound, label: "Biens loués", value: properties.filter((p) => p.status === "RENTED").length },
  ];

  return (
    <main className="mx-auto max-w-7xl space-y-8 px-4 py-8">
      <div>
        <h1 className="font-serif text-3xl font-semibold">Espace propriétaire</h1>
        <p className="mt-1 text-muted-foreground">
          Vos annonces sont proposées en priorité aux locataires dont la recherche correspond.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {stats.map(({ icon: Icon, label, value }) => (
          <Card key={label} className="gap-2 py-5">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardDescription>{label}</CardDescription>
              <Icon className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent className="text-3xl font-semibold">{value}</CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="font-serif text-xl">Nouvelle Fiche Bien</CardTitle>
            <CardDescription>Plus la fiche est précise, plus le matching IA est pertinent.</CardDescription>
          </CardHeader>
          <CardContent>
            <PropertyForm />
          </CardContent>
        </Card>

        <section className="space-y-3">
          <h2 className="font-medium">Annonces récentes</h2>
          {properties.length === 0 && (
            <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
              Aucune annonce pour l&apos;instant.
            </p>
          )}
          {properties.map((p) => (
            <div key={p.id} className="flex items-start gap-3 rounded-xl border bg-card p-4">
              {Array.isArray(p.photos) && typeof p.photos[0] === "string" ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={p.photos[0]} alt="" className="size-16 shrink-0 rounded-lg object-cover" />
              ) : (
                <div className="flex size-16 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <Building2 className="size-5 text-muted-foreground" />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{p.title}</p>
                <p className="text-sm text-muted-foreground">
                  {quartierBySlug(p.quartier)?.nom ?? p.quartier} · {p.surface} m² · {euros(p.rentHc + p.charges)} CC ·
                  DPE {p.dpe}
                </p>
                <p className="truncate text-xs text-muted-foreground">{p.owner.email}</p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-2">
                <Badge variant={p.status === "ACTIVE" ? "ai" : "secondary"}>
                  {p.status === "ACTIVE" ? "En ligne" : p.status === "RENTED" ? "Loué" : "Brouillon"}
                </Badge>
                <form action={setPropertyStatus}>
                  <input type="hidden" name="id" value={p.id} />
                  <input type="hidden" name="status" value={p.status === "ACTIVE" ? "RENTED" : "ACTIVE"} />
                  <Button type="submit" variant="ghost" size="sm">
                    {p.status === "ACTIVE" ? "Marquer loué" : "Remettre en ligne"}
                  </Button>
                </form>
              </div>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
