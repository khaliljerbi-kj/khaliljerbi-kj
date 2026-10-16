// Jeu de données de démonstration : `npm run db:seed`
import { PrismaClient, type Prisma } from "@prisma/client";

import data from "../../shared/quartiers.json";

const prisma = new PrismaClient();
const q = (slug: string) => data.quartiers.find((x) => x.slug === slug)!;

type Seed = Omit<Prisma.PropertyUncheckedCreateInput, "ownerId" | "arrondissement" | "latitude" | "longitude">;

const PROPERTIES: Seed[] = [
  {
    title: "2 pièces sur cour, poutres apparentes",
    description: "Au calme absolu côté cour, à deux pas de la rue de la Butte-aux-Cailles et de ses bars. Cuisine équipée, parquet.",
    address: "18 rue des Cinq-Diamants, 75013 Paris",
    quartier: "butte-aux-cailles",
    rentHc: 1180, charges: 70, surface: 36, rooms: 2, bedrooms: 1, floor: 2, dpe: "D",
    furnished: true, hasFiber: true, facesCourtyard: true, hasDishwasher: true,
  },
  {
    title: "Studio optimisé proche RER B Cité U",
    description: "Studio rénové face au parc Montsouris, idéal étudiant·e du plateau de Saclay : RER B direct.",
    address: "5 boulevard Jourdan, 75014 Paris",
    quartier: "montsouris",
    rentHc: 860, charges: 50, surface: 21, rooms: 1, floor: 4, dpe: "C",
    furnished: true, hasFiber: true, hasElevator: true,
  },
  {
    title: "3 pièces familial face au square des Batignolles",
    description: "Lumineux, deux chambres, balcon filant. Écoles et marché bio à proximité.",
    address: "30 rue des Batignolles, 75017 Paris",
    quartier: "batignolles",
    rentHc: 2150, charges: 180, surface: 64, rooms: 3, bedrooms: 2, floor: 5, dpe: "C",
    hasElevator: true, hasFiber: true, hasBalcony: true, hasCellar: true, hasDishwasher: true,
  },
  {
    title: "Loft sur cour à Oberkampf",
    description: "Ancien atelier, double hauteur, donnant sur une cour pavée silencieuse en plein cœur de la vie nocturne.",
    address: "112 rue Oberkampf, 75011 Paris",
    quartier: "oberkampf",
    rentHc: 1520, charges: 90, surface: 45, rooms: 2, bedrooms: 1, floor: 0, dpe: "D",
    hasFiber: true, facesCourtyard: true, petsAllowed: true,
  },
  {
    title: "2 pièces rue Montorgueil",
    description: "Au cœur de la rue piétonne, commerces de bouche au pied de l'immeuble. Vue sur rue animée.",
    address: "48 rue Montorgueil, 75002 Paris",
    quartier: "montorgueil",
    rentHc: 1450, charges: 100, surface: 38, rooms: 2, bedrooms: 1, floor: 3, dpe: "E",
    furnished: true, hasFiber: true,
  },
  {
    title: "Studio de charme à Charonne",
    description: "Petit studio refait, quartier de caves à vin et restaurants, ligne 9 à 3 minutes.",
    address: "75 rue de Charonne, 75011 Paris",
    quartier: "charonne",
    rentHc: 890, charges: 60, surface: 22, rooms: 1, floor: 1, dpe: "D",
    furnished: true, hasFiber: true, facesCourtyard: true,
  },
  {
    title: "4 pièces bourgeois à Passy",
    description: "Haussmannien, trois chambres, gardien, très calme. Proche lycées réputés.",
    address: "22 rue de Passy, 75016 Paris",
    quartier: "passy",
    rentHc: 3400, charges: 350, surface: 98, rooms: 4, bedrooms: 3, floor: 4, dpe: "D",
    hasElevator: true, hasCellar: true, hasDishwasher: true, hasFiber: true,
  },
  {
    title: "2 pièces vue parc des Buttes-Chaumont",
    description: "Vue dégagée sur le parc, balcon, cuisine ouverte. Parfait pour jeunes parents.",
    address: "10 avenue Simon-Bolivar, 75019 Paris",
    quartier: "buttes-chaumont",
    rentHc: 1390, charges: 110, surface: 44, rooms: 2, bedrooms: 1, floor: 6, dpe: "C",
    hasElevator: true, hasBalcony: true, hasFiber: true, petsAllowed: true,
  },
  {
    title: "Studio étudiant Quartier Latin",
    description: "À 5 min du RER B Luxembourg, au calme sur cour. Bibliothèques et cinémas autour.",
    address: "9 rue Saint-Jacques, 75005 Paris",
    quartier: "quartier-latin",
    rentHc: 920, charges: 45, surface: 19, rooms: 1, floor: 5, dpe: "E",
    furnished: true, facesCourtyard: true, hasFiber: true,
  },
  {
    title: "2 pièces canal Saint-Martin",
    description: "Au bord du canal, parquet point de Hongrie, cheminée décorative.",
    address: "60 quai de Valmy, 75010 Paris",
    quartier: "canal-saint-martin",
    rentHc: 1480, charges: 90, surface: 40, rooms: 2, bedrooms: 1, floor: 2, dpe: "D",
    hasFiber: true, hasDishwasher: true,
  },
];

async function main() {
  const owner = await prisma.user.upsert({
    where: { email: "demo-proprietaire@paris-immo-ia.local" },
    create: { email: "demo-proprietaire@paris-immo-ia.local", name: "Propriétaire démo", role: "LANDLORD" },
    update: {},
  });
  // Exécuté à chaque déploiement Vercel : ne recrée les biens de démo que si besoin.
  const force = process.argv.includes("--force");
  if (!force && (await prisma.property.count({ where: { ownerId: owner.id } })) > 0) {
    console.log("Biens de démonstration déjà présents (--force pour les recréer)");
    return;
  }
  await prisma.property.deleteMany({ where: { ownerId: owner.id } });
  await prisma.property.createMany({
    data: PROPERTIES.map((p) => {
      const quartier = q(p.quartier);
      return {
        ...p,
        ownerId: owner.id,
        arrondissement: quartier.arrondissement,
        latitude: quartier.lat,
        longitude: quartier.lng,
      };
    }),
  });
  console.log(`✓ ${PROPERTIES.length} biens de démonstration créés`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
