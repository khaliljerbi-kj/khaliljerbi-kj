# Paris Immo IA — MVP

Plateforme de location 100 % parisienne : le locataire décrit son mode de vie (à l'écrit ou à la voix),
l'IA en extrait une recherche structurée, et le moteur ne renvoie que **3 Perfect Matches**, chacun avec un
encadré rédigé sur-mesure : *« Pourquoi ce bien est fait pour vous ? »*.

```
┌──────────── Next.js (App Router, Tailwind v4, Shadcn UI) ────────────┐
│  /search        chat + micro + 3 Fiches Biens + création d'alerte    │
│  /proprietaire  tableau de bord + création d'annonce (Server Action) │──┐ Prisma
│  /api/backend/* → proxy vers FastAPI                                 │  │
└──────────────────────────────────┬───────────────────────────────────┘  │
                                   ▼                                      ▼
┌──────────────────────── FastAPI (Python) ───────────────┐      ┌──────────────┐
│ POST /api/chat        LLM (function calling) → critères │◀────▶│  PostgreSQL  │
│                       → matching → pitchs LLM           │ SQL- │ users        │
│ POST /api/transcribe  Whisper                           │ Alch.│ properties   │
│ POST /api/alerts      enregistre la recherche JSON      │      │ search_alerts│
│ worker alertes        nouveaux biens > 90 % → email     │      └──────────────┘
└─────────────────────────────────────────────────────────┘
        shared/quartiers.json · shared/places.json (base de connaissances commune)
```

## Démarrage rapide

Prérequis : Node 20+, Python 3.11+, Docker (ou un PostgreSQL 13+).

```bash
docker compose up -d                      # PostgreSQL

cd frontend
cp .env.example .env
npm install                               # génère aussi le client Prisma
npx prisma migrate deploy                 # crée les tables
npm run db:seed                           # 10 biens de démo
npm run dev                               # http://localhost:3000

cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                      # ajoutez vos clés API
uvicorn app.main:app --reload --port 8000
python -m app.workers.alerts --loop 300   # (optionnel) worker d'alertes
pytest                                    # 22 tests, SQLite en mémoire
```

**Sans aucune clé API**, l'application fonctionne : un extracteur à base de règles remplace le LLM, les
temps de trajet sont estimés et le micro utilise la Web Speech API du navigateur. Ajoutez
`ANTHROPIC_API_KEY` ou `OPENAI_API_KEY` pour la vraie compréhension du langage naturel,
`OPENAI_API_KEY` pour Whisper, `GOOGLE_MAPS_API_KEY` pour les trajets réels.

**Mettre en ligne gratuitement** (Neon + Render + Vercel) : voir [DEPLOIEMENT.md](DEPLOIEMENT.md).

## Fonctionnalités

### A. Chatbot locataire
- **Extraction structurée** (`backend/app/services/llm.py`) : le LLM est *forcé* d'appeler l'outil
  `enregistrer_recherche`, dont le schéma JSON est généré depuis le modèle Pydantic `SearchCriteria`
  (budget CC, trajet max + destination, ambiance, quartiers, critères durs/souhaits, DPE…). La sortie est
  revalidée par Pydantic ; les slugs de quartiers inconnus sont écartés ; en cas d'erreur, repli heuristique.
- **Multi-tours** : les critères accumulés sont renvoyés à chaque tour, le LLM renvoie l'objet complet à jour.
- **Micro-quartiers** : 28 quartiers (`shared/quartiers.json`) avec scores calme / vie nocturne / familial,
  tags et lignes de métro, injectés dans le prompt système. Quartier cité → `quartiers` ; simple mode de vie
  → `suggested_quartiers` déduits (ambiance + proximité de la destination).
- **Anthropic ou OpenAI** : même prompt, même schéma (`LLM_PROVIDER=auto|anthropic|openai|heuristic`).
- **Voix** : `MediaRecorder` → `POST /api/transcribe` (Whisper, langue fr). Si le backend n'a pas de clé,
  bascule automatique sur la Web Speech API.

### B. Matching & priorisation (`backend/app/services/matching.py`)
1. **Filtres durs** : budget (+5 % de tolérance), surface, pièces, meublé/vide, indispensables, DPE, trajet (+25 %).
2. **Score pondéré 0-100 explicable** : budget 20, trajet 25, localisation 20, ambiance 20, surface 10,
   bonus 10, énergie 5 — seuls les critères exprimés comptent. Un bien **sur cour** satisfait le besoin de
   calme même dans un quartier animé (Oberkampf, Charonne…).
3. **Base locale d'abord** : si ≥ 3 biens locaux dépassent `PERFECT_MATCH_SCORE` (75), seuls eux sont renvoyés.
4. **Fallback externe simulé** (`scraper_mock.py`, SeLoger/Leboncoin) pour compléter, de façon déterministe.
5. **Jamais plus de 3 résultats**, diversifiés par quartier.
6. **Trajet irréaliste** : Télécom Paris est à Palaiseau (~45 min depuis Paris). Plutôt qu'une page vide,
   le critère est assoupli, les biens les plus proches sont proposés et un bandeau l'explique.

### C. Fiche Bien
Loyer CC (et HC + charges), surface, pièces, DPE coloré, étage/ascenseur, meublé/vide, temps de trajet,
équipements, détail du score, et l'encadré IA généré par un second appel d'outil (`rediger_pitchs`) qui
reçoit la demande d'origine + les données réelles du bien (consigne : n'inventer aucun fait).

