"use client";

import { useEffect, useRef, useState } from "react";
import { ImagePlus, X } from "lucide-react";

import { cn } from "@/lib/utils";

const MAX = 8;
const ACCEPT = "image/jpeg,image/png,image/webp";

/**
 * Sélection de photos avec aperçus. Les fichiers restent dans un <input type="file" name="photos">
 * synchronisé via DataTransfer, ce qui permet d'en ajouter en plusieurs fois et d'en retirer.
 */
export function PhotoPicker({ error }: { error?: string }) {
  const input = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    const dt = new DataTransfer();
    files.forEach((f) => dt.items.add(f));
    if (input.current) input.current.files = dt.files;
    return () => urls.forEach(URL.revokeObjectURL);
  }, [files]);

  const add = (list: FileList | null) => {
    const images = Array.from(list ?? []).filter((f) => ACCEPT.includes(f.type));
    setFiles((current) => [...current, ...images].slice(0, MAX));
  };

  return (
    <div>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {previews.map((src, i) => (
          <div key={src} className="group relative aspect-[4/3] overflow-hidden rounded-lg border bg-muted">
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
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              add(e.dataTransfer.files);
            }}
            className={cn(
              "flex aspect-[4/3] cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border border-dashed text-center text-xs text-muted-foreground transition-colors hover:bg-accent",
              dragging && "border-primary bg-accent",
              files.length === 0 && "col-span-3 aspect-auto py-8 sm:col-span-4",
            )}
          >
            <ImagePlus className="size-5" />
            {files.length === 0 ? "Glissez vos photos ici ou cliquez pour choisir (JPEG, PNG, WebP · 8 Mo max)" : "Ajouter"}
            {/* Input réel envoyé avec le formulaire ; son contenu est piloté par `files`. */}
            <input
              ref={input}
              type="file"
              name="photos"
              accept={ACCEPT}
              multiple
              className="sr-only"
              onChange={(e) => {
                // Copie avant que l'effet ne remplace input.files par la sélection cumulée.
                const picked = e.target.files;
                add(picked);
              }}
            />
          </label>
        )}
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">
        {files.length}/{MAX} photos · la première sert de couverture.
      </p>
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}
