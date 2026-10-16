const eur = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const num = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const pct = new Intl.NumberFormat("fr-FR", { style: "percent", maximumFractionDigits: 1, signDisplay: "exceptZero" });
const pctPlain = new Intl.NumberFormat("fr-FR", { style: "percent", maximumFractionDigits: 0 });

export const formatEur = (v: number) => eur.format(v);
export const formatEurM2 = (v: number) => `${eur.format(v)}/m²`;
export const formatK = (v: number) => `${num.format(v / 1000)} k€`;
export const formatPct = (v: number) => pct.format(v);
export const formatPctPlain = (v: number) => pctPlain.format(v);
