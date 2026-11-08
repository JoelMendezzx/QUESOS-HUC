"""
Fase 5.1 — Mejoras controladas del modelo compuesto -> familia aromática.

Mismas etiquetas, mismas variables (huella PubChem + fisicoquímicas) y misma validación agrupada por
esqueleto InChIKey que phase5_model.py. Todos los modelos se evalúan en las MISMAS particiones, así que
las comparaciones son pareadas. No toca results/fase5/.

Qué cambia respecto a la Fase 5:
  1. Métricas calculadas DENTRO de cada pliegue y promediadas (además de la forma "juntando pliegues"
     de la Fase 5, para comparar). Referencia de azar calculada en cada pliegue.
  2. Preprocesamiento (bits, mediana, escalado) ajustado dentro de cada pliegue (Pipeline).
  3. Random forest regularizado: la configuración se elige con validación cruzada INTERNA (anidada),
     por familia, sin mirar nunca el pliegue de prueba.
  4. Promedio random forest + regresión logística (sin ajustar pesos: 50/50).
  5. Etiquetas débiles con menos peso SOLO al entrenar: positivos cuyo compuesto está en Flavornet pero
     con notas de otra familia ("sin_coincidencia"). Las etiquetas de prueba no se tocan.

El umbral del F1 se elige, como en la Fase 5, con validación cruzada interna sobre el entrenamiento.

Uso:   python scripts/phase5_1_mejoras.py
       (PowerShell) $env:REPS=10; python scripts/phase5_1_mejoras.py
Variables opcionales: REPS (por defecto 5), WEAK_W (peso de etiquetas débiles, 0.5), N_TREES (400).
Tiempo aproximado: varios minutos por repetición.
Salida: results/fase5_1/
"""
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_quality as P4  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "clean")
OUT = os.path.join(ROOT, "results", "fase5_1")
os.makedirs(OUT, exist_ok=True)

FAM6 = ["fruity", "vegetal", "lactic", "floral", "toasted", "animal"]
PHYS = ["molecular_weight", "xlogp", "tpsa", "hbond_donors", "hbond_acceptors", "rotatable_bonds", "heavy_atoms"]
N_REP = int(os.environ.get("REPS", 5))
WEAK_W = float(os.environ.get("WEAK_W", 0.5))
N_TREES = int(os.environ.get("N_TREES", 400))
N_SPLIT, N_INNER, SEED = 5, 3, 2026
N_RANDOM = 200  # barajados por pliegue para la referencia de azar

RF_ACTUAL = dict(min_samples_leaf=2, max_features="sqrt")
RF_GRID = [RF_ACTUAL,
           dict(min_samples_leaf=5, max_features="sqrt"),
           dict(min_samples_leaf=5, max_features=0.2),
           dict(min_samples_leaf=10, max_features=0.2)]
LOG = []


def say(txt=""):
    print(txt, flush=True)
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
FP_COLS = [f"fp_{i}" for i in range(FP.shape[1])]
PH_COLS = list(PH.columns)
XDF = pd.concat([pd.DataFrame(FP, columns=FP_COLS), PH.reset_index(drop=True)], axis=1)
groups = pr.inchikey.fillna(pr.compound_id).str[:14].values

# ------------------------------------------------------------ pesos de entrenamiento (etiquetas débiles)
W = np.ones(Ym.shape)
if "flavornet_support" in ar.columns:
    sup = (ar[ar.aroma_family.isin(FAM6) & ar.compound_id.isin(compounds)]
           .groupby(["compound_id", "aroma_family"]).flavornet_support.apply(set))
    n_weak = 0
    for (c, f), vals in sup.items():
        if vals == {"sin_coincidencia"}:  # solo hay registros "sin coincidencia" para ese par
            W[compounds.index(c), FAM6.index(f)] = WEAK_W
            n_weak += 1
    say(f"Etiquetas débiles (solo 'sin_coincidencia' en Flavornet): {n_weak} positivos con peso {WEAK_W} "
        "al entrenar; en la prueba cuentan igual que todas.")
    say("   por familia: " + ", ".join(f"{f} {int((W[:, j] < 1).sum())}" for j, f in enumerate(FAM6)))
