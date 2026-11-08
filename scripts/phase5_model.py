"""
Fase 5 — Modelo compuesto -> familia aromática (6 familias de Bérodier).

Entrada : clean/modelo/fact_compound_odor.csv, clean/modelo/compound_properties.csv,
          clean/soporte/dim_compound.csv, data_external/ (Flavornet + PubChem para validación externa)
Salida  : results/fase5/ (tablas, predicciones, métricas, gráficos y modelos entrenados)

Diseño:
- Etiqueta (compuesto, familia) = 1 si la base registra algún descriptor de esa familia para el
  compuesto; 0 = DESCONOCIDO (no hay negativos explícitos en la fuente). Las métricas se interpretan
  como aprendizaje positivo-no etiquetado (PU): el AUPRC observado es una cota inferior.
- Validación: GroupKFold (5 pliegues, 10 repeticiones) agrupando por esqueleto InChIKey
  (los estereoisómeros nunca quedan repartidos entre entrenamiento y prueba).
- Modelos: prevalencia, clase química (línea base), regresión logística L2 y Random Forest.
- Umbral de decisión elegido dentro del entrenamiento (CV interna), nunca con el pliegue de prueba.
- Prueba de permutación y validación externa con compuestos de Flavornet no presentes en la base.

Uso: python scripts/phase5_model.py
"""
import json
import os
import pickle
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupKFold

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_quality as P4  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "clean")
OUT = os.path.join(ROOT, "results", "fase5")
os.makedirs(os.path.join(OUT, "models"), exist_ok=True)
FAM6 = ["fruity", "vegetal", "lactic", "floral", "toasted", "animal"]
N_REP, N_SPLIT, N_PERM = 10, 5, 50
SEED = 2026

fo = pd.read_csv(os.path.join(C, "modelo", "fact_compound_odor.csv"))
props = pd.read_csv(os.path.join(C, "modelo", "compound_properties.csv"))
dc = pd.read_csv(os.path.join(C, "soporte", "dim_compound.csv"))

# ---------------------------------------------------------------- etiquetas
ar = fo[fo.is_aroma_target == True]
hq = ar[(ar.max_evidence_score >= 0.6) & (~ar.all_possible_double_count)]   # sensibilidad: etiquetas de mayor calidad


def label_matrix(pairs, compounds):
    y = pd.DataFrame(0, index=compounds, columns=FAM6)
    for c, f in zip(pairs.compound_id, pairs.aroma_family):
        if f in FAM6 and c in y.index:
            y.loc[c, f] = 1
    return y


compounds = sorted(set(ar.compound_id) & set(props.compound_id))
Y = label_matrix(ar, compounds)
Y_hq = label_matrix(hq, compounds)

# estado de cada celda (para documentar): positivo / desconocido
lab_long = Y.stack().rename("label").reset_index().rename(columns={"level_0": "compound_id", "level_1": "family"})
lab_long["estado_etiqueta"] = np.where(lab_long.label == 1, "positivo", "desconocido (sin negativo explícito)")

# ---------------------------------------------------------------- variables
PHYS = ["molecular_weight", "xlogp", "tpsa", "hbond_donors", "hbond_acceptors", "rotatable_bonds", "heavy_atoms"]


def features(pr):
    fp = np.array([P4.fingerprint_bits(b) or [0] * 881 for b in pr.fingerprint2d_b64])
    ph = pr[PHYS].astype(float).copy()
    ph["xlogp_missing"] = ph.xlogp.isna().astype(float)
    return fp, ph


pr = props.set_index("compound_id").loc[compounds].reset_index()
FP, PH = features(pr)
keep_bits = FP.std(axis=0) > 0
PH_MED = PH.median()
X_fp = FP[:, keep_bits]
X_ph = PH.fillna(PH_MED).values
PH_MU, PH_SD = X_ph.mean(0), X_ph.std(0) + 1e-9
X = np.hstack([X_fp, (X_ph - PH_MU) / PH_SD])
groups = pr.inchikey.fillna(pr.compound_id).str[:14].values
chem = dc.set_index("compound_id").chemical_class.reindex(compounds).fillna("sin_clase").values

# ---------------------------------------------------------------- modelos
def m_prevalence(Xtr, ytr, Xte, ctr, cte):
    return np.tile(ytr.mean(0), (len(Xte), 1))


