"""
Genera las plantillas de revisión experta (Fases 1–3 del plan) en corrections/.

- Todo lo que propone el script va en columnas 'propuesta_*' y con estado = 'propuesta'.
- Las columnas para el revisor están vacías (en amarillo).
- NO sobrescribe una plantilla que ya existe (para no borrar trabajo de revisión).
  Para regenerar desde cero: python scripts/make_correction_templates.py --force

Uso: python scripts/make_correction_templates.py
"""
import os
import sys

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "clean")
OUT = os.path.join(ROOT, "corrections")
os.makedirs(OUT, exist_ok=True)
FORCE = "--force" in sys.argv


def R(p):
    return pd.read_csv(os.path.join(C, p), low_memory=False)


ml = R("modelo/ml_evidence_flat.csv")
pv = R("modelo/fact_process_effect.csv")
ch = R("soporte/dim_cheese.csv")
alias = R("soporte/cheese_alias.csv")
bec = R("soporte/bridge_evidence_cheese.csv")
dd = R("soporte/dim_descriptor.csv")
dterm = R("soporte/descriptor_term.csv")
dfam = R("soporte/descriptor_family.csv")

# etiquetas queso-descriptor (nivel A) y fuertes (nivel C de la auditoría)
lab = ml[ml.use_as_cheese_descriptor_label & (ml.cheese_label_type == "specific")]
strong = lab[(~lab.possible_double_count) &
             ((lab.verification_status == "CONFIRMED_PRIMARY") | (lab.method_hint_gc_olfactometry == True))]
n_lab = lab.groupby("cheese_id").descriptor_id.nunique()
n_strong = strong.groupby("cheese_id").descriptor_id.nunique()

HDR_FILL = PatternFill("solid", fgColor="DDE6F0")
REV_FILL = PatternFill("solid", fgColor="FFF4C2")


def save(df, name, review_cols, validations, widths=None):
    path = os.path.join(OUT, name)
    if os.path.exists(path) and not FORCE:
        print(f"  {name}: YA EXISTE, no se sobrescribe (usa --force para regenerar)")
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "revision"
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append([None if (isinstance(v, float) and pd.isna(v)) else v for v in row])
    for j, col in enumerate(df.columns, start=1):
        cell = ws.cell(row=1, column=j)
        cell.font = Font(bold=True)
        cell.fill = REV_FILL if col in review_cols else HDR_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(col, min(max(len(col) + 2, 12), 40))
        if col in review_cols:
            for i in range(2, len(df) + 2):
                ws.cell(row=i, column=j).fill = REV_FILL
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions
    for col, options in validations.items():
        j = list(df.columns).index(col) + 1
        letter = get_column_letter(j)
        dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
        dv.add(f"{letter}2:{letter}{len(df) + 1}")
        ws.add_data_validation(dv)
    wb.save(path)
    print(f"  {name:45s} {len(df):>4} filas")


REVIEW = ["revisado_por", "fecha_revision", "notas"]

# ----------------------------------------------------------------------------
# FASE 1.1 — equivalencias de nombres de queso
# ----------------------------------------------------------------------------
uses = bec.cheese_label_raw.value_counts().add(pv.cheese_label_raw.value_counts(), fill_value=0)
f11 = alias.copy()
f11["n_filas_en_datos"] = f11.cheese_label_raw.map(uses).fillna(0).astype(int)
f11 = f11.rename(columns={"cheese_name_std": "propuesta_cheese_name_std",
                          "sample_qualifier": "propuesta_sample_qualifier",
                          "label_type": "propuesta_label_type"})
f11["estado"] = "propuesta"
for c in ["decision", "corregido_cheese_name_std", "corregido_label_type", "fuente_correccion"] + REVIEW:
    f11[c] = None
f11 = f11[["cheese_label_raw", "n_filas_en_datos", "cheese_id", "propuesta_cheese_name_std",
           "propuesta_sample_qualifier", "propuesta_label_type", "estado", "decision",
           "corregido_cheese_name_std", "corregido_label_type", "fuente_correccion"] + REVIEW]
f11 = f11.sort_values(["n_filas_en_datos", "cheese_label_raw"], ascending=[False, True])
LABEL_TYPES = ["specific", "generic_category", "multi_cheese", "not_cheese", "unresolved"]
save(f11, "fase1_quesos_equivalencias.xlsx",
     ["decision", "corregido_cheese_name_std", "corregido_label_type", "fuente_correccion"] + REVIEW,
     {"decision": ["OK", "CAMBIAR", "DUDA"], "corregido_label_type": LABEL_TYPES},
     {"cheese_label_raw": 45, "propuesta_cheese_name_std": 35, "notas": 40})

