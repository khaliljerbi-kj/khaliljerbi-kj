# Immo Quant · Frontend (Next.js)

Carte plein écran de Paris (react-map-gl + MapLibre GL, fond vectoriel CARTO Dark Matter, sans token) :
les rues chargées dans les tuiles sont recolorées selon le prix au m² estimé, sur une surface de prix translucide.
Un clic sur une rue (ou un bâtiment : la rue la plus proche est retenue) appelle `/api/estimate` et ouvre le panneau d'analyse
(prix actuel, historique 5 ans, fan chart Monte Carlo 1/5/10 ans, tableau des horizons).

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000 — l'API FastAPI doit tourner sur :8000
```

`/api/*` est proxifié vers `BACKEND_URL` (défaut `http://127.0.0.1:8000`, voir `next.config.ts`).

Stack : Next.js 16 (App Router), Tailwind CSS 4, composants shadcn/ui (`src/components/ui`), Recharts, lucide-react.

Pour passer à Mapbox : remplacer l'import `react-map-gl/maplibre` par `react-map-gl/mapbox`, ajouter `mapbox-gl`
et un `mapboxAccessToken` ; les noms de calques de tuiles (`transportation_name`, `building`) devront suivre le schéma Mapbox Streets (`road`, `building`).