def m_chemclass(Xtr, ytr, Xte, ctr, cte):
    out = np.zeros((len(Xte), ytr.shape[1]))
    glob = (ytr.sum(0) + 1) / (len(ytr) + 2)
    for k, cl in enumerate(cte):
        m = ctr == cl
        out[k] = (ytr[m].sum(0) + 2 * glob) / (m.sum() + 2) if m.any() else glob
    return out


def m_logreg(Xtr, ytr, Xte, ctr, cte, C_=0.05):
    out = np.zeros((len(Xte), ytr.shape[1]))
    for j in range(ytr.shape[1]):
        if ytr[:, j].sum() == 0:
            continue
        clf = LogisticRegression(C=C_, class_weight="balanced", max_iter=3000)
        clf.fit(Xtr, ytr[:, j])
        out[:, j] = clf.predict_proba(Xte)[:, 1]
    return out


def m_rf(Xtr, ytr, Xte, ctr, cte, seed=0):
    out = np.zeros((len(Xte), ytr.shape[1]))
    for j in range(ytr.shape[1]):
        if ytr[:, j].sum() == 0:
            continue
        clf = RandomForestClassifier(n_estimators=400, min_samples_leaf=2, max_features="sqrt",
                                     class_weight="balanced_subsample", random_state=seed, n_jobs=-1)
        clf.fit(Xtr, ytr[:, j])
        out[:, j] = clf.predict_proba(Xte)[:, 1]
    return out


MODELS = {"prevalencia": m_prevalence, "clase_quimica": m_chemclass, "reg_logistica": m_logreg,
          "random_forest": m_rf}


def best_threshold(y, p):
    best, thr = -1, 0.5
    for t in np.unique(np.round(p, 4)):
        f = f1_score(y, p >= t, zero_division=0)
        if f > best:
            best, thr = f, t
    return thr


def cv_eval(Xm, Ym, model, reps=N_REP, seed=SEED, thresholds=True):
    """Devuelve métricas por repetición/familia y predicciones fuera de pliegue (media)."""
    rows, oof_sum, oof_n = [], np.zeros(Ym.shape), np.zeros(Ym.shape)
    for rep in range(reps):
        gkf = GroupKFold(n_splits=N_SPLIT, shuffle=True, random_state=seed + rep)
        P = np.zeros(Ym.shape)
        T = np.zeros(Ym.shape)
        for tr, te in gkf.split(Xm, Ym, groups):
            P[te] = model(Xm[tr], Ym[tr], Xm[te], chem[tr], chem[te])
            if thresholds:  # umbral elegido con CV interna sobre el entrenamiento
                inner = GroupKFold(n_splits=3, shuffle=True, random_state=seed + rep + 100)
                Pin = np.zeros((len(tr), Ym.shape[1]))
                for itr, ite in inner.split(Xm[tr], Ym[tr], groups[tr]):
                    Pin[ite] = model(Xm[tr][itr], Ym[tr][itr], Xm[tr][ite], chem[tr][itr], chem[tr][ite])
                for j in range(Ym.shape[1]):
                    T[te, j] = best_threshold(Ym[tr][:, j], Pin[:, j])
        oof_sum += P
        oof_n += 1
        for j, f in enumerate(FAM6):
            y = Ym[:, j]
            if y.sum() == 0 or y.sum() == len(y):
                continue
            rows.append(dict(rep=rep, family=f, n_pos=int(y.sum()), prevalence=y.mean(),
                             auprc=average_precision_score(y, P[:, j]),
                             roc_auc=roc_auc_score(y, P[:, j]),
                             f1=f1_score(y, P[:, j] >= T[:, j], zero_division=0) if thresholds else np.nan))
    return pd.DataFrame(rows), oof_sum / oof_n


# ---------------------------------------------------------------- evaluación principal
Ym = Y.values
results, oof = [], {}
for name, fn in MODELS.items():
    print("CV", name)
    r, o = cv_eval(X, Ym, fn)
    r["model"] = name
    results.append(r)
    oof[name] = o