# ----------------------------------------------------------------------------
# FASE 1.4–1.5 — familia tecnológica, país y DOP
# Propuesta SOLO a partir de indicadores que ya están en el perfil del queso.
# ----------------------------------------------------------------------------
FAMILIES = ["fresh_acid_lactic", "fresh_rennet", "pasta_filata", "brined", "soft_bloomy_rind",
            "washed_rind_smear", "blue", "semi_hard", "hard_cooked", "grana_extra_hard",
            "swiss_type_eyes", "goat_lactic", "other"]
RULES = [  # (columna del perfil, valor, familia propuesta, base)
    ("mold_p_roqueforti", 1, "blue", "perfil: P. roqueforti"),
    ("mold_p_camemberti", 1, "soft_bloomy_rind", "perfil: P. camemberti"),
    ("flora_washed_rind_smear", 1, "washed_rind_smear", "perfil: flora de corteza lavada"),
    ("proc_pasta_filata", 1, "pasta_filata", "perfil: pasta filata"),
    ("proc_brine", 1, "brined", "perfil: salmuera"),
    ("cult_propionibacteria", 1, "swiss_type_eyes", "perfil: bacterias propiónicas"),
    ("cult_natural_whey", 1, "grana_extra_hard", "perfil: suero-cultivo natural"),
    ("coag_lactic_acid", 1, "fresh_acid_lactic", "perfil: coagulación láctica"),
    ("proc_acid_coagulation", 1, "fresh_acid_lactic", "perfil: coagulación ácida"),
    ("proc_cooked_or_scalded", 1, "hard_cooked", "perfil: cuajada cocida/escaldada"),
]
rows = []
for _, r in ch[ch.label_type == "specific"].iterrows():
    cands, basis = [], []
    for col, val, fam, why in RULES:
        if col in ch.columns and r.get(col) == val:
            cands.append(fam)
            basis.append(why)
    if r.get("ripening_class") == "fresh" and not cands:
        cands.append("fresh_rennet | fresh_acid_lactic")
        basis.append("perfil: maduración 'fresh'")
    cands = list(dict.fromkeys(cands))
    joined = " | ".join(cands)
    rows.append(dict(
        cheese_id=r.cheese_id, cheese_name_std=r.cheese_name_std,
        n_etiquetas_aroma=int(n_lab.get(r.cheese_id, 0)), n_etiquetas_fuertes=int(n_strong.get(r.cheese_id, 0)),
        tiene_perfil=bool(r.has_profile),
        propuesta_cheese_family=joined or None,
        base_de_la_propuesta="; ".join(basis) if basis else "sin indicadores en el perfil: decidir con fuente",
        estado=("propuesta_ambigua" if "|" in joined else "propuesta") if cands else "sin_propuesta",
        decision=None, cheese_family_final=None, fuente_familia=None,
        pais_iso=None, pdo_pgi=None, fuente_pais_dop=None,
        revisado_por=None, fecha_revision=None, notas=None))
f14 = pd.DataFrame(rows).sort_values(["n_etiquetas_fuertes", "n_etiquetas_aroma", "cheese_name_std"],
                                     ascending=[False, False, True])
save(f14, "fase1_quesos_familia_tecnologica.xlsx",
     ["decision", "cheese_family_final", "fuente_familia", "pais_iso", "pdo_pgi", "fuente_pais_dop"] + REVIEW,
     {"decision": ["OK", "CAMBIAR", "DUDA"], "cheese_family_final": FAMILIES,
      "pdo_pgi": ["PDO", "PGI", "TSG", "none", "unknown"]},
     {"cheese_name_std": 28, "propuesta_cheese_family": 30, "base_de_la_propuesta": 45, "notas": 40})

# ----------------------------------------------------------------------------
# FASE 2 — valores de producción (4 bloques) para los quesos con etiquetas de aroma
# ----------------------------------------------------------------------------
def status_block(r, block):
    if block == "leche":
        raw, std = r.get("milk_species_raw"), r.get("milk_species_logic")
        ok = isinstance(std, str) and std != "unknown"
        amb = std in ("alternatives", "mixture_or_alternatives")
    elif block == "tratamiento_termico":
        raw, std = r.get("milk_heat_treatment_raw"), r.get("milk_heat_treatment")
        ok = isinstance(std, str) and std != "unknown"
        amb = std in ("raw_or_pasteurized", "raw_or_thermized", "comparison", "other")
    elif block == "cuajo_cultivo":
        raw = r.get("rennet_culture_raw")
        std = raw
        ok = isinstance(raw, str) and not raw.startswith("not specified")
        amb = False
    else:  # maduracion
        raw = r.get("ripening_raw")
        mn, mx, lb = r.get("ripening_days_min"), r.get("ripening_days_max"), r.get("ripening_label")
        std = None if pd.isna(mn) and pd.isna(mx) else f"{'' if pd.isna(mn) else int(mn)}–{'' if pd.isna(mx) else int(mx)} d"
        ok = std is not None or lb in ("fresh", "aged", "long", "young")
        amb = ok and (pd.isna(mn) or pd.isna(mx))
    estado = "desconocido" if not ok else ("ambiguo" if amb else "conocido")
    return (None if isinstance(raw, float) else raw), (None if isinstance(std, float) else std), estado