### D. Alertes
`POST /api/alerts` stocke le JSON de recherche dans `search_alerts`. `check_alerts()`
(`backend/app/services/alerts.py`) évalue uniquement les biens publiés depuis le dernier passage, envoie un
email (SMTP, ou log en dev) si un bien dépasse 90 %, avec un lien de désabonnement (confirmation par POST).
À lancer en cron (`python -m app.workers.alerts`), en boucle (`--loop 300`) ou dans le process API
(`ALERTS_INTERVAL_SECONDS`).

### E. Espace propriétaire
Server Action Next.js + Prisma + validation Zod : la fiche est en ligne immédiatement et matchée en priorité.
Les DPE G sont refusés (interdits à la location depuis le 1er janvier 2025) ; surface minimale 9 m².

**Photos** : jusqu'à 8 photos (JPEG, PNG, WebP) par glisser-déposer, avec aperçus, retrait et photo de
couverture. Elles sont redimensionnées et compressées dans le navigateur (1600 px, ~350 Ko) pour tenir
sous la limite de 4,5 Mo par requête de Vercel, vérifiées par signature binaire côté serveur, puis
stockées dans PostgreSQL (table `photos`) et servies par `/photos/[id]` avec un cache permanent. Aucun
disque persistant n'est donc nécessaire. Sur la Fiche Bien, elles s'affichent en carrousel.

## Choix techniques

- **Prisma est la source de vérité du schéma** (`frontend/prisma/schema.prisma`) et gère les migrations.
  Le backend Python lit/écrit les mêmes tables via un miroir SQLAlchemy (`backend/app/models.py`) ; les
  UUID et dates sont générés côté base pour que les deux clients écrivent des lignes valides.
- **Google Distance Matrix plutôt que Mapbox** : Mapbox ne calcule pas d'itinéraires en transports en commun.
- **Proxy `/api/backend/*`** dans `next.config.ts` : pas de CORS ni d'URL d'API exposée au navigateur.

## Limites du MVP / prochaines étapes

- Authentification (NextAuth / Clerk) : l'espace propriétaire liste aujourd'hui toutes les annonces.
- Géocodage des adresses (API Adresse BAN) : les biens sont placés au centre de leur micro-quartier.
- Encadrement des loyers parisien : comparer le loyer saisi au loyer de référence majoré.
- Sources externes réelles : passer par des flux partenaires plutôt que du scraping (CGU des portails).
- Photos sur un stockage objet (S3 / R2 / Vercel Blob) au-delà de quelques milliers de photos.
- Streaming de la réponse du chat et cache des temps de trajet.
