"use client";

import { startTransition, useActionState, useEffect, useRef, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

import { createProperty, type FormState } from "@/app/proprietaire/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { QUARTIERS } from "@/lib/quartiers";

import { PhotoPicker } from "./photo-picker";

const FEATURES = [
  { name: "furnished", label: "Meublé" },
  { name: "hasFiber", label: "Fibre optique" },
  { name: "facesCourtyard", label: "Donne sur cour (calme)" },
  { name: "hasElevator", label: "Ascenseur" },
  { name: "hasBalcony", label: "Balcon / terrasse" },
  { name: "hasDishwasher", label: "Lave-vaisselle" },
  { name: "hasCellar", label: "Cave" },
  { name: "hasParking", label: "Parking" },
  { name: "petsAllowed", label: "Animaux acceptés" },
];

function Field({
  name,
  label,
  errors,
  children,
  className,
}: {
  name: string;
  label: string;
  errors?: FormState["errors"];
  children: React.ReactNode;
  className?: string;
}) {
  const error = errors?.[name]?.[0];
  return (
    <div className={className}>
      <Label htmlFor={name} className="mb-1.5">
        {label}
      </Label>
      {children}
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}

export function PropertyForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(createProperty, { ok: false });
  const form = useRef<HTMLFormElement>(null);
  const [resetKey, setResetKey] = useState(0);
  const e = state.errors;

  useEffect(() => {
    if (!state.ok) return;
    form.current?.reset();
    setResetKey((k) => k + 1); // vide aussi les aperçus photo
  }, [state]);

  return (
    <form
      ref={form}
      className="space-y-6"
      onSubmit={(event) => {
        // Pas de `action={...}` : React 19 viderait le formulaire même en cas d'erreur de validation.
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        startTransition(() => action(data));
      }}
    >
      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="mb-3 text-sm font-semibold">Vous</legend>
        <Field name="email" label="Email" errors={e}>
          <Input id="email" name="email" type="email" required placeholder="proprietaire@exemple.fr" />
        </Field>
        <Field name="name" label="Nom (optionnel)" errors={e}>
          <Input id="name" name="name" placeholder="Camille Martin" />
        </Field>
      </fieldset>

      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="mb-3 text-sm font-semibold">Le bien</legend>
        <Field name="title" label="Titre de l'annonce" errors={e} className="sm:col-span-2">
          <Input id="title" name="title" required placeholder="2 pièces lumineux sur cour" />
        </Field>
        <Field name="description" label="Description" errors={e} className="sm:col-span-2">
          <Textarea
            id="description"
            name="description"
            required
            rows={4}
            placeholder="Exposition, état, environnement, commerces, transports…"
          />
        </Field>
        <Field name="address" label="Adresse" errors={e}>
          <Input id="address" name="address" required placeholder="12 rue de la Butte-aux-Cailles, 75013" />
        </Field>
        <Field name="quartier" label="Micro-quartier" errors={e}>
          <NativeSelect id="quartier" name="quartier" required defaultValue="">
            <option value="" disabled>
              Choisir…
            </option>
            {QUARTIERS.map((q) => (
              <option key={q.slug} value={q.slug}>
                {q.arrondissement}e · {q.nom}
              </option>
            ))}
          </NativeSelect>
        </Field>
      </fieldset>

      <fieldset className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <legend className="mb-3 text-sm font-semibold">Données clés</legend>
        <Field name="rentHc" label="Loyer HC (€)" errors={e}>
          <Input id="rentHc" name="rentHc" type="number" min={100} required />
        </Field>
        <Field name="charges" label="Charges (€)" errors={e}>
          <Input id="charges" name="charges" type="number" min={0} defaultValue={0} required />
        </Field>
        <Field name="surface" label="Surface (m²)" errors={e}>
          <Input id="surface" name="surface" type="number" step="0.5" min={9} required />
        </Field>
        <Field name="dpe" label="DPE" errors={e}>
          <NativeSelect id="dpe" name="dpe" defaultValue="D">
            {["A", "B", "C", "D", "E", "F", "G"].map((d) => (
              <option key={d}>{d}</option>
            ))}
          </NativeSelect>
        </Field>
        <Field name="rooms" label="Pièces" errors={e}>
          <Input id="rooms" name="rooms" type="number" min={1} defaultValue={2} required />
        </Field>
        <Field name="bedrooms" label="Chambres" errors={e}>
          <Input id="bedrooms" name="bedrooms" type="number" min={0} defaultValue={1} required />
        </Field>
        <Field name="floor" label="Étage" errors={e}>
          <Input id="floor" name="floor" type="number" min={-1} defaultValue={0} required />
        </Field>
        <Field name="availableFrom" label="Disponible le" errors={e}>
          <Input id="availableFrom" name="availableFrom" type="date" />
        </Field>
      </fieldset>

      <fieldset>
        <legend className="mb-3 text-sm font-semibold">Atouts (utilisés par le matching IA)</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <label key={f.name} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm has-checked:border-primary has-checked:bg-secondary">
              <input type="checkbox" name={f.name} className="accent-[var(--primary)]" /> {f.label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-3 text-sm font-semibold">Photos</legend>
        <PhotoPicker key={resetKey} error={e?.photos?.[0]} />
      </fieldset>

      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" size="lg" disabled={pending}>
          {pending && <Loader2 className="animate-spin" />} Publier l&apos;annonce
        </Button>
        {state.message && (
          <p className={state.ok ? "flex items-center gap-1.5 text-sm text-emerald-700" : "text-sm text-destructive"}>
            {state.ok && <CheckCircle2 className="size-4" />} {state.message}
          </p>
        )}
      </div>
    </form>
  );
}