else:
    say("No existe la columna flavornet_support: los modelos 'con pesos' serán iguales a los normales.")


# ============================================================ modelos
def pre():
    return ColumnTransformer([("fp", VarianceThreshold(0.0), FP_COLS),
                              ("ph", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), PH_COLS)],
                             sparse_threshold=0)


def make(kind, cfg=None):
    if kind == "rf":
        clf = RandomForestClassifier(n_estimators=N_TREES, class_weight="balanced_subsample",
                                     random_state=0, n_jobs=-1, **cfg)
    else:
        clf = LogisticRegression(C=0.05, class_weight="balanced", max_iter=3000)
    return Pipeline([("pre", pre()), ("clf", clf)])


def fit_predict(kind, cfg, tr, te, y, w=None):
    m = make(kind, cfg)
    kw = {} if w is None else {"clf__sample_weight": w[tr]}
    m.fit(XDF.iloc[tr], y[tr], **kw)
    return m.predict_proba(XDF.iloc[te])[:, 1]


def inner_oof(kind, cfg, tr, y, w, seed):
    """Predicciones fuera de pliegue DENTRO del entrenamiento (para elegir configuración y umbral)."""
    out = np.zeros(len(tr))
    inner = GroupKFold(n_splits=N_INNER, shuffle=True, random_state=seed)
    for itr, ite in inner.split(XDF.iloc[tr], y[tr], groups[tr]):
        if y[tr][itr].sum() == 0:
            continue
        out[ite] = fit_predict(kind, cfg, tr[itr], tr[ite], y, w)
    return out


def best_threshold(y, p):
    best, thr = -1, 0.5
    for t in np.unique(np.round(p, 4)):
        f = f1_score(y, p >= t, zero_division=0)
        if f > best:
            best, thr = f, t
    return thr


def safe_ap(y, p):
    return average_precision_score(y, p) if 0 < y.sum() < len(y) else np.nan


MODELS = ["rf_actual", "reg_logistica", "rf_regularizado", "promedio_rf_lr",
          "rf_regularizado_pesos", "promedio_rf_lr_pesos"]