chx = ch.set_index("cheese_id")
targets = sorted(n_lab.index, key=lambda c: (-n_strong.get(c, 0), -n_lab.get(c, 0)))
rows = []
for prio, cid in enumerate(targets, start=1):
    r = chx.loc[cid].to_dict()
    for block, unit in [("leche", "especie(s) y proporción si se conoce"),
                        ("tratamiento_termico", "raw / thermized / pasteurized"),
                        ("cuajo_cultivo", "coagulante; cultivos; mohos/flora"),
                        ("maduracion", "días (mínimo–máximo)")]:
        raw, std, estado = status_block(r, block)
        rows.append(dict(prioridad=prio, cheese_id=cid, cheese_name_std=r["cheese_name_std"],
                         n_etiquetas_fuertes=int(n_strong.get(cid, 0)), bloque=block,
                         valor_actual_texto=raw, valor_actual_normalizado=std, estado_actual=estado,
                         completar="sí" if estado != "conocido" else "no (solo verificar)",
                         valor_nuevo=None, unidad_o_formato=unit, value_scope=None,
                         fuente=None, pagina=None, revisado_por=None, fecha_revision=None, notas=None))
f2 = pd.DataFrame(rows)
save(f2, "fase2_produccion_valores.xlsx",
     ["valor_nuevo", "value_scope", "fuente", "pagina"] + REVIEW,
     {"value_scope": ["type_specification", "sample"]},
     {"cheese_name_std": 26, "valor_actual_texto": 40, "unidad_o_formato": 32, "fuente": 30, "notas": 40})

# ----------------------------------------------------------------------------
# FASE 3 — mapeo de descriptores de aroma (doble revisión para kappa)
# ----------------------------------------------------------------------------
aroma = dd[dd.in_odor_aroma].copy()
terms = dterm.groupby("descriptor_id").term.agg(lambda s: " | ".join(s))
fams = dfam.sort_values("order_in_source").groupby("descriptor_id").family_token.agg(lambda s: " | ".join(s))
n_rows = ml[ml.use_as_compound_odor_label | ml.use_as_cheese_descriptor_label].groupby("descriptor_id").row_id.count()
n_cmp = ml[ml.use_as_compound_odor_label].groupby("descriptor_id").compound_id.nunique()
n_str = strong.groupby("descriptor_id").row_id.count()
f3 = pd.DataFrame(dict(
    descriptor_id=aroma.descriptor_id, descriptor_label=aroma.descriptor_label,
    terminos=aroma.descriptor_id.map(terms), familias_en_fuente=aroma.descriptor_id.map(fams),
    n_filas_etiqueta=aroma.descriptor_id.map(n_rows).fillna(0).astype(int),
    n_compuestos=aroma.descriptor_id.map(n_cmp).fillna(0).astype(int),
    n_etiquetas_fuertes=aroma.descriptor_id.map(n_str).fillna(0).astype(int),
    propuesta_es_aroma=["no" if g else "sí" for g in aroma.family_is_general_or_character],
    propuesta_level1=aroma.family_l1_as_in_source,
    propuesta_separar_terminos=["revisar" if n > 1 else "no" for n in aroma.n_terms],
    estado="propuesta",
))
for who in ("revisor1", "revisor2"):
    for c in ("es_aroma", "level1", "level2", "level3", "termino_lexico"):
        f3[f"{who}_{c}"] = None
for c in ("consenso_es_aroma", "consenso_level1", "consenso_level2", "consenso_level3",
          "lexico_referencia", "notas"):
    f3[c] = None
f3 = f3.sort_values(["n_filas_etiqueta", "descriptor_label"], ascending=[False, True])
rev_cols = [c for c in f3.columns if c.startswith(("revisor", "consenso")) or c in ("lexico_referencia", "notas")]
save(f3, "fase3_descriptores_mapeo.xlsx", rev_cols,
     {"revisor1_es_aroma": ["sí", "no"], "revisor2_es_aroma": ["sí", "no"], "consenso_es_aroma": ["sí", "no"]},
     {"descriptor_label": 34, "terminos": 34, "familias_en_fuente": 30, "notas": 40})

# lista de familias actuales (referencia para el revisor)
fam_counts = dfam[dfam.descriptor_id.isin(aroma.descriptor_id)].family_token.value_counts()
fam_counts.rename_axis("familia_en_fuente").rename("n_descriptores").to_csv(
    os.path.join(OUT, "referencia_familias_actuales.csv"), encoding="utf-8-sig")
print("  referencia_familias_actuales.csv", len(fam_counts), "familias")
