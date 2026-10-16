import "server-only";

import { randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

// Stockage disque pour le MVP ; à remplacer par S3 / R2 en production.
// Hors de public/ : `next start` ne sert que les fichiers présents au moment du build.
export const UPLOAD_DIR = process.env.UPLOAD_DIR ?? path.join(process.cwd(), "uploads");

export const MAX_PHOTOS = 8;
export const MAX_PHOTO_BYTES = 8 * 1024 * 1024;

const TYPES = {
  jpg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
} as const;
type Ext = keyof typeof TYPES;

export const PHOTO_NAME = /^[0-9a-f-]{36}\.(jpg|png|webp)$/;

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
    if (file.size > MAX_PHOTO_BYTES) return `« ${file.name} » dépasse 8 Mo.`;
    const head = new Uint8Array(await file.slice(0, 12).arrayBuffer());
    if (!sniff(head)) return `« ${file.name} » n'est pas une image JPEG, PNG ou WebP.`;
  }
  return null;
}

/** Enregistre les photos (déjà validées) et renvoie leurs URL publiques. */
export async function savePhotos(files: File[]): Promise<string[]> {
  await mkdir(UPLOAD_DIR, { recursive: true });
  return Promise.all(
    files.map(async (file) => {
      const bytes = new Uint8Array(await file.arrayBuffer());
      const name = `${randomUUID()}.${sniff(bytes)!}`;
      await writeFile(path.join(UPLOAD_DIR, name), bytes);
      return `/photos/${name}`;
    }),
  );
}

export async function readPhoto(name: string) {
  if (!PHOTO_NAME.test(name)) return null;
  try {
    const data = await readFile(path.join(UPLOAD_DIR, name));
    return { data, type: TYPES[name.split(".").pop() as Ext] };
  } catch {
    return null;
  }
}
