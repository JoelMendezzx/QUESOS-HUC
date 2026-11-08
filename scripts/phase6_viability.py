"""
Fase 6 — Viabilidad de los modelos producción -> compuestos (A) y producción -> aroma (C)
con los datos por muestra extraídos (clean/muestras/). Análisis exploratorios dentro de cada estudio;
no se combinan valores con unidades distintas.

Salida: results/fase6/
Uso: python scripts/phase6_viability.py
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import kruskal, spearmanr

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "clean", "muestras")
OUT = os.path.join(ROOT, "results", "fase6")
os.makedirs(OUT, exist_ok=True)

s = pd.read_csv(os.path.join(M, "sample.csv"))
sc = pd.read_csv(os.path.join(M, "sample_compound.csv"))
sd = pd.read_csv(os.path.join(M, "sample_descriptor.csv"))
res = {}

# ---------------------------------------------------------------- A1. maduración -> compuestos (dentro de cada estudio)
trend_rows = []
conc = sc[sc.measure_type.isin(["concentracion", "abundancia_relativa"]) & sc.compound_id.notna()].merge(
    s[["sample_id", "study_id", "ripening_days", "milk_heat_treatment_reported"]], on="sample_id")
conc = conc[conc.ripening_days.notna()]
for (study, heat, cid), g in conc.groupby(["study_id", "milk_heat_treatment_reported", "compound_id"], dropna=False):
    g = g.assign(v=g.value.fillna(0.0).where(g.detected != False, 0.0))
    if g.ripening_days.nunique() < 4 or g.v.nunique() < 2:
        continue
    rho, p = spearmanr(g.ripening_days, g.v)
    trend_rows.append(dict(study_id=study, milk_heat_treatment=heat, compound_id=cid,
                           compound_name=g.compound_name_source.iloc[0], n_tiempos=g.ripening_days.nunique(),
                           spearman_rho=round(rho, 3), p_value=round(p, 4),
                           tendencia="aumenta" if rho > 0.5 else ("disminuye" if rho < -0.5 else "sin tendencia clara")))
trend = pd.DataFrame(trend_rows)
trend.to_csv(os.path.join(OUT, "A1_tendencias_maduracion.csv"), index=False, encoding="utf-8-sig")

# coherencia entre estudios: mismo compuesto, misma dirección con la maduración
pivot = trend.pivot_table(index="compound_id", columns=["study_id", "milk_heat_treatment"], values="spearman_rho")
shared = pivot.dropna(thresh=2)
coh = []
for cid, r in shared.iterrows():
    vals = r.dropna()
    signs = np.sign(vals.values)
    coh.append(dict(compound_id=cid, name=trend[trend.compound_id == cid].compound_name.iloc[0],
                    n_series=len(vals), series=", ".join(f"{a}/{b}" for a, b in vals.index),
                    rhos=", ".join(f"{v:.2f}" for v in vals.values),
                    misma_direccion=bool((signs > 0).all() or (signs < 0).all())))
coh = pd.DataFrame(coh)
coh.to_csv(os.path.join(OUT, "A2_coherencia_entre_series.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- A3. pasteurización -> compuestos (DUE24A/B, pares emparejados)
hp = sc[sc.measure_type == "concentracion"].merge(s[["sample_id", "study_id", "ripening_days", "milk_heat_treatment_reported", "production_unit"]], on="sample_id")
hp = hp[hp.study_id.isin(["DUE24A", "DUE24B"])]
hp["pair"] = hp.study_id + "|" + hp.ripening_days.astype(str) + "|" + hp.sample_id.str.extract(r"(B\d|W\d+)$")[0]
pv = hp.pivot_table(index=["pair", "compound_name_source"], columns="milk_heat_treatment_reported", values="value").dropna()
pv["log2_raw_vs_past"] = np.log2(pv["raw"] / pv["pasteurized"])
past = pv.reset_index().groupby("compound_name_source").agg(
    n_pares=("log2_raw_vs_past", "size"), log2_medio=("log2_raw_vs_past", "mean"),
    pares_raw_mayor=("log2_raw_vs_past", lambda x: int((x > 0).sum()))).reset_index().sort_values("log2_medio")
past.to_csv(os.path.join(OUT, "A3_efecto_pasteurizacion.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- C1. producción -> aroma (dentro de cada estudio)
aro = sd[sd.modality == "aroma"].merge(s[["sample_id", "study_id", "ripening_days", "ripening_category_reported",
                                          "other_process", "milk_heat_treatment_reported"]], on="sample_id")
# Chen 2022: suma de frecuencia GC-O por familia y categoría de maduración
ch = aro[aro.study_id == "CHE22"].copy()
ch["mf"] = ch.value.fillna(0)
chf = ch.groupby(["sample_id", "ripening_category_reported", "aroma_family"]).mf.sum().reset_index()
krow = []
for fam, g in chf.groupby("aroma_family"):
    groups = [g[g.ripening_category_reported == c].mf.values for c in ["young", "medium", "aged"]]
    if all(len(x) >= 2 for x in groups) and np.var(np.concatenate(groups)) > 0:
        H, p = kruskal(*groups)
        krow.append(dict(study="CHE22", aroma_family=fam, young=round(groups[0].mean(), 1), medium=round(groups[1].mean(), 1),
                         aged=round(groups[2].mean(), 1), kruskal_H=round(H, 2), p_value=round(p, 4), n_por_grupo=4))
chen_k = pd.DataFrame(krow)
chen_k.to_csv(os.path.join(OUT, "C1_chen_familias_por_maduracion.csv"), index=False, encoding="utf-8-sig")

# Torri 2021: intensidad media RATA por estilo y correlación con días de maduración
to = aro[aro.study_id == "TOR21"].copy()
to["style"] = to.other_process.str.extract(r"estilo (\w+)")[0]
trow = []
for att, g in to.groupby("descriptor_source"):
    rho, p = spearmanr(g.ripening_days, g.value)
    trow.append(dict(study="TOR21", atributo=att, aroma_family=g.aroma_family.iloc[0],
                     media_sweet=round(g[g["style"] == "Sweet"].value.mean(), 2),
                     media_piquant=round(g[g["style"] == "Piquant"].value.mean(), 2),
                     spearman_dias=round(rho, 2), p_value=round(p, 3), n=len(g)))
tor = pd.DataFrame(trow)
tor.to_csv(os.path.join(OUT, "C2_torri_atributos_por_estilo.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- viabilidad: cuentas
both = s[s.has_production_variable & s.has_descriptor_data]
res["muestras"] = len(s)
res["estudios"] = int(s.study_id.nunique())
res["unidades_produccion_independientes"] = int(s.production_unit.nunique())
res["muestras_produccion_y_aroma"] = len(both)
res["estudios_produccion_y_aroma"] = int(both.study_id.nunique())
res["metodos_aroma"] = sd[sd.modality == "aroma"].groupby("evaluation_method").sample_id.nunique().to_dict()
res["variables_produccion_por_estudio"] = {
    st: [c for c in ["milk_heat_treatment_reported", "ripening_days", "ripening_category_reported", "storage_days",
                     "other_process"] if g[c].nunique() > 1]
    for st, g in s.groupby("study_id")}
res["series_maduracion_compuestos"] = int(trend[["study_id", "milk_heat_treatment"]].drop_duplicates().shape[0])
res["compuestos_con_tendencia_en_2_o_mas_series"] = len(coh)
res["coherencia_misma_direccion"] = int(coh.misma_direccion.sum()) if len(coh) else 0
json.dump(res, open(os.path.join(OUT, "resumen_viabilidad.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# figura: compuestos comunes y su tendencia
if len(coh):
    top = trend[trend.compound_id.isin(coh.compound_id)]
    fig, ax = plt.subplots(figsize=(8, max(3, 0.28 * len(coh))))
    names = coh.sort_values("name").name.tolist()
    cols = {("DUE24A", "pasteurized"): "#3b7dd8", ("DUE24A", "raw"): "#d95f02", ("IDI23", "raw"): "#1b9e77"}
    for (st, ht), g in top.groupby(["study_id", "milk_heat_treatment"]):
        g = g.set_index("compound_name").reindex(names)
        ax.scatter(g.spearman_rho, range(len(names)), label=f"{st} / {ht}", color=cols.get((st, ht), "grey"))
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=7)
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("Spearman ρ (compuesto vs días de maduración)")
    ax.set_title("Tendencias con la maduración en compuestos medidos en ≥ 2 series")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "tendencias_maduracion.png"), dpi=150)

print(json.dumps(res, ensure_ascii=False, indent=1))
print(coh.to_string())
print(chen_k.to_string())
print(tor.to_string())
print(past.to_string())
