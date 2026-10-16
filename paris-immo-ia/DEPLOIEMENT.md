# Mettre Paris Immo IA en ligne gratuitement

Trois services gratuits, sans carte bancaire, en vous connectant avec votre compte GitHub :

| Rôle | Service | Offre gratuite |
|---|---|---|
| Base PostgreSQL | [Neon](https://neon.tech) | 0,5 Go, sans limite de durée |
| Backend FastAPI | [Render](https://render.com) | 750 h/mois ; **veille après 15 min sans visite**, ~30 s de réveil |
| Frontend Next.js | [Vercel](https://vercel.com) | offre Hobby |

Durée : 15 à 20 minutes. Suivez l'ordre ci-dessous : chaque étape fournit une valeur à la suivante.

## 0. Fusionner la pull request

Render et Vercel déploient la branche `main`. Fusionnez d'abord la PR « Paris Immo IA » sur GitHub.

## 1. Neon — la base de données

1. Sur [neon.tech](https://neon.tech), **Sign up** → *Continue with GitHub*.
2. **Create project** : nom `paris-immo-ia`, région **AWS Europe Central 1 (Frankfurt)**.
3. Bouton **Connect** du tableau de bord → **désactivez « Connection pooling »** → copiez la chaîne
   de connexion. Elle ressemble à :
   `postgresql://neondb_owner:xxxx@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`

👉 C'est votre **`DATABASE_URL`**, à coller dans Render et dans Vercel.

## 2. Render — le backend

1. Sur [render.com](https://render.com), **Get Started** → *GitHub*, et autorisez l'accès au dépôt
   `khaliljerbi-kj`.
2. **New +** → **Blueprint** → choisissez le dépôt. Render lit `render.yaml` (à la racine du dépôt).
3. Renseignez les variables demandées :
   - `DATABASE_URL` : la chaîne Neon ;
   - `FRONTEND_URL` : laissez vide pour l'instant (étape 4) ;
   - `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY` : **facultatives**. Sans clé, l'app
     fonctionne avec l'extracteur à règles, des trajets estimés et la dictée du navigateur.
4. **Apply**. Le premier build prend 3 à 5 minutes.
5. Copiez l'URL du service, par ex. `https://paris-immo-ia-api.onrender.com` (un suffixe est ajouté si le
   nom est déjà pris). Vérifiez que `https://…onrender.com/api/health` répond `{"status":"ok", …}`.

👉 C'est votre **`BACKEND_URL`**.

## 3. Vercel — le site

1. Sur [vercel.com](https://vercel.com), **Sign Up** → *Continue with GitHub*.
2. **Add New… → Project** → **Import** du dépôt `khaliljerbi-kj/khaliljerbi-kj`.
3. **Root Directory** : `paris-immo-ia/frontend` (bouton *Edit*). Laissez cochée l'option
   *Include files outside the root directory* : le site lit `paris-immo-ia/shared/`.
4. **Environment Variables** :
   - `DATABASE_URL` = la chaîne Neon ;
   - `BACKEND_URL` = l'URL Render, **sans** `/` final.
5. **Deploy**. Le build crée les tables (`prisma migrate deploy`), ajoute 10 biens de démo, puis compile
   le site (2 à 3 minutes).
6. Ouvrez l'URL fournie, par ex. `https://paris-immo-ia.vercel.app`. 🎉

## 4. Finaliser

Dans Render → votre service → **Environment** : `FRONTEND_URL` = l'URL Vercel (utilisée dans les liens
des emails d'alerte) → **Save changes**.

## Bon à savoir

- **Premier message lent** : si personne n'a utilisé le site depuis 15 min, le backend Render dort.
  La page de recherche le réveille dès son ouverture et réessaie automatiquement ; comptez jusqu'à 30 s.
- **Changer `BACKEND_URL`** : Next.js l'intègre au moment du build. Après modification, redéployez
  (Vercel → *Deployments* → ⋯ → *Redeploy*).
- **Photos** : stockées dans Neon (table `photos`), compressées dans le navigateur (~350 Ko chacune).
  0,5 Go représentent environ 1 500 photos.
- **Alertes** : vérifiées toutes les 15 min tant que le backend est éveillé. Sans `SMTP_HOST`, les
  emails sont seulement écrits dans les logs Render. Pour de vrais envois, ajoutez les variables
  `SMTP_*` (ex. offre gratuite de Brevo) dans Render.
- **Mises à jour** : chaque push sur `main` redéploie automatiquement Render et Vercel.

## Dépannage

| Symptôme | Cause probable |
|---|---|
| Build Vercel : `Can't reach database server` | `DATABASE_URL` mal copiée, ou pooling Neon activé |
| Build Vercel : `Cannot find module '@shared/quartiers.json'` | option *Include files outside the root directory* décochée |
| Le chat affiche « Erreur 404 » | `BACKEND_URL` absente ou avec un `/` final → corrigez puis *Redeploy* |
| Le chat affiche « Erreur 504 » | backend Render en cours de réveil : renvoyez le message |
| Render : `ModuleNotFoundError` | le Blueprint doit garder `rootDir: paris-immo-ia` |
