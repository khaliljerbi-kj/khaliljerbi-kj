import { revalidatePath } from "next/cache";
import { notFound } from "next/navigation";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

async function disable(formData: FormData) {
  "use server";
  const id = z.string().uuid().parse(formData.get("id"));
  await prisma.searchAlert.update({ where: { id }, data: { active: false } });
  revalidatePath(`/alertes/${id}/desactiver`);
}

// Confirmation explicite (POST) : un simple GET pourrait être déclenché par l'antivirus d'une messagerie.
export default async function DisableAlert({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!z.string().uuid().safeParse(id).success) notFound();
  const alert = await prisma.searchAlert.findUnique({ where: { id }, include: { user: true } });
  if (!alert) notFound();

  return (
    <main className="mx-auto max-w-md px-4 py-20 text-center">
      <h1 className="font-serif text-2xl font-semibold">Alerte de recherche</h1>
      <p className="mt-3 text-sm text-muted-foreground">« {alert.query} »</p>
      {alert.active ? (
        <form action={disable} className="mt-8">
          <input type="hidden" name="id" value={alert.id} />
          <Button type="submit" variant="outline">
            Ne plus recevoir d&apos;emails pour {alert.user.email}
          </Button>
        </form>
      ) : (
        <p className="mt-8 text-sm">Cette alerte est désactivée. Vous ne recevrez plus d&apos;emails.</p>
      )}
    </main>
  );
}