# ============================================================ validación cruzada
rows, chosen = [], []
POOL = {m: [] for m in MODELS}          # predicciones juntando pliegues, por repetición
THR = {m: [] for m in MODELS}           # umbrales, por repetición
RAND = []
t0 = time.time()
for rep in range(N_REP):
    gkf = GroupKFold(n_splits=N_SPLIT, shuffle=True, random_state=SEED + rep)
    P = {m: np.zeros(Ym.shape) for m in MODELS}
    T = {m: np.zeros(Ym.shape) for m in MODELS}
    rng = np.random.default_rng(SEED + rep)
    for k, (tr, te) in enumerate(gkf.split(XDF, Ym, groups)):
        iseed = SEED + rep * 10 + k + 100
        for j, f in enumerate(FAM6):
            y = Ym[:, j]
            w = W[:, j]
            ytr = y[tr]
            if ytr.sum() == 0:
                continue
            # --- elegir la configuración del RF con CV interna (sin pesos) ---
            inner = {i: inner_oof("rf", cfg, tr, y, None, iseed) for i, cfg in enumerate(RF_GRID)}
            scores = {i: safe_ap(ytr, p) for i, p in inner.items()}
            bi = max(scores, key=lambda i: -1 if np.isnan(scores[i]) else scores[i])
            chosen.append(dict(rep=rep, fold=k, family=f, config=str(RF_GRID[bi]), inner_auprc=scores[bi]))
            in_lr = inner_oof("lr", None, tr, y, None, iseed)
            in_rfw = inner_oof("rf", RF_GRID[bi], tr, y, w, iseed)
            in_lrw = inner_oof("lr", None, tr, y, w, iseed)
            inner_pred = {"rf_actual": inner[0], "reg_logistica": in_lr, "rf_regularizado": inner[bi],
                          "promedio_rf_lr": (inner[bi] + in_lr) / 2, "rf_regularizado_pesos": in_rfw,
                          "promedio_rf_lr_pesos": (in_rfw + in_lrw) / 2}
            # --- ajustar con todo el entrenamiento y predecir la prueba ---
            p_rf0 = fit_predict("rf", RF_ACTUAL, tr, te, y)
            p_lr = fit_predict("lr", None, tr, te, y)
            p_rfb = p_rf0 if bi == 0 else fit_predict("rf", RF_GRID[bi], tr, te, y)
            p_rfw = fit_predict("rf", RF_GRID[bi], tr, te, y, w)
            p_lrw = fit_predict("lr", None, tr, te, y, w)
            test_pred = {"rf_actual": p_rf0, "reg_logistica": p_lr, "rf_regularizado": p_rfb,
                         "promedio_rf_lr": (p_rfb + p_lr) / 2, "rf_regularizado_pesos": p_rfw,
                         "promedio_rf_lr_pesos": (p_rfw + p_lrw) / 2}
            yte = y[te]
            valid = 0 < yte.sum() < len(yte)
            if valid:  # referencia de azar en este pliegue: AUPRC de un orden aleatorio
                RAND.append(dict(rep=rep, fold=k, family=f, prev_test=yte.mean(),
                                 auprc_azar=np.mean([average_precision_score(yte, rng.random(len(yte)))
                                                     for _ in range(N_RANDOM)])))
            for m in MODELS:
                P[m][te, j] = test_pred[m]
                thr = best_threshold(ytr, inner_pred[m])
                T[m][te, j] = thr
                if valid:
                    rows.append(dict(model=m, rep=rep, fold=k, family=f, pos_test=int(yte.sum()),
                                     n_test=len(te), auprc=average_precision_score(yte, test_pred[m]),
                                     roc_auc=roc_auc_score(yte, test_pred[m]),
                                     f1=f1_score(yte, test_pred[m] >= thr, zero_division=0)))
    for m in MODELS:
        POOL[m].append(P[m])
        THR[m].append(T[m])
    say(f"repetición {rep + 1}/{N_REP} lista ({(time.time() - t0) / 60:.1f} min)")

