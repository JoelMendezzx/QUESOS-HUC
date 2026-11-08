"""
Fase 6 — Extracción de datos experimentales POR MUESTRA desde estudios de acceso abierto.

Fuente de cada dato: tablas de los artículos (descargadas en data_external/articles/ y convertidas
a CSV con scripts/article_tables.py) + texto de métodos. Solo se registran condiciones de producción
que el artículo da EXPLÍCITAMENTE para sus muestras; lo demás queda vacío.

Salida: clean/muestras/ (study.csv, sample.csv, sample_compound.csv, sample_descriptor.csv,
        data_dictionary_muestras.csv, resumen_fase6.json)

Uso: python scripts/phase6_extract.py
"""
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_quality as P4  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "data_external", "articles")
PC = os.path.join(ROOT, "data_external", "pubchem")
OUT = os.path.join(ROOT, "clean", "muestras")
os.makedirs(OUT, exist_ok=True)
V, I, N = P4.V, P4.I, P4.N


def read_table(folder, n):
    with open(os.path.join(ART, folder, f"table_{n}.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    return [r for r in rows if r and not r[0].startswith("# CAPTION")]


def num(s):
    """'1,394,525' -> 1394525.0 ; '8.06 ± 22.8' -> (8.06, 22.8); 'ND'/'Nd'/'–'/'-' -> None."""
    s = (s or "").strip()
    m = re.match(r"^([<>]?)\s*([\d,]*\.?\d+)\s*(?:[a-z]{1,3}\s*)?(?:±\s*([\d,]*\.?\d+))?", s)
    if not m:
        return None, None
    v = float(m.group(2).replace(",", "")) if m.group(2) else None
    sd = float(m.group(3).replace(",", "")) if m.group(3) else None
    return v, sd


def fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


# ---------------------------------------------------------------- resolución de compuestos
dc = pd.read_csv(os.path.join(ROOT, "clean", "soporte", "dim_compound.csv"))
ca = pd.read_csv(os.path.join(ROOT, "clean", "soporte", "compound_alias.csv"))
pr = pd.read_csv(os.path.join(ROOT, "clean", "modelo", "compound_properties.csv"))
ALIAS = {}
for a, c in zip(ca.alias, ca.compound_id):
    ALIAS[fold(a)] = c
for a, c in zip(pr.iupac_name_pubchem.fillna(""), pr.compound_id):
    if a:
        ALIAS.setdefault(fold(a), c)
CID2CMP = dict(zip(pr.pubchem_cid.astype(int), pr.compound_id))
CAS = dc.set_index("compound_id").cas_final


def pubchem_name(name):
    path = os.path.join(PC, f"name6_{re.sub(r'[^A-Za-z0-9_.-]+', '_', name)[:110]}.json")
    if not os.path.exists(path):
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{urllib.parse.quote(name)}/cids/JSON"
        try:
            data = urllib.request.urlopen(url, timeout=30).read()
        except Exception:
            data = b'{"Fault": {}}'
        open(path, "wb").write(data)
        time.sleep(0.25)
    try:
        ids = json.load(open(path, encoding="utf-8")).get("IdentifierList", {}).get("CID", [])
    except json.JSONDecodeError:
        ids = []
    return ids[0] if ids else None


def clean_name(n):
    n = re.sub(r"\s+", " ", n).strip()
    n = re.sub(r"^n-\s*", "", n)
    n = n.replace("sulph", "sulf").replace("Sulph", "Sulf")
    return n


def resolve(name):
    """-> (compound_id, pubchem_cid, método)"""
    cands = [clean_name(name)]
    stripped = re.sub(r"(?<=[a-z\)])[def](,[def])*$", "", cands[0])
    if stripped != cands[0]:
        cands.append(stripped)
    for c in cands:
        if fold(c) in ALIAS:
            return ALIAS[fold(c)], None, "alias_base"
    for c in cands:
        cid = pubchem_name(c)
        if cid:
            return CID2CMP.get(cid), cid, "pubchem_nombre"
    return None, None, "no_resuelto"


# ---------------------------------------------------------------- ontología para descriptores
dd = pd.read_csv(os.path.join(ROOT, "clean", "soporte", "dim_descriptor.csv"))
TERM2FAM = {}
for terms, fam in zip(dd.aroma_terms.fillna(""), dd.aroma_family):
    if isinstance(fam, str):
        for t in terms.split(";"):
            if t.strip():
                TERM2FAM.setdefault(P4.stem(t), fam)


FAMILY_NAMES = {"toasted": "toasted", "roasted": "toasted", "floral": "floral", "fruity": "fruity",
                "lactic": "lactic", "animal": "animal", "spicy": "spicy", "vegetal": "vegetal"}
EXTRA = {"ammonia": ("other", "Bérodier 'ammoniacal' (autres)")}


def map_family(term):
    s = P4.stem(term)
    low = term.strip().lower()
    if low in FAMILY_NAMES:
        return FAMILY_NAMES[low], "nombre de familia de Bérodier", V
    if low in EXTRA:
        return EXTRA[low][0], EXTRA[low][1], I
    if s in TERM2FAM:
        return TERM2FAM[s], "ontologia_fase3 (término)", I
    for k, (fam, _) in P4.FN_FAMILY.items():
        if P4.stem(k) == s:
            return fam, "tabla Flavornet→Bérodier (término)", I
    for w in s.split():
        if w in TERM2FAM:
            return TERM2FAM[w], f"ontologia_fase3 (palabra '{w}')", I
    return None, "sin_correspondencia", N


# ---------------------------------------------------------------- registro
STUDIES, SAMPLES, SC, SD = [], [], [], []


def add_study(**k):
    STUDIES.append(k)


def add_sample(**k):
    SAMPLES.append(k)


def add_comp(sample_id, name, raw, unit, measure, method, loc, detected=None, note=None, family_level=False):
    v, sd = num(raw)
    cid_, pcid, how = (None, None, "familia_quimica") if family_level else resolve(name)
    SC.append(dict(sample_id=sample_id, compound_name_source=name.strip(), compound_id=cid_,
                   cas=CAS.get(cid_) if cid_ else None, pubchem_cid=pcid, compound_match=how,
                   is_family_total=family_level, measure_type=measure, value=v, value_sd=sd,
                   value_raw=(raw or "").strip(), unit_original=unit, detected=detected,
                   detection_note=note, analytical_method=method, source_location=loc))


def add_desc(sample_id, term, category, modality, method, value=None, value_unit=None, presence=None,
             compound=None, loc=None, note=None, link_status=V):
    fam, how, st = map_family(term) if modality in ("aroma", "flavor") else (None, "no_aplica (no es aroma)", None)
    SD.append(dict(sample_id=sample_id, descriptor_source=term, category_source=category, modality=modality,
                   evaluation_method=method, value=value, value_unit=value_unit, presence=presence,
                   linked_compound_source=compound,
                   linked_compound_id=resolve(compound)[0] if compound else None,
                   aroma_family=fam, ontology_mapping=how, ontology_status=st,
                   sample_link_status=link_status, source_location=loc, note=note))


# ======================================================================= ESTUDIO 1
S1 = "DUE24A"
add_study(study_id=S1, citation="Duensing PW, Hinrichs J, Schieberle P. (2024) Formation of Key Aroma Compounds During 30 Weeks of Ripening in Gouda-Type Cheese Produced from Pasteurized and Raw Milk. J. Agric. Food Chem.",
          doi="10.1021/acs.jafc.4c01814", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC11100003/", access="acceso abierto (PMC)",
          design="Dos quesos tipo Gouda a escala piloto (leche pasteurizada PM-G / cruda RM-G) muestreados a 0, 4, 7, 11, 19 y 30 semanas",
          in_excel_sources="sí (Duensing 2024a)")
for code, heat, tab in [("PM-G", "pasteurized", 1), ("RM-G", "raw", 2)]:
    rows = read_table("PMC11100003", tab)
    weeks = [0, 4, 7, 11, 19, 30]
    for w in weeks:
        add_sample(sample_id=f"{S1}-{code}-W{w}", study_id=S1, sample_code_in_source=f"{code}, {w} semanas",
                   cheese_type_reported="Gouda-type (pilot scale)", milk_species_reported=None,
                   milk_heat_treatment_reported=heat,
                   heat_treatment_detail="72–74 °C, 30 s" if heat == "pasteurized" else "sin pasteurizar",
                   coagulant_reported="lab enzyme (cuajo de laboratorio)", starter_culture_reported="defined starter cultures",
                   other_process="leche estandarizada 3,5 % grasa; CaCl2 y lisozima; cuajada lavada; prensado 0,38 MPa; salmuera 28 h",
                   ripening_days=w * 7, ripening_temp_c=15, ripening_rh_pct="80–85", storage_days=None,
                   production_unit=f"{S1}-{code}", replicate_type="valor medio de análisis repetidos (técnicas)",
                   independence_note="Misma producción a distintos tiempos (serie temporal, no muestras independientes)",
                   possible_same_material_as=f"DUE24B-{code}-B1 (si W30)" if w == 30 else None,
                   source_location=f"Tabla {tab}; métodos (PMC11100003 y PMC11100000)")
    hdr_skip = 2
    for r in rows[hdr_skip:]:
        name = r[1] if tab == 1 else r[0]
        vals = r[2:8] if tab == 1 else r[1:7]
        for w, raw in zip(weeks, vals):
            add_comp(f"{S1}-{code}-W{w}", name, raw, "μg/kg materia seca", "concentracion",
                     "SIDA (dilución isotópica) GC-MS", f"PMC11100003 Tabla {tab}",
                     detected=True if num(raw)[0] is not None else None)

# ======================================================================= ESTUDIO 2
S2 = "DUE24B"
add_study(study_id=S2, citation="Duensing PW, Hinrichs J, Schieberle P. (2024) Influence of Milk Pasteurization on the Key Aroma Compounds in a 30 Weeks Ripened Pilot-Scale Gouda Cheese Elucidated by the Sensomics Approach. J. Agric. Food Chem.",
          doi="10.1021/acs.jafc.4c01813", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC11100000/", access="acceso abierto (PMC)",
          design="Gouda piloto de leche pasteurizada y cruda (misma leche dividida), 30 semanas; lote 1 y lote 2 (repetición un año después)",
          in_excel_sources="sí (Duensing 2024a/b)")
for code, heat in [("PM-G", "pasteurized"), ("RM-G", "raw")]:
    for b in (1, 2):
        add_sample(sample_id=f"{S2}-{code}-B{b}", study_id=S2, sample_code_in_source=f"{code}, lote {b}",
                   cheese_type_reported="Gouda (pilot scale)", milk_species_reported=None,
                   milk_heat_treatment_reported=heat,
                   heat_treatment_detail="72–74 °C, 30 s" if heat == "pasteurized" else "sin pasteurizar",
                   coagulant_reported="lab enzyme", starter_culture_reported="defined starter cultures",
                   other_process="ídem DUE24A; lote 2 = repetición completa un año después",
                   ripening_days=210, ripening_temp_c=15, ripening_rh_pct="80–85", storage_days=None,
                   production_unit=f"{S2}-{code}-B{b}",
                   replicate_type="lote 1: media de réplicas (con rango); lote 2: valor único",
                   independence_note="Lotes 1 y 2 = producciones independientes; PM-G y RM-G comparten la leche de partida",
                   possible_same_material_as=f"{S1}-{code}-W30" if b == 1 else None,
                   source_location="Métodos (PMC11100000)")
for code, tab_c, tab_o, tab_g in [("PM-G", 3, 4, 2), ("RM-G", 6, 7, 5)]:
    rows = read_table("PMC11100000", tab_c)
    for r in rows[3:] if tab_c == 3 else rows[2:]:
        name = r[0]
        b1, b2 = (r[1], r[3]) if tab_c == 3 else (r[1], r[2])
        add_comp(f"{S2}-{code}-B1", name, b1, "μg/kg", "concentracion", "SIDA GC-MS", f"PMC11100000 Tabla {tab_c}", True)
        add_comp(f"{S2}-{code}-B2", name, b2, "μg/kg", "concentracion", "SIDA GC-MS", f"PMC11100000 Tabla {tab_c}", True)
    for r in read_table("PMC11100000", tab_o)[2:]:
        add_comp(f"{S2}-{code}-B1", r[0], r[2], "adimensional", "OAV", "concentración / umbral ortonasal",
                 f"PMC11100000 Tabla {tab_o}", True)
        add_comp(f"{S2}-{code}-B2", r[0], r[3], "adimensional", "OAV", "concentración / umbral ortonasal",
                 f"PMC11100000 Tabla {tab_o}", True)
    g = read_table("PMC11100000", tab_g)
    start = 2 if tab_g == 2 else 2
    for r in g[start:]:
        if len(r) < 6 or not r[0].strip().isdigit():
            continue
        fd = r[-1] if tab_g == 5 else r[7]
        add_desc(f"{S2}-{code}-B1", r[2], "odor quality (GC-O)", "aroma", "GC-O / AEDA (panel entrenado, 3 evaluadores)",
                 value=num(fd)[0], value_unit="FD factor", presence=True, compound=r[1],
                 loc=f"PMC11100000 Tabla {tab_g}",
                 note="La tabla no indica el lote; se vincula al lote 1 (análisis principal del artículo).",
                 link_status=I)

# ======================================================================= ESTUDIO 3
S3 = "IDI23"
add_study(study_id=S3, citation="Santamarina-García G. et al. (2023) Relationship between the dynamics of volatile aroma compounds and microbial succession during the ripening of raw ewe milk-derived Idiazabal cheese. Curr. Res. Food Sci.",
          doi="10.1016/j.crfs.2022.100425", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC9860272/", access="acceso abierto (PMC)",
          design="4 productores artesanales de Idiazabal DOP; duplicados a 1, 7, 14, 30, 60 y 120 días (n = 48); tablas con media ± DE de los productores",
          in_excel_sources="no (estudio nuevo)")
days = [1, 7, 14, 30, 60, 120]
for d in days:
    add_sample(sample_id=f"{S3}-D{d}", study_id=S3, sample_code_in_source=f"día {d} (media de productores A–D)",
               cheese_type_reported="Idiazabal PDO (artisanal)", milk_species_reported="sheep (Latxa)",
               milk_heat_treatment_reported="raw", heat_treatment_detail=None,
               coagulant_reported="artisanal or commercial rennet (NATUREN 195 Premium), según productor",
               starter_culture_reported="mesophilic: Choozit MM 100 (L. lactis lactis, cremoris, biovar diacetylactis)",
               other_process="leche templada a 25 °C", ripening_days=d, ripening_temp_c="8–14", ripening_rh_pct="80–95",
               storage_days=None, production_unit=f"{S3}-productores A-D (agregado)",
               replicate_type="media ± DE de 4 productores × duplicado (n = 8 por tiempo)",
               independence_note="Valor agregado de 4 productores independientes; misma serie temporal",
               possible_same_material_as=None, source_location="Sección 2.1 (Cheese sampling)")
t4 = read_table("idiazabal2023", 4)
for r in t4[2:]:
    if not re.match(r"^C\d+$", r[0]):
        continue
    for d, raw in zip(days, r[3:9]):
        nd = raw.strip().upper() == "ND"
        add_comp(f"{S3}-D{d}", r[2], raw, "abundancia relativa (área/área PI × 2,5 g / peso muestra × 100)",
                 "abundancia_relativa", "HS-SPME GC-MS", "PMC9860272 Tabla 1 (tabla 4 del HTML)",
                 detected=False if nd else (True if num(raw)[0] is not None else None),
                 note="ND explícito en la tabla" if nd else None)
t3 = read_table("idiazabal2023", 3)
for r in t3[2:]:
    if len(set(r)) == 1:
        continue
    for d, raw in zip(days, r[2:8]):
        note = "OIR < 1 (no odorante activo)" if raw.strip().startswith("<") else (
            "sin valor ('–')" if raw.strip() in ("–", "-") else None)
        add_comp(f"{S3}-D{d}", r[0], raw, "adimensional", "OIR (índice de impacto odorante = conc./umbral)",
                 "calculado a partir de GC-MS y umbrales bibliográficos", "PMC9860272 Tabla 2 (tabla 3 del HTML)",
                 detected=None, note=note)

# ======================================================================= ESTUDIO 4
S4 = "DOP20"
add_study(study_id=S4, citation="Dopieralska P. et al. (2020) Changes in Fatty Acid and Volatile Compound Profiles during Storage of Smoked Cheese Made from the Milk of Native Polish Cow Breeds Raised in the Low Beskids. Animals 10(11):2103.",
          doi="10.3390/ani10112103", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC7696590/", access="acceso abierto (PMC)",
          design="12 quesos ahumados (3 sesiones × 4 quesos) analizados a 1, 21, 42 y 69 días de almacenamiento",
          in_excel_sources="sí (Dopieralska 2020)")
for d in [1, 21, 42, 69]:
    add_sample(sample_id=f"{S4}-S{d}", study_id=S4, sample_code_in_source=f"día {d} de almacenamiento",
               cheese_type_reported="smoked cheese (Low Beskids, native Polish breeds)",
               milk_species_reported="cow (Polish Red, Polish Red-and-White, Polish Black-and-White)",
               milk_heat_treatment_reported="pasteurized", heat_treatment_detail="75 °C, 15 s",
               coagulant_reported="rennet MicroClage 2000 IMCU (1,4 mL/100 L)",
               starter_culture_reported="Choozit Star 26 (S. thermophilus), 2 %",
               other_process="grasa estandarizada 2,9 %; ahumado; envasado al vacío; almacenamiento a 5 °C",
               ripening_days=None, ripening_temp_c=None, ripening_rh_pct=None, storage_days=d,
               production_unit=f"{S4}-3 sesiones", replicate_type="media ± DE, n = 3",
               independence_note="Misma producción (3 sesiones) a distintos tiempos de almacenamiento",
               possible_same_material_as=None, source_location="Métodos (PMC7696590)")
for r in read_table("dopieralska2020", 3)[2:]:
    if len(set(r)) == 1:
        continue
    total = r[0].strip().lower() == "total"
    for d, raw in zip([1, 21, 42, 69], r[2:6]):
        nd = raw.strip().lower() == "nd"
        if total:
            continue
        add_comp(f"{S4}-S{d}", r[0], raw, "% de área", "porcentaje_area", "HS-SPME GC-MS", "PMC7696590 Tabla 3",
                 detected=False if nd else (True if num(raw)[0] is not None else None),
                 note="Nd explícito en la tabla" if nd else None)

# ======================================================================= ESTUDIO 5
S5 = "NAT20"
add_study(study_id=S5, citation="Natrella G. et al. (2020) Evolution of VOC and Sensory Characteristics of Stracciatella Cheese as Affected by Different Preservatives. Foods 9(10):1446.",
          doi="10.3390/foods9101446", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC7601598/", access="acceso abierto (PMC)",
          design="Stracciatella con 4 formulaciones (control, extracto de hoja de olivo, ácido sórbico, ambos) a 1, 4, 8, 12 y 16 días",
          in_excel_sources="sí (Natrella 2020)")
TREAT = {"Ctr": "control (sin conservante)", "Ex": "extracto de hoja de olivo", "So": "ácido sórbico",
         "Ex-So": "extracto + ácido sórbico"}
for t in TREAT:
    for d in [1, 4, 8, 12, 16]:
        add_sample(sample_id=f"{S5}-{t}-T{d}", study_id=S5, sample_code_in_source=f"{t}, día {d}",
                   cheese_type_reported="Stracciatella", milk_species_reported=None,
                   milk_heat_treatment_reported=None,
                   heat_treatment_detail="nata UHT (30 % grasa) mezclada 1:1 con hebras de mozzarella",
                   coagulant_reported=None, starter_culture_reported=None,
                   other_process=f"conservante: {TREAT[t]}", ripening_days=None, ripening_temp_c=None,
                   ripening_rh_pct=None, storage_days=d, production_unit=f"{S5}-{t}",
                   replicate_type="media ± DE", independence_note="Una producción por formulación, serie temporal",
                   possible_same_material_as=None, source_location="PMC7601598 Tabla 1 y métodos")
t4n = read_table("PMC7601598", 4)
cols = [(t, d) for t in ["Ctr", "Ex", "So", "Ex-So"] for d in [1, 4, 8, 12, 16]]
for r in t4n[2:]:
    for (t, d), raw in zip(cols, r[1:21]):
        add_comp(f"{S5}-{t}-T{d}", r[0], raw, "adimensional", "OAV", "SPME GC-MS / umbral bibliográfico",
                 "PMC7601598 Tabla 4", detected=None,
                 note="'-' = OAV ≤ 1 o no detectado (la tabla solo lista OAV > 1)" if raw.strip() in ("-", "–") else None)
t3n = read_table("PMC7601598", 3)
for r in t3n[1:]:
    if len(set(r)) == 1:
        continue
    for t, raw in zip(["Ctr", "Ex", "So", "Ex-So"], r[1:5]):
        add_comp(f"{S5}-{t}-T16", r[0], raw, "μg/kg", "concentracion", "SPME GC-MS", "PMC7601598 Tabla 3",
                 detected=None, note="'-' = < 1 μg/kg o no detectado (la tabla solo lista > 1 μg)" if raw.strip() in ("-", "–") else None)

# ======================================================================= ESTUDIO 6
S6 = "TOR21"
add_study(study_id=S6, citation="Torri L. et al. (2021) Relationship between Sensory Attributes, (Dis) Liking and Volatile Organic Composition of Gorgonzola PDO Cheese. Foods 10(11):2791.",
          doi="10.3390/foods10112791", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC8621326/", access="acceso abierto (PMC)",
          design="6 Gorgonzola DOP comerciales (dulce/picante, 70–95 días, artesanal/industrial) evaluados por consumidores (RATA)",
          in_excel_sources="sí (Torri 2021)")
for r in read_table("PMC8621326", 1)[1:]:
    add_sample(sample_id=f"{S6}-{r[0]}", study_id=S6, sample_code_in_source=r[0],
               cheese_type_reported=f"Gorgonzola PDO ({r[1].lower()})", milk_species_reported=None,
               milk_heat_treatment_reported=None, heat_treatment_detail=None, coagulant_reported=None,
               starter_culture_reported=None, other_process=f"estilo {r[1]}; proceso {r[3]}",
               ripening_days=float(r[2]), ripening_temp_c=None, ripening_rh_pct=None, storage_days=None,
               production_unit=f"{S6}-{r[0]}", replicate_type="producto comercial (un lote)",
               independence_note="Productos distintos del mismo fabricante (IGOR), verano 2019",
               possible_same_material_as=None, source_location="PMC8621326 Tabla 1")
t3t = read_table("PMC8621326", 3)
codes = ["S80", "S75", "S70", "P95", "P85", "P80"]
cat = None
for r in t3t[2:]:
    if all(x == "" for x in r[1:]):
        cat = r[0]
        continue
    for k, code in enumerate(codes):
        base = 2 + 5 * k
        occ, mean = r[base], r[base + 3]
        modality = "aroma" if cat == "Flavor" else ("taste" if cat == "Taste" else "texture")
        add_desc(f"{S6}-{code}", r[0], cat, modality, "consumidores, RATA (n = 358)",
                 value=num(mean)[0], value_unit="intensidad media RATA (incluye ceros)",
                 presence=(num(occ)[0] or 0) > 0, loc="PMC8621326 Tabla 3",
                 note=f"ocurrencias: {occ}")

# ======================================================================= ESTUDIO 7
S7 = "CHE22"
add_study(study_id=S7, citation="Chen C. et al. (2022) Characterisation of the key volatile compounds of commercial Gouda cheeses and their contribution to aromas according to Chinese consumers' preference. Food Chem. X.",
          doi="10.1016/j.fochx.2022.100416", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC9532783/", access="acceso abierto (PMC)",
          design="12 Gouda comerciales: jóvenes (C1–C4), medios (C5–C8) y madurados (C9–C12); GC-O (frecuencia modificada) y OAV",
          in_excel_sources="sí (Chen 2022)")
for k in range(1, 13):
    mat = "young" if k <= 4 else ("medium" if k <= 8 else "aged")
    add_sample(sample_id=f"{S7}-C{k}", study_id=S7, sample_code_in_source=f"C{k}",
               cheese_type_reported=f"Gouda, commercial ({mat})", milk_species_reported=None,
               milk_heat_treatment_reported=None, heat_treatment_detail=None, coagulant_reported=None,
               starter_culture_reported=None, other_process=f"categoría de maduración: {mat}",
               ripening_days=None, ripening_temp_c=None, ripening_rh_pct=None, storage_days=None,
               ripening_category_reported=mat, production_unit=f"{S7}-C{k}",
               replicate_type="producto comercial", independence_note="Productos comerciales distintos",
               possible_same_material_as=None,
               source_location="Sección 2.1; edad exacta en la Tabla S1 suplementaria (no consultada)")
t1c = read_table("PMC9532783", 1)
for r in t1c[2:]:
    if not r[0].strip().isdigit():
        continue
    name, ad = r[1], r[2]
    for k in range(12):
        oav, mf = r[4 + 2 * k], r[5 + 2 * k]
        nd = oav.strip() in ("–", "-") and mf.strip() in ("–", "-")
        add_comp(f"{S7}-C{k + 1}", name, oav, "adimensional", "OAV", "HS-SPME GC-MS / umbral", "PMC9532783 Tabla 1",
                 detected=False if nd else True, note="'–' en OAV y MF (no detectado por GC-MS ni GC-O)" if nd else None)
        add_desc(f"{S7}-C{k + 1}", ad, "aroma descriptor (GC-O)", "aroma", "GC-O, frecuencia modificada (MF %)",
                 value=num(mf)[0], value_unit="MF (%)", presence=not nd, compound=name, loc="PMC9532783 Tabla 1",
                 note="no percibido en esta muestra ('–')" if nd else None)

# ---------------------------------------------------------------- tablas
study = pd.DataFrame(STUDIES)
sample = pd.DataFrame(SAMPLES)
sc = pd.DataFrame(SC)
sd = pd.DataFrame(SD)
# vínculo con dim_cheese (tipo de queso armonizado)
TYPE2CHEESE = {"DUE24A": "Gouda", "DUE24B": "Gouda", "IDI23": "Idiazabal", "DOP20": "Polish smoked cheese",
               "NAT20": None, "TOR21": "Gorgonzola", "CHE22": "Gouda"}
dch = pd.read_csv(os.path.join(ROOT, "clean", "soporte", "dim_cheese.csv"))
cid_by_name = dict(zip(dch.cheese_name_std, dch.cheese_id))
sample["cheese_id"] = sample.study_id.map(lambda s: cid_by_name.get(TYPE2CHEESE.get(s)))
for col in ["ripening_category_reported"]:
    if col not in sample:
        sample[col] = None
sample["has_compound_data"] = sample.sample_id.isin(sc.sample_id)
sample["has_descriptor_data"] = sample.sample_id.isin(sd[sd.modality == "aroma"].sample_id)
sample["has_production_variable"] = (sample.milk_heat_treatment_reported.notna() | sample.ripening_days.notna()
                                     | sample.storage_days.notna() | sample.other_process.notna())
order = ["sample_id", "study_id", "sample_code_in_source", "cheese_type_reported", "cheese_id",
         "milk_species_reported", "milk_heat_treatment_reported", "heat_treatment_detail", "coagulant_reported",
         "starter_culture_reported", "other_process", "ripening_days", "ripening_category_reported", "ripening_temp_c",
         "ripening_rh_pct", "storage_days", "production_unit", "replicate_type", "independence_note",
         "possible_same_material_as", "has_production_variable", "has_compound_data", "has_descriptor_data",
         "source_location"]
sample = sample[order]
for df, name in [(study, "study.csv"), (sample, "sample.csv"), (sc, "sample_compound.csv"), (sd, "sample_descriptor.csv")]:
    df.to_csv(os.path.join(OUT, name), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- diccionario
DD = {
    "study.csv": {"study_id": "Identificador del estudio", "citation": "Cita", "doi": "DOI verificado en la página del artículo",
                  "url": "URL consultada", "access": "Tipo de acceso", "design": "Diseño experimental (según el artículo)",
                  "in_excel_sources": "Si el estudio ya figuraba en las fuentes del Excel"},
    "sample.csv": {"sample_id": "Identificador único de la muestra", "study_id": "FK a study",
                   "sample_code_in_source": "Código o descripción de la muestra en el artículo",
                   "cheese_type_reported": "Tipo de queso según el artículo", "cheese_id": "FK a dim_cheese (tipo armonizado)",
                   "milk_species_reported": "Especie de leche indicada por el artículo para la muestra (vacío = no indicada)",
                   "milk_heat_treatment_reported": "raw / pasteurized indicado por el artículo",
                   "heat_treatment_detail": "Detalle del tratamiento térmico", "coagulant_reported": "Coagulante indicado",
                   "starter_culture_reported": "Cultivo iniciador indicado", "other_process": "Otras condiciones indicadas",
                   "ripening_days": "Días de maduración de la muestra", "ripening_category_reported": "Categoría de maduración (si no hay días)",
                   "ripening_temp_c": "Temperatura de maduración (°C)", "ripening_rh_pct": "Humedad relativa de maduración (%)",
                   "storage_days": "Días de almacenamiento (quesos ya elaborados)", "production_unit": "Unidad de producción (para medir independencia)",
                   "replicate_type": "Tipo de réplica / agregación del valor", "independence_note": "Relación con otras muestras",
                   "possible_same_material_as": "Muestra de otro estudio que podría ser el mismo material",
                   "has_production_variable": "Tiene al menos una variable de producción documentada",
                   "has_compound_data": "Tiene mediciones de compuestos", "has_descriptor_data": "Tiene descriptores de aroma",
                   "source_location": "Tabla/sección del artículo"},
    "sample_compound.csv": {"sample_id": "FK a sample", "compound_name_source": "Nombre del compuesto en el artículo",
                            "compound_id": "FK a dim_compound (si el compuesto está en la base)", "cas": "CAS (de dim_compound)",
                            "pubchem_cid": "CID de PubChem obtenido por nombre (si no está en la base)",
                            "compound_match": "Cómo se identificó el compuesto", "is_family_total": "Total de una familia química",
                            "measure_type": "concentracion / abundancia_relativa / porcentaje_area / OAV / OIR",
                            "value": "Valor numérico", "value_sd": "Desviación estándar (si se da)", "value_raw": "Texto original de la celda",
                            "unit_original": "Unidad original del artículo", "detected": "False = no detección explícita (ND); vacío = no aplica o no indicado",
                            "detection_note": "Nota sobre la celda", "analytical_method": "Método analítico", "source_location": "Tabla del artículo"},
    "sample_descriptor.csv": {"sample_id": "FK a sample", "descriptor_source": "Descriptor en el artículo",
                              "category_source": "Categoría del descriptor en el artículo", "modality": "aroma / taste / texture",
                              "evaluation_method": "Panel sensorial (RATA) o GC-O; nunca propiedades de compuestos aislados",
                              "value": "Valor (FD, MF % o intensidad)", "value_unit": "Unidad del valor", "presence": "Presencia en la muestra",
                              "linked_compound_source": "Compuesto asociado (GC-O)", "linked_compound_id": "FK a dim_compound",
                              "aroma_family": "Familia de Bérodier (ontología de la Fase 3)", "ontology_mapping": "Cómo se asignó la familia",
                              "ontology_status": "Estado de la asignación", "sample_link_status": "Estado del vínculo con la muestra",
                              "source_location": "Tabla del artículo", "note": "Nota"},
}
pd.DataFrame([dict(table=t, column=c, description=d) for t, cols in DD.items() for c, d in cols.items()]).to_csv(
    os.path.join(OUT, "data_dictionary_muestras.csv"), index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- resumen
both = sample[sample.has_production_variable & (sample.has_compound_data | sample.has_descriptor_data)]
summ = dict(
    estudios=len(study), muestras=len(sample), unidades_de_produccion=int(sample.production_unit.nunique()),
    muestras_con_produccion_y_compuestos=int((sample.has_production_variable & sample.has_compound_data).sum()),
    muestras_con_produccion_y_descriptores_aroma=int((sample.has_production_variable & sample.has_descriptor_data).sum()),
    registros_compuesto=len(sc), registros_compuesto_con_compound_id=int(sc.compound_id.notna().sum()),
    no_detecciones_explicitas=int((sc.detected == False).sum()),
    registros_descriptor=len(sd), registros_descriptor_aroma=int((sd.modality == "aroma").sum()),
    descriptores_aroma_con_familia=int(((sd.modality == "aroma") & sd.aroma_family.notna()).sum()),
    muestras_por_estudio=sample.groupby("study_id").size().to_dict(),
    variables_faltantes={c: int(sample[c].isna().sum()) for c in
                         ["milk_species_reported", "milk_heat_treatment_reported", "coagulant_reported",
                          "starter_culture_reported", "ripening_days"]},
)
json.dump(summ, open(os.path.join(OUT, "resumen_fase6.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(summ, ensure_ascii=False, indent=1))