res = pd.concat(results)
summary = res.groupby(["model", "family"]).agg(n_pos=("n_pos", "first"), prevalence=("prevalence", "first"),
                                               auprc_mean=("auprc", "mean"), auprc_sd=("auprc", "std"),
                                               roc_auc_mean=("roc_auc", "mean"), f1_mean=("f1", "mean")).reset_index()
macro = res.groupby(["model", "rep"]).agg(auprc=("auprc", "mean"), roc_auc=("roc_auc", "mean"), f1=("f1", "mean"))
macro_sum = macro.groupby("model").agg(macro_auprc=("auprc", "mean"), macro_auprc_sd=("auprc", "std"),
                                       macro_roc_auc=("roc_auc", "mean"), macro_f1=("f1", "mean"),
                                       macro_f1_sd=("f1", "std")).reset_index()
summary.to_csv(os.path.join(OUT, "metricas_por_familia.csv"), index=False, encoding="utf-8-sig")
macro_sum.to_csv(os.path.join(OUT, "metricas_macro.csv"), index=False, encoding="utf-8-sig")
res.to_csv(os.path.join(OUT, "metricas_por_repeticion.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- sensibilidad: etiquetas de mayor calidad
sens = []
for name in ["clase_quimica", "reg_logistica", "random_forest"]:
    r, _ = cv_eval(X, Y_hq.values, MODELS[name], reps=5, thresholds=False)
    r["model"] = name
    sens.append(r)
sens = pd.concat(sens).groupby(["model", "family"]).agg(n_pos=("n_pos", "first"), prevalence=("prevalence", "first"),
                                                        auprc_mean=("auprc", "mean")).reset_index()
sens.to_csv(os.path.join(OUT, "sensibilidad_etiquetas_alta_calidad.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- prueba de permutación (¿mejor que el azar?)
rng = np.random.default_rng(SEED)
perm = []
obs = {m: res[res.model == m].query("rep == 0").auprc.mean() for m in ["reg_logistica", "random_forest"]}
for k in range(N_PERM):
    idx = rng.permutation(len(Ym))
    for m in ["reg_logistica", "random_forest"]:
        r, _ = cv_eval(X, Ym[idx], MODELS[m], reps=1, seed=SEED, thresholds=False)
        perm.append(dict(perm=k, model=m, macro_auprc=r.auprc.mean()))
perm = pd.DataFrame(perm)
perm_sum = perm.groupby("model").macro_auprc.agg(["mean", "std", "max"]).reset_index()
perm_sum["observed_rep0"] = perm_sum.model.map(obs)
perm_sum["p_value"] = [((perm[perm.model == m].macro_auprc >= obs[m]).sum() + 1) / (N_PERM + 1)
                       for m in perm_sum.model]
perm_sum.to_csv(os.path.join(OUT, "prueba_permutacion.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- predicciones fuera de pliegue y errores
pred = pd.DataFrame({"compound_id": compounds})
pred = pred.merge(dc[["compound_id", "iupac_name", "cas_final", "chemical_class"]], on="compound_id", how="left")
for m in ["clase_quimica", "reg_logistica", "random_forest"]:
    for j, f in enumerate(FAM6):
        pred[f"p_{m}_{f}"] = oof[m][:, j]
for f in FAM6:
    pred[f"label_{f}"] = Y[f].values
pred.to_csv(os.path.join(OUT, "predicciones_oof.csv"), index=False, encoding="utf-8-sig")
err = []
for f in FAM6:
    p = pred[f"p_random_forest_{f}"]
    fn_ = pred[(pred[f"label_{f}"] == 1)].assign(p=p).nsmallest(5, "p")
    fp_ = pred[(pred[f"label_{f}"] == 0)].assign(p=p).nlargest(5, "p")
    for kind, df in [("falso_negativo (etiquetado, prob. baja)", fn_), ("posible_falso_positivo (no etiquetado, prob. alta)", fp_)]:
        for r in df.itertuples():
            err.append(dict(family=f, tipo=kind, compound_id=r.compound_id, iupac_name=r.iupac_name,
                            chemical_class=r.chemical_class, prob_rf=round(r.p, 3)))
pd.DataFrame(err).to_csv(os.path.join(OUT, "analisis_errores.csv"), index=False, encoding="utf-8-sig")
by_class = []
for cl, g in pred.groupby("chemical_class", dropna=False):
    for f in FAM6:
        y = g[f"label_{f}"]
        if 0 < y.sum() < len(y):
            by_class.append(dict(chemical_class=cl, family=f, n=len(g), n_pos=int(y.sum()),
                                 auprc_rf=average_precision_score(y, g[f"p_random_forest_{f}"])))
pd.DataFrame(by_class).to_csv(os.path.join(OUT, "rendimiento_por_clase_quimica.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- concordancia con Flavornet (compuestos de la base)
fn = P4.load_flavornet()
cas = dc.set_index("compound_id").cas_final


def flav_labels(cas_list):
    out = []
    for c in cas_list:
        fams = {P4.FN_FAMILY[o][0] for o in fn.get(c, set()) if o in P4.FN_FAMILY}
        out.append([1 if f in fams else 0 for f in FAM6])
    return np.array(out)


in_fn = np.array([cas.get(c) in fn for c in compounds])
YF = flav_labels([cas.get(c) for c in compounds])
agree = []
for j, f in enumerate(FAM6):
    yf = YF[in_fn, j]
    ye = Ym[in_fn, j]
    if 0 < yf.sum() < len(yf):
        agree.append(dict(family=f, n_compuestos=int(in_fn.sum()), positivos_flavornet=int(yf.sum()),
                          positivos_base=int(ye.sum()), ambos=int((yf & ye).sum()),
                          auprc_rf_vs_flavornet=average_precision_score(yf, oof["random_forest"][in_fn, j]),
                          auprc_lr_vs_flavornet=average_precision_score(yf, oof["reg_logistica"][in_fn, j]),
                          prevalencia_flavornet=yf.mean()))
pd.DataFrame(agree).to_csv(os.path.join(OUT, "concordancia_flavornet_compuestos_base.csv"), index=False,
                           encoding="utf-8-sig")

# ---------------------------------------------------------------- modelos finales + validación externa
final = {}
for m, fnm in [("reg_logistica", m_logreg), ("random_forest", m_rf)]:
    models_m = []
    for j, f in enumerate(FAM6):
        clf = (LogisticRegression(C=0.05, class_weight="balanced", max_iter=3000) if m == "reg_logistica" else
               RandomForestClassifier(n_estimators=400, min_samples_leaf=2, max_features="sqrt",
                                      class_weight="balanced_subsample", random_state=0, n_jobs=-1))
        clf.fit(X, Ym[:, j])
        models_m.append(clf)
    final[m] = models_m
    with open(os.path.join(OUT, "models", f"{m}.pkl"), "wb") as fh:
        pickle.dump(dict(models=models_m, families=FAM6, keep_bits=keep_bits.tolist(), phys=PHYS,
                         phys_median=PH_MED.to_dict(), phys_mu=PH_MU.tolist(), phys_sd=PH_SD.tolist(),
                         note="Entrenado con todas las etiquetas de la base v3; ver FASE5_Modelo_Compuesto_Aroma.md"), fh)

ext_rows = []
pc_dir = os.path.join(ROOT, "data_external", "pubchem")
known_cas = set(dc.cas_final.dropna())
known_ik = set(props.inchikey.dropna().str[:14])
for c in sorted(fn):
    if c in known_cas:
        continue
    d = P4._json(os.path.join(pc_dir, f"cas_{P4._safe(c)}.json"))
    ids = (d or {}).get("IdentifierList", {}).get("CID", [])
    if not ids:
        continue
    pp = P4._json(os.path.join(pc_dir, f"prop_{ids[0]}.json"))
    p = ((pp or {}).get("PropertyTable", {}).get("Properties") or [{}])[0]
    if not p.get("Fingerprint2D") or (p.get("InChIKey", "")[:14] in known_ik):
        continue
    fams = {P4.FN_FAMILY[o][0] for o in fn[c] if o in P4.FN_FAMILY}
    row = dict(cas=c, pubchem_cid=ids[0], flavornet_odors="; ".join(sorted(fn[c])), inchikey=p.get("InChIKey"),
               fingerprint2d_b64=p.get("Fingerprint2D"))
    for k in PHYS:
        key = {"molecular_weight": "MolecularWeight", "xlogp": "XLogP", "tpsa": "TPSA",
               "hbond_donors": "HBondDonorCount", "hbond_acceptors": "HBondAcceptorCount",
               "rotatable_bonds": "RotatableBondCount", "heavy_atoms": "HeavyAtomCount"}[k]
        row[k] = p.get(key)
    for f in FAM6:
        row[f"flavornet_{f}"] = int(f in fams)
    row["has_mapped_family"] = bool(fams)
    ext_rows.append(row)
ext = pd.DataFrame(ext_rows)
ext_metrics = []
if len(ext):
    ext = ext[ext.has_mapped_family].reset_index(drop=True)
    efp, eph = features(ext)
    Xe = np.hstack([efp[:, keep_bits], ((eph.fillna(PH_MED).values) - PH_MU) / PH_SD])
    Pe = {"clase_quimica": None}
    for m in ["reg_logistica", "random_forest"]:
        Pm = np.column_stack([mdl.predict_proba(Xe)[:, 1] for mdl in final[m]])
        for j, f in enumerate(FAM6):
            ext[f"p_{m}_{f}"] = Pm[:, j]
            y = ext[f"flavornet_{f}"].values
            if 0 < y.sum() < len(y):
                ext_metrics.append(dict(model=m, family=f, n=len(y), n_pos=int(y.sum()), prevalence=y.mean(),
                                        auprc=average_precision_score(y, Pm[:, j]), roc_auc=roc_auc_score(y, Pm[:, j])))
    ext.drop(columns=["fingerprint2d_b64"]).to_csv(os.path.join(OUT, "validacion_externa_flavornet_predicciones.csv"),
                                                   index=False, encoding="utf-8-sig")
ext_m = pd.DataFrame(ext_metrics)
ext_m.to_csv(os.path.join(OUT, "validacion_externa_flavornet_metricas.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- tablas de datos y gráficos
lab_long.to_csv(os.path.join(OUT, "etiquetas_compuesto_familia.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(dict(compound_id=compounds, group_inchikey14=groups, chemical_class=chem)).to_csv(
    os.path.join(OUT, "dataset_compuestos.csv"), index=False, encoding="utf-8-sig")

fig, ax = plt.subplots(figsize=(9, 4.5))
order = ["prevalencia", "clase_quimica", "reg_logistica", "random_forest"]
colors = {"prevalencia": "#bdbdbd", "clase_quimica": "#8c8c8c", "reg_logistica": "#3b7dd8", "random_forest": "#1b9e77"}
w = 0.2
for k, m in enumerate(order):
    s = summary[summary.model == m].set_index("family").reindex(FAM6)
    ax.bar(np.arange(6) + (k - 1.5) * w, s.auprc_mean, w, yerr=s.auprc_sd, label=m, color=colors[m], capsize=2)
ax.set_xticks(range(6))
ax.set_xticklabels(FAM6)
ax.set_ylabel("AUPRC (CV agrupada, 10 rep.)")
ax.set_title("Compuesto → familia aromática: AUPRC por familia")
ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
fig.tight_layout()
fig.savefig(os.path.join(OUT, "auprc_por_familia.png"), dpi=150)

fig, ax = plt.subplots(figsize=(6, 4))
for m in ["reg_logistica", "random_forest"]:
    ax.hist(perm[perm.model == m].macro_auprc, bins=15, alpha=0.6, label=f"{m} (permutado)", color=colors[m])
    ax.axvline(obs[m], color=colors[m], linestyle="--", label=f"{m} observado")
ax.set_xlabel("macro-AUPRC")
ax.set_title("Prueba de permutación (50 permutaciones)")
ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "prueba_permutacion.png"), dpi=150)

info = dict(n_compuestos=len(compounds), n_grupos_estructura=int(len(set(groups))),
            positivos_por_familia=Y.sum().to_dict(), positivos_alta_calidad=Y_hq.sum().to_dict(),
            n_bits_fingerprint=int(keep_bits.sum()), n_variables_fisicoquimicas=len(PHYS) + 1,
            n_externos=int(len(ext)), repeticiones=N_REP, pliegues=N_SPLIT, permutaciones=N_PERM)
json.dump(info, open(os.path.join(OUT, "resumen_dataset.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(info, ensure_ascii=False))
print(macro_sum.to_string())
print(summary.to_string())
print(perm_sum.to_string())
print(ext_m.to_string())