fold = pd.DataFrame(rows)
rand = pd.DataFrame(RAND)
fold.to_csv(os.path.join(OUT, "metricas_por_pliegue.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(chosen).to_csv(os.path.join(OUT, "configuracion_rf_elegida.csv"), index=False, encoding="utf-8-sig")

# ============================================================ resúmenes
# macro por repetición (media de familias, con la métrica de cada familia promediada sobre sus pliegues)
per_rep_fam = fold.groupby(["model", "rep", "family"])[["auprc", "roc_auc", "f1"]].mean().reset_index()
per_rep = per_rep_fam.groupby(["model", "rep"])[["auprc", "roc_auc", "f1"]].mean().reset_index()

pooled_rows = []
for m in MODELS:
    for rep in range(N_REP):
        Pm, Tm = POOL[m][rep], THR[m][rep]
        ap = [average_precision_score(Ym[:, j], Pm[:, j]) for j in range(6)]
        f1 = [f1_score(Ym[:, j], Pm[:, j] >= Tm[:, j], zero_division=0) for j in range(6)]
        pooled_rows.append(dict(model=m, rep=rep, auprc_juntando=np.mean(ap), f1_juntando=np.mean(f1)))
pooled_df = pd.DataFrame(pooled_rows)

summ = (per_rep.groupby("model").agg(macro_auprc=("auprc", "mean"), macro_auprc_sd=("auprc", "std"),
                                     macro_roc_auc=("roc_auc", "mean"), macro_f1_por_pliegue=("f1", "mean"))
        .join(pooled_df.groupby("model").agg(macro_auprc_juntando=("auprc_juntando", "mean"),
                                             macro_f1_juntando=("f1_juntando", "mean")))
        .reindex(MODELS))
azar_fam = rand.groupby("family").auprc_azar.mean().reindex(FAM6)
prev_fam = Y.mean().reindex(FAM6)

say()
say("=" * 78)
say("RESULTADO MACRO (métrica por pliegue = la recomendada)")
say("=" * 78)
say(summ.round(3).to_string())
say(f"Referencias: prevalencia real (macro) = {prev_fam.mean():.3f}; azar por pliegue (orden aleatorio, macro) = "
    f"{azar_fam.mean():.3f}; ROC-AUC del azar = 0,500.")
summ.to_csv(os.path.join(OUT, "resumen_macro.csv"), encoding="utf-8-sig")

fam = per_rep_fam.groupby(["family", "model"]).auprc.agg(["mean", "std"]).reset_index()
fam_t = fam.pivot(index="family", columns="model", values="mean").reindex(index=FAM6, columns=MODELS)
fam_t.insert(0, "azar_por_pliegue", azar_fam)
fam_t.insert(0, "prevalencia", prev_fam)
say()
say("AUPRC por familia (media de repeticiones; métrica por pliegue)")
say(fam_t.round(3).to_string())
fam.to_csv(os.path.join(OUT, "auprc_por_familia.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------ comparación pareada con el RF actual
say()
say("=" * 78)
say("COMPARACIÓN PAREADA CON rf_actual (mismas particiones; diferencia de macro-AUPRC por repetición)")
say("=" * 78)
base = per_rep[per_rep.model == "rf_actual"].set_index("rep").auprc
cmp_rows = []
for m in MODELS[1:]:
    d = per_rep[per_rep.model == m].set_index("rep").auprc - base
    fam_d = (per_rep_fam[per_rep_fam.model == m].set_index(["rep", "family"]).auprc
             - per_rep_fam[per_rep_fam.model == "rf_actual"].set_index(["rep", "family"]).auprc
             ).groupby("family").mean().reindex(FAM6)
    cmp_rows.append(dict(modelo=m, diferencia_media=d.mean(), diferencia_sd=d.std(),
                         repeticiones_mejor=f"{int((d > 0).sum())}/{len(d)}",
                         **{f"dif_{f}": fam_d[f] for f in FAM6}))
cmp = pd.DataFrame(cmp_rows)
say(cmp.round(3).to_string(index=False))
cmp.to_csv(os.path.join(OUT, "comparacion_pareada.csv"), index=False, encoding="utf-8-sig")

ch = pd.DataFrame(chosen)
say()
say("Configuración del RF elegida por la CV interna (frecuencia por familia):")
say(ch.groupby(["family", "config"]).size().unstack(fill_value=0).to_string())

best_m = summ.macro_auprc.idxmax()
oof = np.mean(POOL[best_m], axis=0)
pd.concat([pd.DataFrame({"compound_id": compounds}),
           pd.DataFrame(oof, columns=[f"p_{f}" for f in FAM6]),
           pd.DataFrame(Ym, columns=[f"label_{f}" for f in FAM6])], axis=1).to_csv(
    os.path.join(OUT, f"predicciones_oof_{best_m}.csv"), index=False, encoding="utf-8-sig")

say()
say("=" * 78)
say("CÓMO LEERLO")
say("=" * 78)
say(f"- Mejor macro-AUPRC por pliegue: {best_m} ({summ.loc[best_m, 'macro_auprc']:.3f} ± "
    f"{summ.loc[best_m, 'macro_auprc_sd']:.3f}) frente a rf_actual ({summ.loc['rf_actual', 'macro_auprc']:.3f}).")
say("- Una mejora cuenta si la diferencia media es mayor que su DE y se repite en casi todas las repeticiones.")
say("- Los modelos '_pesos' solo cambian el entrenamiento; la prueba usa las mismas etiquetas que el resto.")
say("- Nada aquí se eligió mirando Flavornet: la validación externa queda para el modelo final.")
with open(os.path.join(OUT, "resumen_fase5_1.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG))
say(f"\nTodo guardado en {OUT}")
