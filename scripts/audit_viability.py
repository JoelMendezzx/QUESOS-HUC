"""
Auditoría de viabilidad predictiva sobre la base limpia (clean/).
Responde 5 preguntas y guarda las tablas de detalle en clean/auditoria/.

Uso: python scripts/audit_viability.py
"""
import os
import re
import unicodedata

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "clean")
OUT = os.path.join(C, "auditoria")
os.makedirs(OUT, exist_ok=True)


def R(p):
    return pd.read_csv(os.path.join(C, p), low_memory=False)


ml = R("modelo/ml_evidence_flat.csv")
pv = R("modelo/fact_process_effect.csv")
co = R("modelo/fact_compound_odor.csv")
ch = R("soporte/dim_cheese.csv")
src = R("soporte/dim_source.csv")
bes = R("soporte/bridge_evidence_source.csv")

PRIMARY_SRC = set(src.loc[src.source_type == "primary", "source_id"])


def fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def cited_keys(s):
    """Normaliza cada cita primaria a 'apellido año' (aprox.) para contar estudios distintos."""
    if not isinstance(s, str):
        return []
    keys = []
    for part in re.split(r"[;|]", s):
        p = fold(part).strip()
        p = re.sub(r"^(odor notes|notes)\s*:\s*", "", p)
        if p.startswith("ch."):
            continue
        m = re.match(r"^([a-z][a-z\-' ]*?)(?:,|\s+and\s|\s*&|\s+et al|\s*\()[^0-9]*?(\d{4})", p)
        if m:
            keys.append(f"{m.group(1).strip()} {m.group(2)}")
    return keys


def primary_studies(rows):
    """Estudios primarios distintos: fuentes de tipo 'primary' + fuentes primarias citadas."""
    keys = set()
    for _, r in rows.iterrows():
        for sid in str(r["source_ids"]).split("|"):
            if sid in PRIMARY_SRC:
                row = src[src.source_id == sid].iloc[0]
                keys.add(f"{fold(row.first_author)} {int(row.year)}")
        keys.update(cited_keys(r["cited_primary_source_raw"]))
    return keys


def known_ctx(df, p=""):
    milk = df[p + "milk_species_logic"].notna() & (df[p + "milk_species_logic"] != "unknown")
    heat = df[p + "milk_heat_treatment"].notna() & (df[p + "milk_heat_treatment"] != "unknown")
    cult = df[p + "rennet_culture_raw"].notna() & ~df[p + "rennet_culture_raw"].astype(str).str.startswith("not specified")
    ripe = (df[p + "ripening_days_min"].notna() | df[p + "ripening_days_max"].notna()
            | df[p + "ripening_label"].isin(["fresh", "aged", "long", "young"]))
    return milk, heat, cult, ripe


res = {}

# ---------------------------------------------------------------- Q1
spec = ch[ch.label_type == "specific"]
prof = spec[spec.has_profile]
milk, heat, cult, ripe = known_ctx(prof)
heat_exact = prof.milk_heat_treatment.isin(["raw", "pasteurized", "thermized"])
ripe_num = prof.ripening_days_min.notna() | prof.ripening_days_max.notna()
q1 = prof[["cheese_id", "cheese_name_std", "profile_completeness", "profile_from_label_only"]].copy()
q1["milk_known"], q1["heat_known"], q1["heat_unambiguous"] = milk, heat, heat_exact
q1["culture_known"], q1["ripening_known"], q1["ripening_numeric"] = cult, ripe, ripe_num
q1["all4_known"] = milk & heat & cult & ripe
q1["all4_strict"] = milk & heat_exact & cult & ripe_num
q1.sort_values(["profile_completeness", "cheese_name_std"], ascending=[False, True]).to_csv(
    os.path.join(OUT, "q1_completitud_quesos.csv"), index=False, encoding="utf-8-sig")
# v2: producción armonizada del tipo (spec_*), con valores verificados en pliegos
sp = spec.copy()
sp_m, sp_h = sp.spec_milk.notna(), sp.spec_heat_treatment.notna()
sp_c = sp.spec_coagulant_culture.notna()
sp_r = sp.spec_ripening_days_min.notna() | sp.spec_ripening_days_max.notna()
sp_hx = sp.spec_heat_treatment.isin(["raw", "pasteurized", "thermized"])
res["q1_v2"] = dict(milk=int(sp_m.sum()), heat=int(sp_h.sum()), heat_exact=int(sp_hx.sum()),
                    cult=int(sp_c.sum()), ripe=int(sp_r.sum()), all4=int((sp_m & sp_h & sp_c & sp_r).sum()),
                    strict=int((sp_m & sp_hx & sp_c & sp_r).sum()),
                    all4_names=sorted(sp.loc[sp_m & sp_h & sp_c & sp_r, "cheese_name_std"]))
