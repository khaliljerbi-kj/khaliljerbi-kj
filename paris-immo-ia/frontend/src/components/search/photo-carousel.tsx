"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

export function PhotoCarousel({ photos, alt }: { photos: string[]; alt: string }) {
  const [index, setIndex] = useState(0);
  const go = (delta: number) => setIndex((i) => (i + delta + photos.length) % photos.length);
  const many = photos.length > 1;

  return (
    <div className="absolute inset-0">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={photos[index]} alt={`${alt} — photo ${index + 1}`} className="size-full object-cover" />
      <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/40 to-transparent" />
      {many && (
        <>
          {[
            { delta: -1, Icon: ChevronLeft, side: "left-2", label: "Photo précédente" },
            { delta: 1, Icon: ChevronRight, side: "right-2", label: "Photo suivante" },
          ].map(({ delta, Icon, side, label }) => (
            <button
              key={label}
              type="button"
              onClick={() => go(delta)}
              aria-label={label}
              className={cn(
                "absolute top-1/2 -translate-y-1/2 rounded-full bg-background/85 p-1.5 text-foreground shadow-sm hover:bg-background",
                side,
              )}
            >
              <Icon className="size-4" />
            </button>
          ))}
          <div className="absolute bottom-2.5 left-1/2 flex -translate-x-1/2 gap-1.5">
            {photos.map((src, i) => (
              <button
                key={src}
                type="button"
                onClick={() => setIndex(i)}
                aria-label={`Photo ${i + 1}`}
                className={cn("size-1.5 rounded-full bg-white/60", i === index && "w-4 bg-white")}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
