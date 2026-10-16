import "server-only";

import { randomUUID } from "node:crypto";

import { prisma } from "@/lib/prisma";

// Photos stockées en base (table `photos`) : aucun disque persistant requis, ce qui
// permet l'hébergement serverless (Vercel). Le navigateur les compresse avant envoi.

export const MAX_PHOTOS = 8;
export const MAX_PHOTO_BYTES = 3 * 1024 * 1024;

const TYPES = {
  jpg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
} as const;
type Ext = keyof typeof TYPES;

export const PHOTO_NAME = /^([0-9a-f-]{36})\.(jpg|png|webp)$/;

/** Identifie le format par sa signature binaire plutôt que par le type annoncé par le navigateur. */
function sniff(bytes: Uint8Array): Ext | null {
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "jpg";
  if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return "png";
  const ascii = (from: number, to: number) => String.fromCharCode(...bytes.slice(from, to));
  if (ascii(0, 4) === "RIFF" && ascii(8, 12) === "WEBP") return "webp";
  return null;
}

/** Vérifie les fichiers et renvoie un message d'erreur, ou null s'ils sont tous valides. */
export async function validatePhotos(files: File[]): Promise<string | null> {
  if (files.length > MAX_PHOTOS) return `${MAX_PHOTOS} photos maximum.`;
  for (const file of files) {
    if (file.size > MAX_PHOTO_BYTES) return `« ${file.name} » est trop lourde (3 Mo max).`;
    const head = new Uint8Array(await file.slice(0, 12).arrayBuffer());
    if (!sniff(head)) return `« ${file.name} » n'est pas une image JPEG, PNG ou WebP.`;
  }
  return null;
}

/**
 * Prépare des photos déjà validées : lignes à créer avec le bien (création imbriquée Prisma)
 * et URL publiques correspondantes, dans l'ordre choisi par le propriétaire.
 */
export async function preparePhotos(files: File[]) {
  const rows = await Promise.all(
    files.map(async (file) => {
      const bytes = new Uint8Array(await file.arrayBuffer());
      const ext = sniff(bytes)!;
      return { id: randomUUID(), mimeType: TYPES[ext], data: bytes, ext };
    }),
  );
  return {
    create: rows.map(({ id, mimeType, data }) => ({ id, mimeType, data })),
    urls: rows.map(({ id, ext }) => `/photos/${id}.${ext}`),
  };
}

export async function readPhoto(name: string) {
  const match = PHOTO_NAME.exec(name);
  if (!match) return null;
  return prisma.photo.findUnique({ where: { id: match[1] }, select: { data: true, mimeType: true } });
}