sp[["cheese_id", "cheese_name_std", "cheese_family", "spec_milk", "spec_heat_treatment", "spec_coagulant_culture",
    "spec_ripening_days_min", "spec_ripening_days_max", "spec_completeness"]].sort_values(
    "spec_completeness", ascending=False).to_csv(os.path.join(OUT, "q1_completitud_quesos_v2.csv"),
                                                  index=False, encoding="utf-8-sig")
res["q1"] = dict(n_dim=len(ch), n_specific=len(spec), n_profile=len(prof),
                 milk=int(milk.sum()), heat=int(heat.sum()), heat_exact=int(heat_exact.sum()),
                 cult=int(cult.sum()), ripe=int(ripe.sum()), ripe_num=int(ripe_num.sum()),
                 all4=int(q1.all4_known.sum()), strict=int(q1.all4_strict.sum()),
                 all4_names=sorted(q1.loc[q1.all4_known, "cheese_name_std"]),
                 strict_names=sorted(q1.loc[q1.all4_strict, "cheese_name_std"]),
                 dist=prof.profile_completeness.value_counts().sort_index().to_dict())

# ---------------------------------------------------------------- Q2
lab = ml[ml.use_as_cheese_aroma_label & (ml.cheese_label_type == "specific")].copy()
lab["is_primary"] = lab.verification_status == "CONFIRMED_PRIMARY"
lab["is_gco"] = lab.method_hint_gc_olfactometry == True
levels = {
    "A_amplio": lab,
    "B_sin_doble_conteo": lab[~lab.possible_double_count],
    "C_GCO_o_primaria_sin_doble": lab[(lab.is_primary | lab.is_gco) & ~lab.possible_double_count],
    "D_primaria_confirmada": lab[lab.is_primary],
}
q2 = []
for k, d in levels.items():
    q2.append(dict(nivel=k, filas=len(d), quesos=d.cheese_id.nunique(),
                   pares_queso_descriptor=d[["cheese_id", "descriptor_id"]].drop_duplicates().shape[0],
                   descriptores=d.descriptor_id.nunique(), compuestos=d.compound_id.nunique()))
q2 = pd.DataFrame(q2)
q2.to_csv(os.path.join(OUT, "q2_etiquetas_medidas.csv"), index=False, encoding="utf-8-sig")
per_cheese = levels["C_GCO_o_primaria_sin_doble"].groupby("cheese_name_std").agg(
    pares=("descriptor_id", "nunique"), filas=("row_id", "count")).sort_values("pares", ascending=False)
per_cheese.to_csv(os.path.join(OUT, "q2_quesos_con_etiquetas_C.csv"), encoding="utf-8-sig")
res["q2"] = q2
res["q2_top"] = per_cheese.head(12)
res["q2_cheese_counts"] = levels["A_amplio"].groupby("cheese_name_std").descriptor_id.nunique()

# ---------------------------------------------------------------- Q3
all_ps = primary_studies(ml)
lab_ps = primary_studies(levels["A_amplio"])
labC_ps = primary_studies(levels["C_GCO_o_primaria_sin_doble"])
pv_ps = set()
for s in pv.cited_primary_source_raw.dropna():
    pv_ps.update(cited_keys(s))
pv_comp = pv[pv.compound_id.notna() & ~pv.is_reference_row & pv.ratio_vs_reference.notna()]
pv_comp_ps = set()
for s in pv_comp.cited_primary_source_raw.dropna():
    pv_comp_ps.update(cited_keys(s))
# concentración de la evidencia por estudio
cnt = {}
for _, r in levels["A_amplio"].iterrows():
    for k in primary_studies(pd.DataFrame([r])):
        cnt[k] = cnt.get(k, 0) + 1
top_studies = pd.Series(cnt).sort_values(ascending=False)
top_studies.rename("filas_etiqueta").to_csv(os.path.join(OUT, "q3_estudios_primarios.csv"),
                                            encoding="utf-8-sig")
no_primary = levels["A_amplio"].apply(lambda r: len(primary_studies(pd.DataFrame([r]))) == 0, axis=1).sum()
res["q3"] = dict(all=len(all_ps), lab=len(lab_ps), labC=len(labC_ps), pv=len(pv_ps),
                 pv_comp=len(pv_comp_ps), top=top_studies.head(10), n_lab=len(levels["A_amplio"]),
                 no_primary=int(no_primary),
                 n_src_primary=len(PRIMARY_SRC), n_src=len(src),
                 src_types=src.source_type.value_counts(dropna=False).to_dict())

# ---------------------------------------------------------------- Q4
def fam_table(d):
    rows = []
    for fam, g in d.groupby("aroma_family"):
        rows.append(dict(familia=fam, filas=len(g), quesos=g.cheese_id.nunique(),
                         descriptores=g.descriptor_id.nunique(), compuestos=g.compound_id.nunique(),
                         estudios_primarios=len(primary_studies(g)),
                         pct_primaria=round(100 * (g.verification_status == "CONFIRMED_PRIMARY").mean(), 1)))
    return pd.DataFrame(rows).sort_values(["estudios_primarios", "quesos", "filas"], ascending=False)


