"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { prisma } from "@/lib/prisma";
import { QUARTIERS, quartierBySlug } from "@/lib/quartiers";

const checkbox = z.preprocess((v) => v === "on" || v === "true", z.boolean());
const int = (min: number, max: number, label: string) =>
  z.coerce.number({ invalid_type_error: `${label} invalide` }).int().min(min, `${label} : minimum ${min}`).max(max, `${label} : maximum ${max}`);

const PropertySchema = z.object({
  email: z.string().trim().toLowerCase().email("Email invalide"),
  name: z.string().trim().max(80).optional(),
  title: z.string().trim().min(5, "Titre trop court").max(120),
  description: z.string().trim().min(20, "Décrivez le bien en quelques phrases (20 caractères min.)").max(4000),
  address: z.string().trim().min(5, "Adresse requise").max(200),
  quartier: z.enum(QUARTIERS.map((q) => q.slug) as [string, ...string[]], { message: "Choisissez un quartier" }),
  rentHc: int(100, 20000, "Loyer hors charges"),
  charges: int(0, 2000, "Charges"),
  surface: z.coerce.number().min(9, "Un logement décent fait au moins 9 m²").max(500),
  rooms: int(1, 12, "Pièces"),
  bedrooms: int(0, 10, "Chambres"),
  floor: int(-1, 60, "Étage"),
  dpe: z
    .enum(["A", "B", "C", "D", "E", "F", "G"])
    .refine((d) => d !== "G", "Les logements classés G sont interdits à la location depuis le 1er janvier 2025."),
  hasElevator: checkbox,
  furnished: checkbox,
  hasFiber: checkbox,
  facesCourtyard: checkbox,
  hasBalcony: checkbox,
  hasParking: checkbox,
  hasCellar: checkbox,
  hasDishwasher: checkbox,
  petsAllowed: checkbox,
  photoUrl: z.union([z.literal(""), z.string().url("URL de photo invalide")]).optional(),
  availableFrom: z.union([z.literal(""), z.coerce.date()]).optional(),
});

export type FormState = {
  ok: boolean;
  message?: string;
  errors?: Partial<Record<string, string[]>>;
};

export async function createProperty(_prev: FormState, formData: FormData): Promise<FormState> {
  const parsed = PropertySchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { ok: false, message: "Certains champs sont à corriger.", errors: parsed.error.flatten().fieldErrors };
  }
  const { email, name, photoUrl, availableFrom, quartier, ...data } = parsed.data;
  const q = quartierBySlug(quartier)!;

  const owner = await prisma.user.upsert({
    where: { email },
    create: { email, name: name || null, role: "LANDLORD" },
    update: { role: "LANDLORD", ...(name ? { name } : {}) },
  });

  await prisma.property.create({
    data: {
      ...data,
      ownerId: owner.id,
      quartier,
      arrondissement: q.arrondissement,
      // Position du micro-quartier ; à remplacer par un géocodage de l'adresse (BAN / Google).
      latitude: q.lat,
      longitude: q.lng,
      photos: photoUrl ? [photoUrl] : [],
      availableFrom: availableFrom || null,
      status: "ACTIVE",
    },
  });

  revalidatePath("/proprietaire");
  return { ok: true, message: "Annonce publiée : elle est immédiatement proposée en priorité aux locataires." };
}

export async function setPropertyStatus(formData: FormData) {
  const id = z.string().uuid().parse(formData.get("id"));
  const status = z.enum(["ACTIVE", "RENTED"]).parse(formData.get("status"));
  await prisma.property.update({ where: { id }, data: { status } });
  revalidatePath("/proprietaire");
}
