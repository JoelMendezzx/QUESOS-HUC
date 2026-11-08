"""
Fase 5 — DIAGNÓSTICO del modelo compuesto -> familia aromática.

No reentrena el modelo final ni toca results/fase5/. Responde, con las mismas etiquetas y la misma
validación agrupada por esqueleto InChIKey:

  1. ¿Cuánto cambia la métrica al calcularla por pliegue en vez de juntar las predicciones?
  2. ¿Cuánto pesa la fuga del preprocesamiento (bits, mediana, escalado ajustados con todos los datos)?
  3. ¿De dónde sale la señal? (solo huella, solo fisicoquímicas, solo clase química, combinaciones)
  4. ¿Ayudarían más datos? (curva de aprendizaje con 40 %, 60 %, 80 % y 100 % del entrenamiento)
  5. ¿Sobreajusta? (AUPRC en entrenamiento frente a prueba)
  6. ¿Solo acierta con compuestos parecidos a los de entrenamiento? (similitud de Tanimoto)
  7. ¿Hay etiquetas dudosas? (probabilidad que el modelo da a los positivos según su respaldo en Flavornet
     y su puntuación de evidencia)

Uso:   python scripts/phase5_diagnostico.py
       DIAG_REPS=5 python scripts/phase5_diagnostico.py   (más repeticiones = más estable, más lento)
Salida: results/fase5_diagnostico/ (CSV por prueba + diagnostico_resumen.txt)
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_quality as P4  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "clean")
OUT = os.path.join(ROOT, "results", "fase5_diagnostico")
os.makedirs(OUT, exist_ok=True)

FAM6 = ["fruity", "vegetal", "lactic", "floral", "toasted", "animal"]
PHYS = ["molecular_weight", "xlogp", "tpsa", "hbond_donors", "hbond_acceptors", "rotatable_bonds", "heavy_atoms"]
N_REP = int(os.environ.get("DIAG_REPS", 3))
N_SPLIT = 5
SEED = 2026
LOG = []


def say(txt=""):
    print(txt)
    LOG.append(str(txt))


# ============================================================ datos (igual que phase5_model.py)
fo = pd.read_csv(os.path.join(C, "modelo", "fact_compound_odor.csv"))
props = pd.read_csv(os.path.join(C, "modelo", "compound_properties.csv"))
dc = pd.read_csv(os.path.join(C, "soporte", "dim_compound.csv"))
ar = fo[fo.is_aroma_target == True]  # noqa: E712
compounds = sorted(set(ar.compound_id) & set(props.compound_id))

Y = pd.DataFrame(0, index=compounds, columns=FAM6)
for c, f in zip(ar.compound_id, ar.aroma_family):
    if f in FAM6 and c in Y.index:
        Y.loc[c, f] = 1
Ym = Y.values

pr = props.set_index("compound_id").loc[compounds].reset_index()
FP = np.array([P4.fingerprint_bits(b) or [0] * 881 for b in pr.fingerprint2d_b64], dtype=float)
PH = pr[PHYS].astype(float).copy()
PH["xlogp_missing"] = PH.xlogp.isna().astype(float)
chem = dc.set_index("compound_id").chemical_class.reindex(compounds).fillna("sin_clase").values

FP_COLS = [f"fp_{i}" for i in range(FP.shape[1])]
PH_COLS = list(PH.columns)
XDF = pd.concat([pd.DataFrame(FP, columns=FP_COLS), PH.reset_index(drop=True)], axis=1)
XDF["chem"] = chem

# grupos exactamente como en phase5_model.py
raw_key = pr.inchikey.fillna(pr.compound_id)
groups = raw_key.str[:14].values

# ============================================================ 0. comprobaciones de los datos
say("=" * 78)
say("0. COMPROBACIONES DE LOS DATOS")
say("=" * 78)
say(f"Compuestos: {len(compounds)} | grupos de estructura: {len(set(groups))} | repeticiones: {N_REP}")
sin_ik = pr.inchikey.isna()
say(f"Compuestos sin InChIKey (agrupados por compound_id[:14]): {int(sin_ik.sum())}")
g = pd.DataFrame({"compound_id": compounds, "group": groups, "inchikey": pr.inchikey.values})
multi = g.groupby("group").filter(lambda d: len(d) > 1)
choque = multi.groupby("group").filter(lambda d: d.inchikey.isna().any())
say(f"Grupos con más de un compuesto: {multi.group.nunique()} "
    f"(de ellos, con algún compuesto sin InChIKey -> posible choque por truncar el ID: {choque.group.nunique()})")
if len(choque):
    choque.to_csv(os.path.join(OUT, "0_grupos_sospechosos.csv"), index=False, encoding="utf-8-sig")
say("Positivos por familia: " + ", ".join(f"{f} {int(Y[f].sum())}" for f in FAM6))
co = pd.DataFrame(Ym.T @ Ym, index=FAM6, columns=FAM6)
co.to_csv(os.path.join(OUT, "0_coocurrencia_familias.csv"), encoding="utf-8-sig")
say("Coocurrencia de familias (diagonal = positivos) -> 0_coocurrencia_familias.csv")

# ============================================================ particiones fijas (las mismas para todas las pruebas)
SPLITS = []
for rep in range(N_REP):
    gkf = GroupKFold(n_splits=N_SPLIT, shuffle=True, random_state=SEED + rep)
    SPLITS.append(list(gkf.split(XDF, Ym, groups)))


# ============================================================ modelos y preprocesamiento
def rf():
    return RandomForestClassifier(n_estimators=400, min_samples_leaf=2, max_features="sqrt",
                                  class_weight="balanced_subsample", random_state=0, n_jobs=-1)


def lr():
    return LogisticRegression(C=0.05, class_weight="balanced", max_iter=3000)


def preprocessor(use_fp=True, use_ph=True, use_chem=False):
    parts = []
    if use_fp:
        parts.append(("fp", VarianceThreshold(0.0), FP_COLS))
    if use_ph:
        parts.append(("ph", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), PH_COLS))
    if use_chem:
        parts.append(("chem", OneHotEncoder(handle_unknown="ignore"), ["chem"]))
    return ColumnTransformer(parts, sparse_threshold=0)


def run_cv(model_fn, feats, mode="infold", frac=1.0, train_scores=False, tag=""):
    """mode='infold': preprocesamiento ajustado dentro de cada pliegue (correcto).
       mode='global': ajustado con TODOS los compuestos antes de la CV (como phase5_model.py)."""
    rows, oofs = [], []
    rng = np.random.default_rng(SEED)
    if mode == "global":
        Xg = preprocessor(**feats).fit_transform(XDF)
    for rep, splits in enumerate(SPLITS):
        P = np.zeros(Ym.shape)
        for k, (tr, te) in enumerate(splits):
            if frac < 1.0:  # submuestra de GRUPOS del entrenamiento
                ug = np.unique(groups[tr])
                keep = rng.choice(ug, size=max(2, int(round(frac * len(ug)))), replace=False)
                tr = tr[np.isin(groups[tr], keep)]
            for j, f in enumerate(FAM6):
                ytr, yte = Ym[tr, j], Ym[te, j]
                if ytr.sum() == 0:
                    P[te, j] = 0.0
                    continue
                if mode == "global":
                    clf = model_fn().fit(Xg[tr], ytr)
                    P[te, j] = clf.predict_proba(Xg[te])[:, 1]
                    ptr = clf.predict_proba(Xg[tr])[:, 1] if train_scores else None
                else:
                    pipe = Pipeline([("pre", preprocessor(**feats)), ("clf", model_fn())]).fit(XDF.iloc[tr], ytr)
                    P[te, j] = pipe.predict_proba(XDF.iloc[te])[:, 1]
                    ptr = pipe.predict_proba(XDF.iloc[tr])[:, 1] if train_scores else None
                if 0 < yte.sum() < len(yte):
                    row = dict(tag=tag, rep=rep, fold=k, family=f, n_test=len(te), pos_test=int(yte.sum()),
                               prev_test=yte.mean(), auprc=average_precision_score(yte, P[te, j]),
                               roc_auc=roc_auc_score(yte, P[te, j]))
                    if train_scores:
                        row["auprc_train"] = average_precision_score(ytr, ptr)
                    rows.append(row)
        oofs.append(P)
    return pd.DataFrame(rows), np.array(oofs)


def pooled(oofs):
    """Métrica 'juntando pliegues', como phase5_model.py: una AUPRC por repetición y familia."""
    out = []
    for P in oofs:
        for j, f in enumerate(FAM6):
            out.append(dict(family=f, auprc_pooled=average_precision_score(Ym[:, j], P[:, j]),
                            roc_pooled=roc_auc_score(Ym[:, j], P[:, j])))
    return pd.DataFrame(out).groupby("family").mean()


def by_family(df, col="auprc"):
    return df.groupby("family")[col].mean().reindex(FAM6)


def macro(df, col="auprc"):
    return by_family(df, col).mean()


# ============================================================ 1. métrica por pliegue frente a juntar pliegues
say()
say("=" * 78)
say("1. ¿CAMBIA LA MÉTRICA AL CALCULARLA POR PLIEGUE?")
say("=" * 78)
prev_real = Y.mean().reindex(FAM6)
# modelo de prevalencia: predice la proporción del entrenamiento (igual que m_prevalence)
prev_oofs = []
for splits in SPLITS:
    P = np.zeros(Ym.shape)
    for tr, te in splits:
        P[te] = Ym[tr].mean(0)
    prev_oofs.append(P)
pp = pooled(np.array(prev_oofs))
t1 = pd.DataFrame({"prevalencia_real": prev_real, "auprc_prevalencia_juntando": pp.auprc_pooled.reindex(FAM6),
                   "roc_prevalencia_juntando": pp.roc_pooled.reindex(FAM6)})
say(t1.round(3).to_string())
say(f"-> El azar real es la prevalencia (macro {prev_real.mean():.3f}) y su ROC-AUC es 0,50. Si al juntar "
    f"pliegues sale {pp.auprc_pooled.mean():.3f} y ROC {pp.roc_pooled.mean():.3f}, la línea base está "
    "distorsionada por mezclar pliegues.")
t1.to_csv(os.path.join(OUT, "1_linea_base_prevalencia.csv"), encoding="utf-8-sig")

# ============================================================ 2. fuga del preprocesamiento
say()
say("=" * 78)
say("2. FUGA DEL PREPROCESAMIENTO (global = como hoy; infold = corregido)")
say("=" * 78)
FEATS_ACT = dict(use_fp=True, use_ph=True, use_chem=False)
res2, oof_store = [], {}
for name, fn in [("random_forest", rf), ("reg_logistica", lr)]:
    for mode in ["global", "infold"]:
        df, oofs = run_cv(fn, FEATS_ACT, mode=mode, train_scores=(name == "random_forest" and mode == "infold"),
                          tag=f"{name}_{mode}")
        oof_store[(name, mode)] = (df, oofs)
        pl = pooled(oofs)
        res2.append(dict(modelo=name, preprocesamiento=mode, macro_auprc_por_pliegue=macro(df),
                         macro_auprc_juntando=pl.auprc_pooled.mean(), macro_roc_por_pliegue=macro(df, "roc_auc")))
t2 = pd.DataFrame(res2)
say(t2.round(3).to_string(index=False))
for name in ["random_forest", "reg_logistica"]:
    a = t2[(t2.modelo == name) & (t2.preprocesamiento == "global")].macro_auprc_por_pliegue.iloc[0]
    b = t2[(t2.modelo == name) & (t2.preprocesamiento == "infold")].macro_auprc_por_pliegue.iloc[0]
    say(f"-> {name}: diferencia global - infold = {a - b:+.3f} "
        f"({'despreciable' if abs(a - b) < 0.01 else 'IMPORTANTE: la fuga infla la métrica'})")
t2.to_csv(os.path.join(OUT, "2_fuga_preprocesamiento.csv"), index=False, encoding="utf-8-sig")

# ============================================================ 3. de dónde sale la señal
say()
say("=" * 78)
say("3. ¿DE DÓNDE SALE LA SEÑAL? (preprocesamiento correcto, AUPRC por pliegue)")
say("=" * 78)
ABL = {
    "solo_huella": dict(use_fp=True, use_ph=False, use_chem=False),
    "solo_fisicoquimicas": dict(use_fp=False, use_ph=True, use_chem=False),
    "solo_clase_quimica": dict(use_fp=False, use_ph=False, use_chem=True),
    "huella+fisico (actual)": FEATS_ACT,
    "huella+fisico+clase": dict(use_fp=True, use_ph=True, use_chem=True),
}
t3 = {}
for name, fn in [("random_forest", rf), ("reg_logistica", lr)]:
    for lab, feats in ABL.items():
        if lab == "huella+fisico (actual)":
            df = oof_store[(name, "infold")][0]
        else:
            df, _ = run_cv(fn, feats, tag=f"{name}_{lab}")
        t3[(name, lab)] = by_family(df)
t3 = pd.DataFrame(t3).T
t3["MACRO"] = t3.mean(1)
t3.loc[("prevalencia_real", ""), :] = list(prev_real.values) + [prev_real.mean()]
say(t3.round(3).to_string())
t3.to_csv(os.path.join(OUT, "3_ablacion_variables.csv"), encoding="utf-8-sig")
for name in ["random_forest", "reg_logistica"]:
    gain = t3.loc[(name, "huella+fisico+clase")] - t3.loc[(name, "huella+fisico (actual)")]
    say(f"-> {name}: agregar la clase química como variable cambia el macro-AUPRC en {gain['MACRO']:+.3f} "
        f"(por familia: " + ", ".join(f"{f} {gain[f]:+.2f}" for f in FAM6) + ")")

# ============================================================ 4 y 5. curva de aprendizaje y sobreajuste
say()
say("=" * 78)
say("4. ¿AYUDARÍAN MÁS DATOS? (curva de aprendizaje, random forest, preprocesamiento correcto)")
say("=" * 78)
t4 = {}
for frac in [0.4, 0.6, 0.8, 1.0]:
    df = oof_store[("random_forest", "infold")][0] if frac == 1.0 else run_cv(rf, FEATS_ACT, frac=frac)[0]
    t4[f"{int(frac * 100)} %"] = by_family(df)
t4 = pd.DataFrame(t4).T
t4["MACRO"] = t4.mean(1)
say(t4.round(3).to_string())
t4.to_csv(os.path.join(OUT, "4_curva_aprendizaje.csv"), encoding="utf-8-sig")
slope = (t4.loc["100 %"] - t4.loc["60 %"])
for f in FAM6 + ["MACRO"]:
    s = slope[f]
    verdict = "sigue subiendo: más datos probablemente ayuden" if s > 0.02 else \
        ("sube poco" if s > 0.005 else "plana: más datos del mismo tipo ayudarían poco")
    say(f"   {f:8s} 60 %->100 %: {s:+.3f}  {verdict}")

say()
say("5. SOBREAJUSTE (AUPRC en entrenamiento frente a prueba, random forest)")
df_rf = oof_store[("random_forest", "infold")][0]
t5 = pd.DataFrame({"auprc_entrenamiento": by_family(df_rf, "auprc_train"), "auprc_prueba": by_family(df_rf)})
t5["brecha"] = t5.auprc_entrenamiento - t5.auprc_prueba
say(t5.round(3).to_string())
say("-> Una brecha grande con entrenamiento cerca de 1 indica que memoriza: más datos, más regularización "
    "(min_samples_leaf, max_depth) o variables más generales.")
t5.to_csv(os.path.join(OUT, "5_sobreajuste.csv"), encoding="utf-8-sig")

# ============================================================ 6. similitud con el entrenamiento
say()
say("=" * 78)
say("6. ¿SOLO ACIERTA CON COMPUESTOS PARECIDOS? (Tanimoto máximo con el entrenamiento)")
say("=" * 78)
B = FP.astype(bool)
inter = B.astype(int) @ B.astype(int).T
cnt = B.sum(1)
union = cnt[:, None] + cnt[None, :] - inter
TAN = np.where(union > 0, inter / np.maximum(union, 1), 0.0)
maxsim = np.zeros(len(compounds))
nrep = np.zeros(len(compounds))
for splits in SPLITS:
    for tr, te in splits:
        maxsim[te] += TAN[np.ix_(te, tr)].max(1)
        nrep[te] += 1
maxsim /= np.maximum(nrep, 1)
oof_rf = oof_store[("random_forest", "infold")][1].mean(0)
cut = np.median(maxsim)
rows6 = []
for j, f in enumerate(FAM6):
    for lab, m in [("poco_parecidos", maxsim < cut), ("muy_parecidos", maxsim >= cut)]:
        y = Ym[m, j]
        if 0 < y.sum() < len(y):
            rows6.append(dict(family=f, grupo=lab, n=int(m.sum()), pos=int(y.sum()), prevalencia=y.mean(),
                              auprc=average_precision_score(y, oof_rf[m, j])))
t6 = pd.DataFrame(rows6)
t6["auprc_sobre_prevalencia"] = t6.auprc / t6.prevalencia
say(f"Mediana del Tanimoto máximo con el entrenamiento: {cut:.2f}")
say(t6.round(3).to_string(index=False))
say("-> Si 'poco_parecidos' queda cerca de su prevalencia, el modelo solo reconoce análogos cercanos: "
    "hacen falta compuestos más variados (Pyrfume/GoodScents), no un algoritmo más complejo.")
t6.to_csv(os.path.join(OUT, "6_similitud.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame({"compound_id": compounds, "tanimoto_max_entrenamiento": maxsim}).to_csv(
    os.path.join(OUT, "6_similitud_por_compuesto.csv"), index=False, encoding="utf-8-sig")

# ============================================================ 7. calidad de etiquetas
say()
say("=" * 78)
say("7. ¿HAY ETIQUETAS DUDOSAS? (percentil que el modelo da a cada positivo dentro de su familia)")
say("=" * 78)
pct = pd.DataFrame(oof_rf, index=compounds, columns=FAM6).rank(pct=True)
pos = ar[ar.aroma_family.isin(FAM6) & ar.compound_id.isin(compounds)].copy()
pos["percentil_modelo"] = [pct.loc[c, f] for c, f in zip(pos.compound_id, pos.aroma_family)]
for col in ["flavornet_support", "harmonization_status", "max_evidence_score"]:
    if col not in pos.columns:
        say(f"(columna {col} no está en fact_compound_odor.csv; se omite)")
        continue
    if col == "max_evidence_score":
        pos["_bin"] = pd.cut(pos[col], [-np.inf, 0.4, 0.6, 0.8, np.inf], labels=["<0.4", "0.4-0.6", "0.6-0.8", ">=0.8"])
        key = "_bin"
    else:
        key = col
    t7 = pos.groupby(["aroma_family", key]).percentil_modelo.agg(["count", "mean"]).unstack(key)
    say(f"\nPercentil medio de los positivos según {col} (más bajo = el modelo 'no se lo cree'):")
    say(t7["mean"].round(2).to_string())
    t7.to_csv(os.path.join(OUT, f"7_etiquetas_por_{col}.csv"), encoding="utf-8-sig")
low = (pos.sort_values("percentil_modelo")
       .drop_duplicates(["compound_id", "aroma_family"])
       .merge(dc[["compound_id", "iupac_name", "chemical_class"]], on="compound_id", how="left"))
cols = [c for c in ["compound_id", "iupac_name", "chemical_class", "aroma_family", "percentil_modelo",
                    "flavornet_support", "max_evidence_score", "harmonization_status"] if c in low.columns]
low[cols].head(40).to_csv(os.path.join(OUT, "7_positivos_menos_creibles.csv"), index=False, encoding="utf-8-sig")
say("-> Si los positivos sin respaldo en Flavornet o con evidencia baja tienen percentiles mucho menores, hay ruido "
    "en las etiquetas. Lista para revisar a mano: 7_positivos_menos_creibles.csv")

# ============================================================ resumen
say()
say("=" * 78)
say("RESUMEN PARA DECIDIR")
say("=" * 78)
rf_g = t2[(t2.modelo == "random_forest") & (t2.preprocesamiento == "global")].macro_auprc_por_pliegue.iloc[0]
rf_i = t2[(t2.modelo == "random_forest") & (t2.preprocesamiento == "infold")].macro_auprc_por_pliegue.iloc[0]
say(f"- Random forest, macro-AUPRC por pliegue: {rf_i:.3f} corregido ({rf_g:.3f} con la fuga). "
    f"Azar real: {prev_real.mean():.3f}.")
best = t3.drop(index=("prevalencia_real", "")).MACRO.idxmax()
say(f"- Mejor combinación de variables: {best[0]} con {best[1]} (macro {t3.loc[best, 'MACRO']:.3f}).")
say(f"- Curva de aprendizaje 60 %->100 %: {slope['MACRO']:+.3f} en el macro.")
say(f"- Brecha de sobreajuste media: {t5.brecha.mean():.3f}.")
low_sim = t6[t6.grupo == "poco_parecidos"].set_index("family").auprc_sobre_prevalencia
say("- Compuestos poco parecidos, AUPRC/prevalencia: " + ", ".join(f"{f} {v:.1f}x" for f, v in low_sim.items()))
with open(os.path.join(OUT, "diagnostico_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG))
say(f"\nTodo guardado en {OUT}")