q4 = fam_table(levels["A_amplio"])
q4.to_csv(os.path.join(OUT, "q4_familias_aromaticas.csv"), index=False, encoding="utf-8-sig")
co_fam = co[co.is_aroma_target == True]
q4b = co_fam.groupby("aroma_family").agg(pares=("compound_id", "size"),
                                                   compuestos=("compound_id", "nunique")).sort_values(
    "compuestos", ascending=False)
q4b.to_csv(os.path.join(OUT, "q4_familias_compuesto_olor.csv"), encoding="utf-8-sig")
res["q4"], res["q4b"] = q4, q4b

# ---------------------------------------------------------------- Q5
lab5 = levels["A_amplio"].copy()
m, h, c_, r_ = known_ctx(lab5, "ctx_")
lab5["ctx_all4"] = m & h & c_ & r_
PROD_COLS = [c for c in ml.columns if c.startswith("ctx_") and not c.endswith("_raw")]
lab5["prod_vector"] = lab5[PROD_COLS].fillna("NA").astype(str).apply(lambda r: "|".join(r.tolist()), axis=1)
full = lab5[lab5.ctx_all4]
fullC = full[(full.is_primary | full.is_gco) & ~full.possible_double_count]
q5 = pd.DataFrame([
    dict(subconjunto="Etiquetas queso-descriptor (queso concreto)", filas=len(lab5),
         quesos=lab5.cheese_id.nunique(), vectores_produccion_distintos=lab5.prod_vector.nunique(),
         pares_queso_descriptor=lab5[["cheese_id", "descriptor_id"]].drop_duplicates().shape[0]),
    dict(subconjunto="... con los 4 bloques de producción conocidos", filas=len(full),
         quesos=full.cheese_id.nunique(), vectores_produccion_distintos=full.prod_vector.nunique(),
         pares_queso_descriptor=full[["cheese_id", "descriptor_id"]].drop_duplicates().shape[0]),
    dict(subconjunto="... y además GC-O/primaria sin doble conteo", filas=len(fullC),
         quesos=fullC.cheese_id.nunique(), vectores_produccion_distintos=fullC.prod_vector.nunique(),
         pares_queso_descriptor=fullC[["cheese_id", "descriptor_id"]].drop_duplicates().shape[0]),
])
SPEC = [c for c in ml.columns if c.startswith("cheese_spec_") and c != "cheese_spec_completeness"]
lab5["spec_vector"] = lab5[SPEC + ["cheese_cheese_family"]].fillna("NA").astype(str).apply(lambda r: "|".join(r.tolist()), axis=1)
full2 = lab5[lab5.cheese_spec_completeness == 1.0]
full2C = full2[(full2.is_primary | full2.is_gco) & ~full2.possible_double_count]
q5 = pd.concat([q5, pd.DataFrame([
    dict(subconjunto="v2: con los 4 bloques del TIPO de queso armonizados (spec_*)", filas=len(full2),
         quesos=full2.cheese_id.nunique(), vectores_produccion_distintos=full2.spec_vector.nunique(),
         pares_queso_descriptor=full2[["cheese_id", "descriptor_id"]].drop_duplicates().shape[0]),
    dict(subconjunto="v2: ... y además GC-O/primaria sin doble conteo", filas=len(full2C),
         quesos=full2C.cheese_id.nunique(), vectores_produccion_distintos=full2C.spec_vector.nunique(),
         pares_queso_descriptor=full2C[["cheese_id", "descriptor_id"]].drop_duplicates().shape[0]),
])], ignore_index=True)
res["q5_v2_cheeses"] = sorted(full2.cheese_name_std.unique())
q5.to_csv(os.path.join(OUT, "q5_produccion_aroma.csv"), index=False, encoding="utf-8-sig")
odor_cmp = set(co.compound_id)
pv_link = pv_comp[pv_comp.compound_id.isin(odor_cmp)]
res["q5"] = q5
res["q5_full_cheeses"] = sorted(full.cheese_name_std.unique())
res["q5_pv"] = dict(rows=len(pv), comp=len(pv_comp), link=len(pv_link),
                    link_cmp=pv_link.compound_id.nunique(), link_fac=pv_link.factor_category.nunique(),
                    link_ps=len(set(k for s in pv_link.cited_primary_source_raw.dropna() for k in cited_keys(s))),
                    link_cheese=pv_link.cheese_id.nunique(),
                    fac=pv_link.factor_category.value_counts().head(8).to_dict(),
                    fam=pv[~pv.is_reference_row & pv.ratio_vs_reference.notna()].shape[0])

# ---------------------------------------------------------------- impresión
pd.set_option("display.width", 200)
for k, v in res.items():
    print(f"\n===== {k}")
    print(v)
