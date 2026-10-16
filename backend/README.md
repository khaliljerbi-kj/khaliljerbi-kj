# Immo Quant · Backend (FastAPI)

API d'estimation du prix au m² à Paris et de projection Monte Carlo (Mouvement Brownien Géométrique).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000   # docs interactives : http://localhost:8000/docs
pytest
```

## Endpoints

| Route | Description |
|---|---|
| `GET /api/estimate?lat=48.85&lon=2.33[&street=Rue de Rennes]` | Prix actuel, historique 5 ans (trimestriel), projections 10 ans pour 3 scénarios + bandes P5/P25/P75/P95, résumé à 1/5/10 ans |
| `POST /api/estimate` | Idem, corps JSON `{ "lat", "lon", "street" }` (ou `street` seul) |
| `GET /api/price-grid` | Grille 90×120 du prix lissé sur Paris, utilisée pour colorer les rues |
| `GET /api/health` | Health check |

## Modèle

- **Prix actuel (mock DVF)** — `app/quant/price_field.py` : interpolation par noyau gaussien entre des prix de référence par arrondissement, texture déterministe ±4 %, prime par rue ±5 % (hash stable du nom). Toujours borné à **7 000 – 15 000 €/m²**. Même point ⇒ même résultat.
- **Historique 5 ans** — `app/quant/history.py` : cycle parisien (pic 2022, correction 2023-24) avec bêta local et bruit idiosyncratique, ancré sur le prix actuel. Calibrage μ/σ annualisés à partir des log-rendements trimestriels (pandas).
- **Projection GBM** — `app/quant/gbm.py` :
  `S_t = S_0 · exp((μ − σ²/2)·t + σ·W_t)`, discrétisation exacte, pas mensuel, 4 000 trajectoires par scénario, variables antithétiques.
  μ et σ = calibrage local rétréci vers les valeurs long terme (2 %/an, 5 %), puis chocs macro :

  | Scénario | Choc de taux | Demande | σ |
  |---|---|---|---|
  | Pessimiste | +1,5 pt (× élasticité −2 %/pt) | −0,5 %/an | ×1,35 |
  | Médian | 0 | 0 | ×1 |
  | Optimiste | −1 pt | +0,5 %/an | ×1,10 |

  Chaque courbe = médiane des trajectoires du scénario ; le fan chart = percentiles du scénario médian. P(perte) et VaR 95 % analytiques via `scipy.stats`.

Pour brancher les vraies données DVF, remplacer `estimate_price` / `build_history` par des agrégats calculés sur les fichiers DVF (data.gouv.fr) ; le reste de la chaîne est inchangé.
