"use client";

import { useEffect, useRef, useState } from "react";
import { ImagePlus, Loader2, X } from "lucide-react";

import { compressImage } from "@/lib/compress-image";
import { cn } from "@/lib/utils";

const MAX = 8;
const ACCEPT = ["image/jpeg", "image/png", "image/webp"];
const MAX_TOTAL = 4 * 1024 * 1024; // une requête Vercel est limitée à 4,5 Mo, marge comprise

/**
 * Sélection de photos avec aperçus. Les photos sont compressées dans le navigateur, puis
 * placées dans un <input type="file" name="photos"> synchronisé via DataTransfer, ce qui
 * permet d'en ajouter en plusieurs fois et d'en retirer.
 */
export function PhotoPicker({ error }: { error?: string }) {
  const input = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    const dt = new DataTransfer();
    files.forEach((f) => dt.items.add(f));
    if (input.current) input.current.files = dt.files;
    return () => urls.forEach(URL.revokeObjectURL);
  }, [files]);

  async function add(picked: File[]) {
    const images = picked.filter((f) => ACCEPT.includes(f.type));
    setLocalError(images.length < picked.length ? "Formats acceptés : JPEG, PNG, WebP." : null);
    if (!images.length) return;
    setProcessing(true);
    const compressed = await Promise.all(images.map(compressImage));
    setProcessing(false);

    const next = [...files, ...compressed].slice(0, MAX);
    let total = next.reduce((sum, f) => sum + f.size, 0);
    while (next.length > files.length && total > MAX_TOTAL) total -= next.pop()!.size;
    if (next.length < files.length + compressed.length) {
      setLocalError(
        next.length === MAX ? `${MAX} photos maximum.` : "Taille maximale atteinte : certaines photos n'ont pas été ajoutées.",
      );
    }
    setFiles(next);
  }

  const message = localError ?? error;
  return (
    <div>
      {/* Input réel envoyé avec le formulaire (toujours monté, même à 8 photos) ; piloté par `files`.
          Pas de `disabled` : un input désactivé serait exclu du FormData. */}
      <input
        ref={input}
        id="photos"
        type="file"
        name="photos"
        accept={ACCEPT.join(",")}
        multiple
        className="sr-only"
        // Copie de la sélection avant que l'effet ne la remplace par la liste cumulée.
        onChange={(e) => add(Array.from(e.target.files ?? []))}
      />
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {previews.map((src, i) => (
          <div key={src} className="relative aspect-[4/3] overflow-hidden rounded-lg border bg-muted">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={src} alt={files[i]?.name ?? ""} className="size-full object-cover" />
            {i === 0 && (
              <span className="absolute bottom-1 left-1 rounded bg-background/90 px-1.5 py-0.5 text-[10px] font-medium">
                Couverture
              </span>
            )}
            <button
              type="button"
              onClick={() => setFiles((current) => current.filter((_, j) => j !== i))}
              className="absolute right-1 top-1 rounded-full bg-background/90 p-1 opacity-80 hover:opacity-100"
              aria-label={`Retirer ${files[i]?.name ?? "la photo"}`}
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}
        {files.length < MAX && (
          <label
            htmlFor="photos"
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              add(Array.from(e.dataTransfer.files));
            }}
            className={cn(
              "flex aspect-[4/3] cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border border-dashed text-center text-xs text-muted-foreground transition-colors hover:bg-accent",
              dragging && "border-primary bg-accent",
              files.length === 0 && "col-span-3 aspect-auto py-8 sm:col-span-4",
            )}
          >
            {processing ? <Loader2 className="size-5 animate-spin" /> : <ImagePlus className="size-5" />}
            {processing
              ? "Optimisation des photos…"
              : files.length === 0
                ? "Glissez vos photos ici ou cliquez pour choisir (JPEG, PNG, WebP)"
                : "Ajouter"}
          </label>
        )}
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">
        {files.length}/{MAX} photos · la première sert de couverture · optimisées automatiquement.
      </p>
      {message && <p className="mt-1 text-xs text-destructive">{message}</p>}
    </div>
  );
}
