"""
Construye la base de datos HUC limpia (CSV) a partir del Excel original.

Principio: NO se inventa información. Solo se reorganiza, normaliza y separa
lo que ya existe en el Excel. Lo que no está en la fuente queda vacío (NA).

Uso:  python scripts/build_clean_db.py
Salida: carpeta clean/
"""
import os
import re
import unicodedata
import warnings
import sys
from collections import Counter, OrderedDict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harmonization_decisions as HD  # noqa: E402  (decisiones de armonización, Fases 1–3)
import phase4_quality as P4  # noqa: E402  (Fase 4: PubChem y Flavornet desde data_external/)

warnings.filterwarnings("ignore")
CORR_LOG = []  # registro de cada corrección aplicada (base v2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "HUC-Database descriptor  compound  cheese English.xlsx")
OUT = os.path.join(ROOT, "clean")
os.makedirs(OUT, exist_ok=True)

X = pd.read_excel(SRC, sheet_name=None)  # lee valores cacheados de las fórmulas
EV = X["Evidence"]
OA = X["1. Odor & Aroma"]
PV = X["Process and Volatiles"]
CP = X["Cheese Profiles"]
SY = X["Synonyms"]
BP = X["Biochemical Pathways"]
AC = X["Articles to Confirm"]
TA = X["2. Taste"]
TR = X["3. Trigeminal"]
TX = X["4. Texture"]

# quitar espacios de los encabezados y columnas vacías
for df in (EV, OA, PV, CP, SY, BP, AC, TA, TR, TX):
    df.columns = [str(c).strip() for c in df.columns]
EV = EV.loc[:, [c for c in EV.columns if not c.startswith("Unnamed")]]
TR = TR.loc[:, [c for c in TR.columns if not c.startswith("Unnamed")]]

ISSUES = []  # registro de problemas detectados automáticamente


def issue(table, key, field, problem, value=None):
    ISSUES.append(dict(table=table, record_key=key, field=field, problem=problem,
                       value=None if value is None else str(value)[:300]))


# ----------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------
NULL_TOKENS = {"", "—", "-", "–", "nan", "none", "n/a", "na"}


def clean(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = str(s).replace(" ", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return None if s.lower() in NULL_TOKENS else s


def fold(s):
    s = clean(s)
    if s is None:
        return None
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def split_list(s, sep=";"):
    s = clean(s)
    if s is None:
        return []
    return [t for t in (clean(p) for p in s.split(sep)) if t]


def dedupe(seq):
    return list(OrderedDict.fromkeys(seq))


def cas_format_ok(c):
    return bool(c) and re.fullmatch(r"\d{2,7}-\d{2}-\d", c) is not None


def cas_checksum_ok(c):
    if not cas_format_ok(c):
        return False
    a, b, chk = c.split("-")
    digits = (a + b)[::-1]
    return sum((i + 1) * int(d) for i, d in enumerate(digits)) % 10 == int(chk)


def clean_cas(c):
    c = clean(c)
    if c is None:
        return None
    c = c.strip(" ;,")
    return c if cas_format_ok(c) else None


def to_int(v):
    v = clean(v)
    if v is None:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def to_num(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    s = clean(v)
    if s is None:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


# clean/modelo  -> lo necesario para entrenar (+ diccionario de columnas)
# clean/soporte -> catálogos, puentes, otras modalidades y control de calidad
MODEL_FILES = {"ml_evidence_flat.csv", "fact_process_effect.csv", "fact_compound_odor.csv",
               "data_dictionary.csv", "compound_properties.csv"}
OUT_MODEL = os.path.join(OUT, "modelo")
OUT_SUPPORT = os.path.join(OUT, "soporte")
for _d in (OUT_MODEL, OUT_SUPPORT):
    os.makedirs(_d, exist_ok=True)


def folder_for(name):
    return OUT_MODEL if name in MODEL_FILES else OUT_SUPPORT


def write(df, name):
    path = os.path.join(folder_for(name), name)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    rel = os.path.relpath(path, OUT).replace("\\", "/")
    print(f"  {rel:50s} {df.shape[0]:>6} filas x {df.shape[1]:>3} cols")


# ----------------------------------------------------------------------------
# 1. FUENTES  (dim_source)
# ----------------------------------------------------------------------------
# erratas evidentes de autor (mismo año, misma obra)
SOURCE_FIX = {"Bintis": "Bintsis", "Boscani": "Boscaini", "Fuchsmann": "Fuchsman",
              "Le Quéret": "Le Quéré", "Rammirez": "Ramirez"}


def short_citation(s):
    """'Papademas 2018 (p. 300)' -> 'Papademas 2018'"""
    s = clean(s)
    if s is None:
        return None
    s = re.sub(r"\(.*?\)", "", s).strip()
    m = re.match(r"^(.+?\D)\s*(\d{4}[a-z]?)\b", s)
    if not m:
        return s
    author = clean(m.group(1))
    if author in SOURCE_FIX:
        issue("dim_source", s, "author", "Errata de autor unificada", f"{author} -> {SOURCE_FIX[author]}")
        author = SOURCE_FIX[author]
    return f"{author} {m.group(2)}"


source_names = Counter()
for col_df, col in [(EV, "source_raw"), (OA, "Source"), (PV, "source"), (TA, "Source"),
                    (TR, "Source"), (TX, "Source"), (BP, "source"), (CP, "source"),
                    (AC, "Sources of the master-file row")]:
    for v in col_df[col].dropna():
        for t in split_list(v):
            sc = short_citation(t)
            if sc and sc.lower() != "cheese label in the source":
                source_names[sc] += 1

# tipo de fuente según la hoja Evidence (solo filas con una única fuente)
stype = {}
for _, r in EV.dropna(subset=["source_raw", "source_type"]).iterrows():
    toks = split_list(r["source_raw"])
    if len(toks) == 1:
        stype.setdefault(short_citation(toks[0]), Counter())[r["source_type"]] += 1

src_rows, SRC_ID = [], {}
used = set()
for name in sorted(source_names, key=lambda s: fold(s)):
    m = re.match(r"^(.+?)\s+(\d{4})([a-z]?)$", name)
    author, year, suf = (m.group(1), int(m.group(2)), m.group(3)) if m else (name, None, "")
    base = re.sub(r"[^A-Za-z]", "", fold(author))[:3].upper() or "SRC"
    sid = f"{base}{str(year)[-2:] if year else 'XX'}{suf}"
    k = sid
    i = 0
    while k in used:
        i += 1
        k = f"{sid}_{i + 1}"
    used.add(k)
    SRC_ID[name] = k
    st = stype.get(name)
    src_rows.append(dict(source_id=k, short_citation=name, first_author=author, year=year,
                         source_type=st.most_common(1)[0][0] if st else None,
                         n_mentions=source_names[name]))
dim_source = pd.DataFrame(src_rows)


def source_ids(s):
    out = []
    for t in split_list(s):
        sc = short_citation(t)
        if sc in SRC_ID:
            out.append(SRC_ID[sc])
    return dedupe(out)


def cited_parts(s):
    """Divide la celda de fuentes primarias citadas en citas individuales."""
    s = clean(s)
    if s is None:
        return []
    return [p for p in (clean(x) for x in re.split(r"[;|]", s)) if p]


def cited_short(s):
    """Devuelve 'Autor año' solo si la celda contiene UNA cita con año.
    'Moio, Piombino, and Addeo (2000)' -> 'Moio 2000'"""
    parts = cited_parts(s)
    if len(parts) != 1:
        return None
    eq = re.search(r"\(=\s*([^)]+?\d{4}[a-z]?)\)", parts[0])  # la propia celda dice '(= Qian 2002a)'
    if eq:
        return clean(eq.group(1))
    m = re.match(r"^([^\d(,&]+?)(?:,|\s&|\sand\s|\set al\.?|\s\()[^()]*?\((\d{4}[a-z]?)\)", parts[0])
    if not m:
        return None
    first = clean(m.group(1))
    return f"{first} {m.group(2)}" if first else None


def src_lookup(short):
    if not short:
        return None
    k = fold(short)
    for name, sid in SRC_ID.items():
        if fold(name) == k:
            return sid
    return None


# ----------------------------------------------------------------------------
# 2. COMPUESTOS  (dim_compound + compound_alias)
# ----------------------------------------------------------------------------
recs = []  # (name, cas, cid, origin, priority)
for _, r in EV.iterrows():
    recs.append((clean(r["iupac_compound"]), clean(r["cas"]), None, "Evidence", 1))
for _, r in PV.iterrows():
    if clean(r["iupac_compound"]):
        recs.append((clean(r["iupac_compound"]), clean(r["cas"]), None, "Process and Volatiles", 2))
for i_, r in OA.iterrows():
    n = split_list(r["IUPAC- Chemical Compound(s)"])
    c = split_list(r["CAS number"])
    d = split_list(r["Pubchem CID"])
    if len(n) != len(d):
        issue("1. Odor & Aroma", f"fila Excel {i_ + 2}", "Pubchem CID",
              "Nº de compuestos distinto del nº de CID: CID desalineados (no se usan; CID tomado de Synonyms)",
              r["Pubchem CID"])
    for i, name in enumerate(n):
        # el CID de esta hoja no es fiable por posición -> solo nombre y CAS
        recs.append((name, c[i] if i < len(c) else None, None, "1. Odor & Aroma", 3))
for _, r in SY.iterrows():
    recs.append((clean(r["IUPAC compound(s)"]), clean(r["CAS"]), clean(r["CID"]), "Synonyms", 4))
for _, r in TA.iterrows():
    n = split_list(r["IUPAC- Chemical Compound(s)"])
    c = split_list(r["CAS number"])
    d = split_list(r["Pubchem CID"])
    for i, name in enumerate(n):
        recs.append((name, c[i] if i < len(c) else None, d[i] if i < len(d) else None,
                     "2. Taste", 5))

# Sinónimo IUPAC directo de un CAS que ya existe en la base (no añade datos nuevos)
alias_to_cas = {"ethanoic acid": "64-19-7"}
for name, cas, _, _, _ in recs:
    cc = clean_cas(cas)
    if name and cc:
        alias_to_cas.setdefault(fold(name), cc)

groups = OrderedDict()
for name, cas, cid, origin, prio in recs:
    if not name:
        continue
    cc = clean_cas(cas) or alias_to_cas.get(fold(name))
    key = cc if cc else "NAME:" + fold(name)
    g = groups.setdefault(key, dict(cas=cc, names=Counter(), prio={}, cids=Counter(),
                                    origins=set(), raw_cas=set()))
    g["names"][name] += 1
    g["prio"][name] = min(prio, g["prio"].get(name, 99))
    g["origins"].add(origin)
    if clean(cas):
        g["raw_cas"].add(clean(cas))
    ci = to_int(cid)
    if ci:
        g["cids"][ci] += 1

REF_STANDARD_PAT = re.compile(r"trimethylpurine|quinolin|quinuclidin", re.I)


def chem_class(name):
    """Clase química por regla sobre el nombre IUPAC (método documentado)."""
    n = fold(name) or ""
    if re.search(r"thiol|sulfan|sulfid|sulfon|disulf|trisulf|thio|thiazol|sulfur", n):
        return "sulfur_compound"
    if "pyrazin" in n:
        return "pyrazine"
    if re.search(r"oxolan-2-one|oxan-2-one|olide|lactone", n):
        return "lactone"
    if "indol" in n:
        return "indole"
    if re.search(r"phenol|cresol", n):
        return "phenol"
    if re.search(r"oate\b|acetate\b|formate\b", n):
        return "ester"
    if re.search(r"\bacid\b|oic acid", n):
        return "carboxylic_acid"
    if "furan" in n:
        return "furan"
    if re.search(r"(al|enal|aldehyde)$", n):
        return "aldehyde"
    if re.search(r"an-2-one$", n) and "," not in n:
        return "methyl_ketone"
    if re.search(r"(one|dione)$", n):
        return "ketone"
    if re.search(r"(ol|-ol)$", n):
        return "alcohol"
    if re.search(r"(ane|ene|diene)$", n):
        return "hydrocarbon"
    return None


cmp_rows, alias_rows = [], []
CMP_BY_CAS, CMP_BY_NAME = {}, {}
for i, (key, g) in enumerate(groups.items(), start=1):
    cid_ = f"CP_{i:04d}"
    pref = sorted(g["names"], key=lambda n: (g["prio"][n], -g["names"][n]))[0]
    cids = list(g["cids"])
    if len(cids) > 1:
        issue("dim_compound", cid_, "pubchem_cid", "CID distintos para el mismo compuesto", cids)
    if g["cas"] is None:
        issue("dim_compound", cid_, "cas", "Sin CAS válido en la fuente", "; ".join(g["raw_cas"]) or pref)
    elif not cas_checksum_ok(g["cas"]):
        issue("dim_compound", cid_, "cas", "CAS con dígito de control incorrecto", g["cas"])
    is_ref = bool(REF_STANDARD_PAT.search(pref))
    cmp_rows.append(dict(
        compound_id=cid_, cas=g["cas"],
        cas_checksum_valid=cas_checksum_ok(g["cas"]) if g["cas"] else None,
        pubchem_cid=g["cids"].most_common(1)[0][0] if cids else None,
        pubchem_cid_conflict=len(cids) > 1,
        iupac_name=pref,
        n_aliases=len(g["names"]),
        chemical_class=chem_class(pref),
        chemical_class_method="regla_sobre_nombre" if chem_class(pref) else None,
        is_reference_standard_only=is_ref,
        only_in_taste_sheet=g["origins"] == {"2. Taste"},
        origin_sheets=" | ".join(sorted(g["origins"])),
    ))
    if g["cas"]:
        CMP_BY_CAS[g["cas"]] = cid_
    for n in g["names"]:
        CMP_BY_NAME[fold(n)] = cid_
        alias_rows.append(dict(compound_id=cid_, alias=n, is_preferred=(n == pref),
                               n_occurrences=g["names"][n]))
dim_compound = pd.DataFrame(cmp_rows)
compound_alias = pd.DataFrame(alias_rows)

# --- Fase 4: verificación y completado de CID/CAS con PubChem + propiedades químicas ---
dim_compound, compound_properties, _p4log = P4.enrich_compounds(dim_compound)
CORR_LOG.extend(_p4log)
FLAVORNET = P4.load_flavornet()
dim_compound["in_flavornet"] = dim_compound.cas_final.isin(FLAVORNET)
dim_compound["flavornet_odors"] = dim_compound.cas_final.map(lambda c: "; ".join(sorted(FLAVORNET[c])) if c in FLAVORNET else None)


def compound_id(name=None, cas=None):
    cc = clean_cas(cas)
    if cc and cc in CMP_BY_CAS:
        return CMP_BY_CAS[cc]
    return CMP_BY_NAME.get(fold(name)) if name else None


# ----------------------------------------------------------------------------
# 3. DESCRIPTORES  (dim_descriptor + alias + familias)
# ----------------------------------------------------------------------------
FAMILY_FIX = {"malta": "Malt", "sulfurous": "Sulfurous"}
NON_AROMA_FAMILIES = {"general", "general intensity", "character", "body", "stable"}


def family_tokens(s):
    s = clean(s)
    if s is None:
        return []
    toks = []
    for part in re.split(r"[;/]", s):
        p = clean(part)
        if p:
            p = FAMILY_FIX.get(p.lower(), p[0].upper() + p[1:])
            toks.append(p)
    return dedupe(toks)


desc = OrderedDict()


def add_desc(label, family, modality):
    lab = clean(label)
    if not lab:
        return
    k = fold(lab)
    d = desc.setdefault(k, dict(label=lab, fam=[], mod=set()))
    d["fam"] = dedupe(d["fam"] + family_tokens(family))
    d["mod"].add(modality)


for _, r in OA.iterrows():
    add_desc(r["Descriptor"], r["Descriptor Family"], "odor_aroma")
for _, r in EV.iterrows():
    add_desc(r["descriptor"], r["descriptor_family"], "odor_aroma")
for _, r in TA.iterrows():
    add_desc(r["Descriptor"], r["Descriptor Family / Category"], "taste")
for _, r in TR.iterrows():
    add_desc(r["Descriptor"], r["Descriptor Family / Category"], "trigeminal")
for _, r in TX.iterrows():
    add_desc(r["Descriptor"], r["Descriptor Family / Category"], "texture")

desc_rows, dalias_rows, dfam_rows, DESC_ID = [], [], [], {}
for i, (k, d) in enumerate(sorted(desc.items(), key=lambda kv: kv[0]), start=1):
    did = f"DS_{i:04d}"
    DESC_ID[k] = did
    fams = d["fam"]
    fl = {f.lower() for f in fams}
    terms = dedupe([clean(t) for t in d["label"].split("/") if clean(t)])
    desc_rows.append(dict(
        descriptor_id=did, descriptor_label=d["label"],
        n_terms=len(terms),
        family_l1_as_in_source=fams[0] if fams else None,
        n_family_tokens=len(fams),
        in_odor_aroma="odor_aroma" in d["mod"], in_taste="taste" in d["mod"],
        in_trigeminal="trigeminal" in d["mod"], in_texture="texture" in d["mod"],
        is_off_flavor=bool(fl & {"off-flavor", "defect", "oxidized", "rancid"}),
        family_is_general_or_character=bool(fams) and fl <= NON_AROMA_FAMILIES,
        in_master_sheet=any(fold(x) == k for x in OA["Descriptor"]),
    ))
    for t in terms:
        dalias_rows.append(dict(descriptor_id=did, term=t))
    for j, f in enumerate(fams, start=1):
        dfam_rows.append(dict(descriptor_id=did, family_token=f, order_in_source=j))
dim_descriptor = pd.DataFrame(desc_rows)

# --- Fase 3: ontología de aroma (Bérodier et al. 1997 + Drake et al. 2001) ---
_dcols = ["is_aroma_target", "aroma_family", "berodier_family_fr", "berodier_subfamily", "aroma_terms",
          "berodier_term", "drake_term", "split_terms", "harmonization_status", "harmonization_criterion"]
for c in _dcols:
    dim_descriptor[c] = None
_missing = []
for i, r in dim_descriptor.iterrows():
    if not r.in_odor_aroma:
        continue
    d = HD.DESCRIPTORS.get(r.descriptor_label)
    if d is None:
        _missing.append(r.descriptor_label)
        continue
    es, l1, l2, l3, bt, dt, sep, est, why = d
    if dt and dt not in HD.DRAKE_TERMS:
        raise ValueError(f"Término de Drake no verificado: {dt}")
    if es == "sí" and l1 not in HD.L1:
        raise ValueError(f"Familia Bérodier no válida: {l1}")
    dim_descriptor.loc[i, _dcols] = [es == "sí", HD.L1.get(l1) if es == "sí" else None, l1, l2, l3, bt, dt,
                                     sep == "sí", est, why]
if _missing:
    raise ValueError(f"Descriptores de aroma sin decisión: {_missing}")
descriptor_term = pd.DataFrame(dalias_rows)
descriptor_family = pd.DataFrame(dfam_rows)


def descriptor_id(label):
    return DESC_ID.get(fold(label))


# ----------------------------------------------------------------------------
# 4. RUTAS BIOQUÍMICAS (dim_pathway)
# ----------------------------------------------------------------------------
pw = Counter()
for v in EV["biochemical pathway"].dropna():
    pw[clean(v)] += 1
for v in OA["Possible biochemical pathway"].dropna():
    for t in split_list(v):
        pw[t] += 0
PW_ID = {}
pw_rows = []
for i, p in enumerate(sorted(pw, key=fold), start=1):
    PW_ID[fold(p)] = f"PW_{i:02d}"
    pw_rows.append(dict(pathway_id=f"PW_{i:02d}", pathway_label=p,
                        is_unassigned=fold(p) == "not assigned", n_evidence=pw[p]))
dim_pathway = pd.DataFrame(pw_rows)

pathway_steps = BP.rename(columns={
    "pathway": "pathway_group", "substrate or precursor": "substrate_or_precursor",
    "step / reaction": "step_or_reaction", "enzyme or microorganism": "enzyme_or_microorganism",
    "product": "product", "resulting compound family": "resulting_compound_family",
    "figure": "figure_in_source", "source": "source_raw"}).copy()
for c in pathway_steps.columns:
    pathway_steps[c] = pathway_steps[c].map(clean)
pathway_steps.insert(0, "step_id", [f"PS_{i:03d}" for i in range(1, len(pathway_steps) + 1)])
pathway_steps["source_id"] = pathway_steps["source_raw"].map(lambda s: "|".join(source_ids(s)) or None)

# ----------------------------------------------------------------------------
# 5. QUESOS  (dim_cheese + cheese_alias)
# ----------------------------------------------------------------------------
# Mapeo explícito de nombres crudos -> (nombre estándar, calificador de muestra, tipo).
# Tipos: specific | generic_category | multi_cheese | not_cheese | unresolved
# Solo se corrigen erratas/variantes evidentes; el texto original se conserva siempre.
S, G, M, N, U = "specific", "generic_category", "multi_cheese", "not_cheese", "unresolved"
CHEESE_MAP = {
    # erratas y variantes ortográficas
    "mozzarrella": ("Mozzarella", None, S),
    "grana tretino": ("Grana Trentino", None, S),
    "gruyere": ("Gruyère", None, S),
    "emmentaler": ("Emmental", None, S),
    "swiss (emmental)": ("Emmental", "Swiss", S),
    "parmigiano-reggiano": ("Parmigiano Reggiano", None, S),
    "parmesan (parmigiano-reggiano)": ("Parmigiano Reggiano", None, S),
    "fossa cheese": ("Formaggio di Fossa", None, S),
    "cottage": ("Cottage", None, S),
    "cream cheese": ("Cream cheese", None, S),
    "gbejna": ("Ġbejna", None, S),
    # variantes con perfil propio en Cheese Profiles
    "aged cheddar": ("Cheddar (aged)", None, S),
    "cheddar (aged)": ("Cheddar (aged)", None, S),
    "aged cheddar (with nutty note)": ("Cheddar (aged)", "with nutty note", S),
    "low-fat cheddar": ("Cheddar (low-fat)", None, S),
    "cheddar (low-fat)": ("Cheddar (low-fat)", None, S),
    "cheddar (british farmhouse)": ("Farmhouse Cheddar", "British", S),
    "goat milk cheddar": ("Goat Cheddar", None, S),
    "goat cheddar": ("Goat Cheddar", None, S),
    "buffalo mozzarella": ("Mozzarella (buffalo)", None, S),
    "mozzarella (buffalo)": ("Mozzarella (buffalo)", None, S),
    "water buffalo mozzarella": ("Mozzarella (buffalo)", None, S),
    "formaella (smoked)": ("Formaella", "smoked", S),
    "smoked formaella": ("Formaella", "smoked", S),
    # calificadores de muestra (se guardan aparte)
    "mature cheddar": ("Cheddar", "mature", S),
    "british cheddar": ("Cheddar", "British", S),
    "cheddar (0–15 months)": ("Cheddar", "0–15 months", S),
    "cheddar (curd slurries)": ("Cheddar", "curd slurries", S),
    "cheddar (full fat)": ("Cheddar", "full fat", S),
    "cheddar (ireland, united kingdom and usa; 20 samples)": ("Cheddar", "Ireland, United Kingdom and USA; 20 samples", S),
    "cheddar (mild, regular and low-fat)": ("Cheddar", "mild, regular and low-fat", S),
    "cheddar (regular//low fat)": ("Cheddar", "regular//low fat", S),
    "cheddar (rind)": ("Cheddar", "rind", S),
    "aged gouda": ("Gouda", "aged", S),
    "camembert (mould surface-ripened)": ("Camembert", "mould surface-ripened", S),
    "feta-type (bovine milk)": ("Feta-type", "bovine milk", G),
    "feta-type": ("Feta-type", None, G),
    "gorgonzola (natural)": ("Gorgonzola", "natural", S),
    "gorgonzola (natural//creamy)": ("Gorgonzola", "natural//creamy", S),
    "grana padano (12 months)": ("Grana Padano", "12 months", S),
    "mozzarella (bovine)": ("Mozzarella", "cow milk", S),
    "mozzarella (cow)": ("Mozzarella", "cow milk", S),
    "bovine mozzarella": ("Mozzarella", "cow milk", S),
    "pecorino (6 months)": ("Pecorino", "6 months", S),
    "ragusano (4 months)": ("Ragusano", "4 months", S),
    "ragusano (8 months)": ("Ragusano", "8 months", S),
    "roncal (type, sheep milk)": ("Roncal", "type, sheep milk", S),
    "sainte-maure (goat)": ("Sainte-Maure", "goat", S),
    "majorero (goat)": ("Majorero", "goat", S),
    "palmero (smoked)": ("Palmero", "smoked", S),
    "teleme (sheep and goat)": ("Teleme", "sheep and goat", S),
    "teleme (sheep milk)": ("Teleme", "sheep milk", S),
    "bouton de culotte (goat)": ("Bouton de Culotte", "goat", S),
    "goat (bouton de culotte)": ("Bouton de Culotte", "goat", S),
    "castelo branco (dop)": ("Castelo Branco", "DOP", S),
    "chevre (cottage cheese model)": ("Chèvre", "cottage cheese model", S),
    "chevre (fresh goat cheese)": ("Chèvre", "fresh goat cheese", S),
    "milk fan (artisanal cheese from yunnan, china)": ("Milk fan", "artisanal, Yunnan, China", S),
    "milk fan (yunnan, china)": ("Milk fan", "Yunnan, China", S),
    "fresco (sonora, mexico)": ("Fresco", "Sonora, Mexico", S),
    "swiss tilsit red label": ("Tilsit", "Swiss red label", S),
    "smoked cheese (polish breeds, beskid niski)": ("Polish smoked cheese", "Polish breeds, Beskid Niski", S),
    "polish smoked cheese": ("Polish smoked cheese", None, S),
    # categorías genéricas
    "aged cheeses": ("Aged cheese (generic)", None, G),
    "aged cheeses (generic)": ("Aged cheese (generic)", None, G),
    "aged cheese (generic)": ("Aged cheese (generic)", None, G),
    "aged cheeses (camembert, cheddar, gruyere)": ("Aged cheese (generic)", "Camembert, Cheddar, Gruyère", G),
    "aged cheeses (gruyere, gouda, american processed, parmigiano, swiss)": ("Aged cheese (generic)", "Gruyère, Gouda, American processed, Parmigiano, Swiss", G),
    "blue": ("Blue cheese (generic)", None, G),
    "blue cheese": ("Blue cheese (generic)", None, G),
    "blue cheeses": ("Blue cheese (generic)", None, G),
    "blue cheeses (generic)": ("Blue cheese (generic)", None, G),
    "blue cheeses (roquefort)": ("Blue cheese (generic)", "Roquefort", G),
    "blue cheeses (roquefort, cabrales, gorgonzola…)": ("Blue cheese (generic)", "Roquefort, Cabrales, Gorgonzola…", G),
    "blue-veined cheeses": ("Blue cheese (generic)", None, G),
    "blue and hard italian cheeses": ("Blue and hard Italian cheeses", None, G),
    "hard italian cheeses": ("Hard Italian cheeses (generic)", None, G),
    "brined cheeses": ("Brined cheese (generic)", None, G),
    "brined cheeses (feta and similar)": ("Brined cheese (generic)", "Feta and similar", G),
    "cheeses (generic)": ("Cheese (generic)", None, G),
    "cheeses in general": ("Cheese (generic)", None, G),
    "cheeses in general (ch. 7)": ("Cheese (generic)", "ch. 7", G),
    "cheeses made with rennet paste": ("Cheeses made with rennet paste (generic)", None, G),
    "dairy products (generic)": ("Dairy products (generic)", None, G),
    "enzyme-modified cheese (emc)": ("Enzyme-modified cheese (EMC)", None, G),
    "emc (cheddar, swiss, romano, mozzarella, provolone, feta, parmesan, blue, gouda, gruyere, colby, brick)": ("Enzyme-modified cheese (EMC)", "Cheddar, Swiss, Romano, mozzarella, provolone, feta, Parmesan, blue, Gouda, Gruyère, Colby, brick", G),
    "goat": ("Goat cheese (generic)", None, G),
    "goat cheese": ("Goat cheese (generic)", None, G),
    "goat cheeses": ("Goat cheese (generic)", None, G),
    "goat cheeses (generic)": ("Goat cheese (generic)", None, G),
    "goat cheese (unspecified)": ("Goat cheese (generic)", None, G),
    "goat milk cheeses": ("Goat cheese (generic)", None, G),
    "raw goat milk cheese": ("Goat cheese (generic)", "raw milk", G),
    "goat cheeses (sainte-maure, garrotxa, majorero, ibores, darfiyeh)": ("Goat cheese (generic)", "Sainte-Maure, Garrotxa, Majorero, Ibores, Darfiyeh", G),
    "goat cheeses (sainte-maure, garrotxa, majorero, ibores, darfiyeh…)": ("Goat cheese (generic)", "Sainte-Maure, Garrotxa, Majorero, Ibores, Darfiyeh…", G),
    "goat and sheep cheeses": ("Goat and sheep cheese (generic)", None, G),
    "goat and sheep milk cheeses": ("Goat and sheep cheese (generic)", None, G),
    "goat and sheep milk cheeses (generic)": ("Goat and sheep cheese (generic)", None, G),
    "goat/sheep cheeses": ("Goat and sheep cheese (generic)", None, G),
    "goat and ewe cheeses": ("Goat and sheep cheese (generic)", None, G),
    "sheep milk cheese": ("Sheep cheese (generic)", None, G),
    "sheep milk cheese (argentina)": ("Sheep cheese (generic)", "Argentina", G),
    "grana": ("Grana (generic)", None, G),
    "grana cheeses": ("Grana (generic)", None, G),
    "grana (generic)": ("Grana (generic)", None, G),
    "grana (gp / pr / gt)": ("Grana (generic)", "GP / PR / GT", G),
    "grana (grana padano, parmigiano reggiano, grana trentino)": ("Grana (generic)", "Grana Padano, Parmigiano Reggiano, Grana Trentino", G),
    "hard cheeses": ("Hard cheese (generic)", None, G),
    "hard swiss cheese": ("Swiss-type (generic)", "hard", G),
    "swiss hard": ("Swiss-type (generic)", "hard", G),
    "swiss hard cheese": ("Swiss-type (generic)", "hard", G),
    "swiss": ("Swiss-type (generic)", None, G),
    "swiss cheeses": ("Swiss-type (generic)", None, G),
    "swiss-type cheese": ("Swiss-type (generic)", None, G),
    "swiss-type cheeses": ("Swiss-type (generic)", None, G),
    "swiss-type (generic)": ("Swiss-type (generic)", None, G),
    "mold cheeses (camembert, blue cheeses)": ("Mold-ripened cheese (generic)", "Camembert, blue cheeses", G),
    "white-mold cheeses (camembert)": ("White-mold cheese (generic)", "Camembert", G),
    "pasta filata": ("Pasta filata (generic)", None, G),
    "pasta filata (generic)": ("Pasta filata (generic)", None, G),
    "processed cheese / cream cheese": ("Processed cheese (generic)", "processed cheese / cream cheese", G),
    "processed cheeses": ("Processed cheese (generic)", None, G),
    "semi-hard cheeses (gouda, etc.)": ("Semi-hard cheese (generic)", "Gouda, etc.", G),
    "sheep cheeses with vegetable rennet (la serena, torta del casar…)": ("Sheep/goat cheeses with vegetable rennet", "sheep; La Serena, Torta del Casar…", G),
    "sheep/goat cheeses with vegetable rennet": ("Sheep/goat cheeses with vegetable rennet", None, G),
    "sheep/goat cheeses with vegetable rennet (la serena, torta del casar, serra da estrela…)": ("Sheep/goat cheeses with vegetable rennet", "La Serena, Torta del Casar, Serra da Estrela…", G),
    "ewe/goat cheeses (vegetable rennet)": ("Sheep/goat cheeses with vegetable rennet", None, G),
    "sheep/goat cheeses with lamb/kid rennet paste": ("Sheep/goat cheeses with lamb/kid rennet paste", None, G),
    "sheep/goat cheeses with lamb/kid rennet paste (idiazabal, pecorino, teleme…)": ("Sheep/goat cheeses with lamb/kid rennet paste", "Idiazabal, Pecorino, Teleme…", G),
    "ewe/goat cheeses (rennet paste)": ("Sheep/goat cheeses with lamb/kid rennet paste", None, G),
    "smear-ripened": ("Smear-ripened cheese (generic)", None, G),
    "smear-ripened (generic)": ("Smear-ripened cheese (generic)", None, G),
    "surface-ripened cheeses": ("Surface-ripened cheese (generic)", None, G),
    "washed-rind cheeses": ("Washed-rind cheese (generic)", None, G),
    "washed-rind cheeses (generic)": ("Washed-rind cheese (generic)", None, G),
    "smoked": ("Smoked cheese (generic)", None, G),
    "smoked cheese": ("Smoked cheese (generic)", None, G),
    "smoked cheeses (generic)": ("Smoked cheese (generic)", None, G),
    "smoked cheeses (san simon da costa, idiazabal, palmero, herreno…)": ("Smoked cheese (generic)", "San Simón da Costa, Idiazabal, Palmero, Herreño…", G),
    "soft cheeses (cottage, feta, domiati)": ("Soft cheese (generic)", "Cottage, Feta, Domiati", G),
    "soft cheeses (with l. plantarum / l. casei)": ("Soft cheese (generic)", "with L. plantarum / L. casei", G),
    "soft cheese (generic)": ("Soft cheese (generic)", None, G),
    "young cheese (generic)": ("Young cheese (generic)", None, G),
    "fresh cheese (generic)": ("Fresh cheese (generic)", None, G),
    "dutch-type (generic)": ("Dutch-type (generic)", None, G),
    # etiquetas con varios quesos (no se separan: el reparto no es explícito)
    "arzua-ulloa and tetilla": ("Arzúa-Ulloa and Tetilla", None, M),
    "blue cheese, camembert, cheddar, processed cheese": ("Blue cheese, Camembert, Cheddar, processed cheese", None, M),
    "blue cheese; emmental": ("Blue cheese; Emmental", None, M),
    "camembert; blue cheeses; cheddar": ("Camembert; blue cheeses; Cheddar", None, M),
    "cheddar, swiss, blue, grana/pecorino, camembert, cottage, limburger…": ("Cheddar, Swiss, blue, grana/pecorino, Camembert, Cottage, Limburger…", None, M),
    "cheddar; blue cheeses": ("Cheddar; blue cheeses", None, M),
    "cheddar; camembert": ("Cheddar; Camembert", None, M),
    "cottage cheese; swiss cheeses": ("Cottage cheese; Swiss cheeses", None, M),
    "edam, gouda, quarg, cottage": ("Edam, Gouda, Quarg, Cottage", None, M),
    "emmental / swiss cheeses": ("Emmental / Swiss cheeses", None, M),
    "idiazabal, fiore sardo, feta, pecorino foggiano": ("Idiazabal, Fiore Sardo, Feta, Pecorino Foggiano", None, M),
    "limburger; gruyere and emmental": ("Limburger; Gruyère and Emmental", None, M),
    "parmesan, grana padano": ("Parmesan, Grana Padano", None, M),
    "parmesan, grana padano and pecorino": ("Parmesan, Grana Padano and Pecorino", None, M),
    "toma piemontese, cantal, idiazabal": ("Toma Piemontese, Cantal, Idiazabal", None, M),
    "various (brie, edam … roquefort)": ("Various (Brie, Edam … Roquefort)", None, M),
    "various (gouda, camembert, la serena)": ("Various (Gouda, Camembert, La Serena)", None, M),
    "roquefort vs cow-milk blue cheeses": ("Roquefort vs cow-milk blue cheeses", None, M),
    "swiss vs cheddar": ("Swiss vs Cheddar", None, M),
    "castelmagno / fossa": ("Castelmagno / Formaggio di Fossa", None, M),
    "gruyere / parmesan / proosdij": ("Gruyère / Parmesan / Proosdij", None, M),
    "quarg / cottage": ("Quarg / Cottage", None, M),
    # no son quesos / sin resolver
    "black tea": ("Black tea", None, N),
    "cacao": ("Cacao", None, N),
    "not applicable (milk)": ("Milk (not cheese)", None, N),
    "check in the table": (None, None, U),
    "european": ("European (unspecified)", None, U),
}


CHEESE_MAP = {fold(k): v for k, v in CHEESE_MAP.items()}

# forma de mostrar por defecto: la variante con mayúsculas vista en las hojas de datos
DISPLAY = {}
for _src_vals in (EV["cheese_type"].dropna().map(split_list).explode(),
                  PV["cheese"].dropna(), OA["Cheese Type"].dropna().map(split_list).explode()):
    for _v in _src_vals:
        _v = clean(_v)
        if _v and (fold(_v) not in DISPLAY or (DISPLAY[fold(_v)].islower() and not _v.islower())):
            DISPLAY[fold(_v)] = _v


def _cheese_std_v1(raw):
    r = clean(raw)
    if r is None:
        return None, None, None
    k = fold(r)
    if k in CHEESE_MAP:
        return CHEESE_MAP[k]
    # por defecto: mismo nombre (forma vista en los datos), con mayúscula inicial
    r = DISPLAY.get(k, r)
    return r[0].upper() + r[1:], None, S


# --- Fase 1.1: correcciones de equivalencias (scripts/harmonization_decisions.py) ---
ALIAS_OVR = {}   # fold(nombre crudo) -> (nombre nuevo, tipo nuevo)
TYPE_OVR = {}    # fold(nombre estándar nuevo) -> tipo
RENAMED = {}     # nombre estándar v1 -> nombre estándar v2
for _raw, (_name, _typ, _st, _orig, _ref, _why) in HD.ALIAS_DECISIONS.items():
    _old_std, _q, _t = _cheese_std_v1(_raw)
    _new = _name or _old_std
    if _new == _old_std and (_typ or _t) == _t:
        continue  # decisión explícita sin cambio de valor (p. ej. Parmesan)
    ALIAS_OVR[fold(_raw)] = (_new, _typ or _t)
    if _typ and _new:
        TYPE_OVR[fold(_new)] = _typ
    if _old_std and _new and _new != _old_std:
        RENAMED.setdefault(_old_std, _new)
    CORR_LOG.append(dict(fase="1.1", tabla="cheese_alias", clave=_raw, campo="cheese_name_std / label_type",
                         valor_anterior=f"{_old_std} / {_t}", valor_nuevo=f"{_new} / {_typ or _t}",
                         estado=_st, referencia=HD.REF.get(_ref, ""), criterio=_why))


def cheese_std(raw):
    std, q, t = _cheese_std_v1(raw)
    if std is None:
        return std, q, t
    k = fold(raw)
    if k in ALIAS_OVR:
        std, t = ALIAS_OVR[k]
    if fold(std) in TYPE_OVR:
        t = TYPE_OVR[fold(std)]
    return std, q, t


# perfiles (primero los que no fueron renombrados, para que un alias reasignado
# no sustituya el perfil propio de una categoría)
profile_by_std = {}
_cp_order = sorted(CP.index, key=lambda i: fold(CP.loc[i, "cheese (cheese_type_clean)"]) in ALIAS_OVR)
for _, r in CP.loc[_cp_order].iterrows():
    std, q, t = cheese_std(r["cheese (cheese_type_clean)"])
    if std in profile_by_std:
        issue("Cheese Profiles", r["cheese (cheese_type_clean)"], "cheese", "Perfil duplicado (se usa el primero)", std)
        continue
    profile_by_std[std] = r

# todos los nombres crudos
raw_names = Counter()
for v in EV["cheese_type"].dropna():
    for t in split_list(v):
        raw_names[t] += 1
for v in PV["cheese"].dropna():
    raw_names[clean(v)] += 1
for v in OA["Cheese Type"].dropna():
    for t in split_list(v):
        raw_names[t] += 0
for v in CP["cheese (cheese_type_clean)"]:
    raw_names[clean(v)] += 0

std_info = OrderedDict()
alias_rows = []
for raw in raw_names:
    std, q, t = cheese_std(raw)
    alias_rows.append(dict(cheese_label_raw=raw, cheese_name_std=std, sample_qualifier=q, label_type=t))
    if std is None:
        issue("cheese_alias", raw, "cheese", "Nombre de queso sin resolver en la fuente", raw)
        continue
    info = std_info.setdefault(std, dict(type=t))
    if t != S and info["type"] == S:
        info["type"] = t

PARENTS = {child: v[0] for child, v in HD.PARENTS.items()}
for p in PARENTS.values():
    std_info.setdefault(p, dict(type=S))
for p in profile_by_std:
    std_info.setdefault(p, dict(type=cheese_std(p)[2] or S))

CHEESE_ID = {}
for i, std in enumerate(sorted(std_info, key=fold), start=1):
    CHEESE_ID[std] = f"CH_{i:03d}"

cheese_alias = pd.DataFrame(alias_rows)
cheese_alias.insert(0, "cheese_id", cheese_alias["cheese_name_std"].map(CHEESE_ID))
cheese_alias = cheese_alias.sort_values(["cheese_id", "cheese_label_raw"], na_position="last")


# ----------------------------------------------------------------------------
# 6. PARSERS DE VARIABLES DE PRODUCCIÓN (texto -> columnas)
#    Regla: 1 = mencionado en la fuente; NA = no mencionado / no especificado.
# ----------------------------------------------------------------------------
def unknown(s):
    s = fold(s)
    return s is None or s.startswith("not specified")


def parse_milk(s):
    out = dict(milk_species_raw=clean(s), milk_cow=None, milk_sheep=None, milk_goat=None,
               milk_buffalo=None, milk_species_logic=None)
    if unknown(s):
        out["milk_species_logic"] = "unknown"
        return out
    f = fold(s)
    sp = {"milk_cow": r"\bcow|bovine", "milk_sheep": r"sheep|ewe", "milk_goat": r"goat",
          "milk_buffalo": r"buffalo"}
    found = [k for k, pat in sp.items() if re.search(pat, f)]
    for k in found:
        out[k] = 1
    if " vs " in f:
        logic = "comparison"
    elif len(found) <= 1:
        logic = "single"
    elif re.search(r"\bor\b", f):
        logic = "alternatives"
    elif re.search(r"\band\b|mixed|≥|%", f):
        logic = "mixture"
    else:
        logic = "mixture_or_alternatives"
    out["milk_species_logic"] = logic
    return out


def parse_heat(s):
    f = fold(s)
    if unknown(s):
        v = "unknown"
    elif " vs " in f:
        v = "comparison"
    elif "raw" in f and "pasteur" in f:
        v = "raw_or_pasteurized"
    elif "raw" in f and "thermi" in f:
        v = "raw_or_thermized"
    elif "raw" in f:
        v = "raw"
    elif "pasteur" in f:
        v = "pasteurized"
    elif "thermi" in f:
        v = "thermized"
    else:
        v = "other"
    return dict(milk_heat_treatment_raw=clean(s), milk_heat_treatment=v)


CULTURE_FLAGS = OrderedDict([
    # coagulante
    ("coag_calf_rennet", r"calf rennet"),
    ("coag_rennet_paste", r"rennet paste"),
    ("coag_lamb_rennet", r"\blamb\b.*rennet|lamb/kid rennet"),
    ("coag_kid_rennet", r"\bkid\b.*rennet|lamb/kid rennet"),
    ("coag_vegetable_rennet", r"vegetable rennet|cynara"),
    ("coag_animal_rennet_unspecified", r"animal rennet"),
    ("coag_lactic_acid", r"lactic coagulation|acid coagulation"),
    # enzimas
    ("enz_pregastric_esterase_or_lipase", r"pregastric|\bpge\b"),
    ("enz_lipase_mentioned", r"lipase"),
    # cultivos
    ("cult_starter_mentioned", r"starter"),
    ("cult_adjunct_mentioned", r"adjunct"),
    ("cult_natural_whey", r"natural whey culture"),
    ("cult_indigenous_lab", r"indigenous lab|natural microflora"),
    ("cult_mesophilic", r"mesophilic"),
    ("cult_citrate_positive", r"citrate"),
    ("cult_diacetylactis", r"diacetylactis"),
    ("cult_leuconostoc", r"leuconostoc"),
    ("cult_lactobacillus", r"l\. plantarum|l\. casei|lactobacill|paracasei"),
    ("cult_probiotic", r"probiotic"),
    ("cult_propionibacteria", r"propionibacter|propionic|freudenreichii|shermanii"),
    # mohos y flora de superficie
    ("mold_p_roqueforti", r"roqueforti"),
    ("mold_p_camemberti", r"camemberti"),
    ("mold_penicillium_unspecified", r"surface mold|penicillium(?! (roqueforti|camemberti))"),
    ("flora_washed_rind_smear", r"washed-rind|linens|brevibacterium|coryneform|smear"),
])


def parse_culture(s):
    out = dict(rennet_culture_raw=clean(s))
    f = fold(s) or ""
    for k, pat in CULTURE_FLAGS.items():
        hit = not unknown(s) and re.search(pat, f)
        if k == "cult_adjunct_mentioned" and re.search(r"without adjunct", f):
            hit = False
        out[k] = 1 if hit else None
    # cuajo sin especificar: menciona 'rennet' pero ningún tipo concreto
    typed = any(out[k] for k in ("coag_calf_rennet", "coag_rennet_paste", "coag_lamb_rennet",
                                 "coag_kid_rennet", "coag_vegetable_rennet",
                                 "coag_animal_rennet_unspecified"))
    out["coag_rennet_unspecified"] = 1 if ("rennet" in f and not typed) else None
    return out


OTHER_FLAGS = OrderedDict([
    ("proc_smoked", r"smok"),
    ("proc_pasta_filata", r"pasta filata"),
    ("proc_brine", r"brine"),
    ("proc_low_fat", r"low fat"),
    ("proc_acid_coagulation", r"acid coagulation"),
    ("proc_natural_creaming", r"natural creaming"),
    ("proc_no_silage_feed", r"no silage"),
    ("proc_cooked_or_scalded", r"cook|scald"),
    ("proc_milk_salting", r"salting of the milk"),
    ("proc_curd_salting", r"curd salting"),
    ("proc_light_pressing", r"light pressing"),
    ("proc_transhumance_milk", r"transhumance"),
    ("proc_wooden_utensils", r"wooden utensils"),
    ("proc_artisanal_handmade", r"artisanal|handmade"),
])


def parse_other(s):
    out = dict(other_process_factor_raw=clean(s))
    f = fold(s) or ""
    for k, pat in OTHER_FLAGS.items():
        out[k] = 1 if re.search(pat, f) else None
    m = re.search(r"(\d+)\s*°\s*c", f)
    out["curd_cooking_temp_c"] = float(m.group(1)) if (m and "cook" in f) else None
    return out


UNIT_DAYS = {"day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30}


def _n(x):
    return float(x.replace(",", "."))


def parse_ripening(s):
    """Convierte texto de maduración a días (1 mes = 30 d, 1 semana = 7 d)."""
    raw = clean(s)
    out = dict(ripening_raw=raw, ripening_days_min=None, ripening_days_max=None,
               ripening_label=None)
    if unknown(s):
        out["ripening_label"] = "unknown"
        return out
    f = fold(s).replace("–", "-").replace("—", "-")
    if f.startswith("fresh"):
        out["ripening_label"] = "fresh"
        out["ripening_days_min"] = 0
    for w in ("aged", "long", "young", "extended"):
        if f.startswith(w):
            out["ripening_label"] = w
    U = r"(day|days|week|weeks|month|months)"
    # rango "A-B unidad"
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*" + U, f)
    if m and not re.search(r"≥\s*\d+\s*-", f):
        k = UNIT_DAYS[m.group(3)]
        out["ripening_days_min"], out["ripening_days_max"] = _n(m.group(1)) * k, _n(m.group(2)) * k
        return out
    # "A unidad to (>) B unidad"  /  "fresh to B"
    m = re.search(r"(?:(\d+(?:[.,]\d+)?)\s*" + U + r"|fresh)\s+to\s+(>\s*)?(\d+(?:[.,]\d+)?)\s*" + U, f)
    if m:
        lo = _n(m.group(1)) * UNIT_DAYS[m.group(2)] if m.group(1) else 0
        out["ripening_days_min"] = lo
        if not m.group(3):
            out["ripening_days_max"] = _n(m.group(4)) * UNIT_DAYS[m.group(5)]
        return out
    # "≥ N", "> N", "fresh or > N"
    m = re.search(r"[≥>]\s*(\d+(?:[.,]\d+)?)\s*(?:-\s*\d+\s*)?" + U, f)
    if m:
        if out["ripening_days_min"] is None:
            out["ripening_days_min"] = _n(m.group(1)) * UNIT_DAYS[m.group(2)]
        return out
    m = re.search(r"up to\s*(\d+(?:[.,]\d+)?)\s*" + U, f)
    if m:
        out["ripening_days_max"] = _n(m.group(1)) * UNIT_DAYS[m.group(2)]
        return out
    m = re.search(r"(?:peak at\s*)?(?:day\s*(\d+)|(\d+(?:[.,]\d+)?)\s*" + U + ")", f)
    if m:
        d = _n(m.group(1)) if m.group(1) else _n(m.group(2)) * UNIT_DAYS[m.group(3)]
        if out["ripening_label"] != "fresh":
            out["ripening_days_min"] = out["ripening_days_max"] = d
        return out
    return out


def ripening_class(mn, mx, label):
    if label == "fresh" and (mx is None or mx <= 15):
        return "fresh"
    if mn is None or mx is None:
        return None
    mid = (mn + mx) / 2
    for lim, c in [(30, "lt_1m"), (90, "1_3m"), (180, "3_6m"), (365, "6_12m"), (730, "12_24m")]:
        if mid <= lim:
            return c
    return "gt_24m"


def parse_context(milk, heat, cult, ripe, other):
    d = {}
    d.update(parse_milk(milk))
    d.update(parse_heat(heat))
    d.update(parse_culture(cult))
    rp = parse_ripening(ripe)
    d.update(rp)
    d["ripening_class"] = ripening_class(rp["ripening_days_min"], rp["ripening_days_max"], rp["ripening_label"])
    d.update(parse_other(other))
    return d


# dim_cheese
ch_rows = []
for std in sorted(std_info, key=fold):
    r = profile_by_std.get(std)
    row = dict(cheese_id=CHEESE_ID[std], cheese_name_std=std,
               parent_cheese_id=CHEESE_ID.get(PARENTS.get(std)),
               label_type=std_info[std]["type"],
               has_profile=r is not None,
               profile_name_original=clean(r["cheese (cheese_type_clean)"]) if r is not None else None)
    if r is not None:
        row.update(parse_context(r["milk (species)"], r["milk treatment"], r["rennet / culture"],
                                 r["ripening time"], r["other process factor"]))
        row["profile_source_raw"] = clean(r["source"])
        row["profile_source_ids"] = "|".join(source_ids(r["source"])) or None
        row["profile_from_label_only"] = "cheese label in the source" in (fold(r["source"]) or "")
    ch_rows.append(row)
dim_cheese = pd.DataFrame(ch_rows)
ctx_cols = [c for c in dim_cheese.columns if c not in
            ("cheese_id", "cheese_name_std", "parent_cheese_id", "label_type", "has_profile",
             "profile_name_original", "profile_source_raw", "profile_source_ids", "profile_from_label_only")]
known_cols = ["milk_species_logic", "milk_heat_treatment", "rennet_culture_raw", "ripening_days_min",
              "ripening_days_max", "other_process_factor_raw"]


def completeness(row):
    """Fracción de los 4 bloques básicos conocidos: leche, tratamiento, cuajo/cultivo, maduración."""
    def ok(v):
        return v is not None and not (isinstance(v, float) and np.isnan(v))
    vals = [ok(row.get("milk_species_logic")) and row.get("milk_species_logic") != "unknown",
            ok(row.get("milk_heat_treatment")) and row.get("milk_heat_treatment") != "unknown",
            ok(row.get("rennet_culture_raw")) and not unknown(row.get("rennet_culture_raw")),
            ok(row.get("ripening_days_min")) or ok(row.get("ripening_days_max"))
            or row.get("ripening_label") in ("fresh", "aged", "long", "young")]
    return round(sum(vals) / len(vals), 2)


dim_cheese["profile_completeness"] = [completeness(r) if r["has_profile"] else 0.0
                                      for r in dim_cheese.to_dict("records")]

# ----------------------------------------------------------------------------
# 6b. FASES 1.4 y 2 — familia tecnológica, país/DOP y producción del TIPO de queso
#     (valores de especificación; nunca se asignan a muestras: van en columnas spec_*)
# ----------------------------------------------------------------------------
V1_NAMES = {_cheese_std_v1(r)[0] for r in raw_names} | {_cheese_std_v1(p)[0] for p in CP["cheese (cheese_type_clean)"]}


def v2_lookup(dct):
    """Traduce claves con nombre v1 a nombre v2 cuando el queso fue renombrado,
    salvo que el nombre v2 ya existiera en v1 como otro queso (no se mezclan datos)."""
    out = dict(dct)
    for old, new in RENAMED.items():
        if old in dct and new not in dct and new not in V1_NAMES:
            out[new] = dct[old]
    return out


FAM = v2_lookup(HD.CHEESE_FAMILY)
fam_cols = ["cheese_family", "secondary_technology", "cheese_family_status", "cheese_family_reference",
            "cheese_family_criterion", "country_iso", "pdo_pgi", "pdo_pgi_status", "pdo_pgi_reference"]
for c in fam_cols:
    dim_cheese[c] = None
for i, r in dim_cheese.iterrows():
    d = FAM.get(r.cheese_name_std)
    if d:
        dim_cheese.loc[i, fam_cols] = [d[0], d[1] or None, d[2], HD.REF.get(d[3], "") if d[3] else None,
                                       d[4], d[5], d[6], d[7], HD.REF.get(d[8], "") if d[8] else None]
bad_fam = set(dim_cheese.cheese_family.dropna()) - set(HD.FAMILIES)
if bad_fam:
    raise ValueError(f"Familias no válidas: {bad_fam}")

# producción del tipo (spec_*): por defecto el valor del perfil del Excel; después, las decisiones de la Fase 2
PROD = {}
for (cheese, block), v in HD.PRODUCTION.items():
    PROD.setdefault(cheese, {})[block] = v
PROD = v2_lookup(PROD)


def _known(v):
    return v is not None and not (isinstance(v, float) and np.isnan(v))


SPEC_ROWS = {}
for i, r in dim_cheese.iterrows():
    src = r.get("profile_source_raw") if r.has_profile else None
    exc = (HD.V, HD.EXC, src, "Valor del perfil de producción del Excel (fuente citada allí).")
    none = (HD.N, HD.NONE, None, "El Excel no lo especifica y no se encontró fuente.")
    milk = r.get("milk_species_raw") if r.get("milk_species_logic") not in (None, "unknown") and _known(r.get("milk_species_logic")) else None
    heat = r.get("milk_heat_treatment") if _known(r.get("milk_heat_treatment")) and r.get("milk_heat_treatment") != "unknown" else None
    coag = r.get("rennet_culture_raw") if _known(r.get("rennet_culture_raw")) and not unknown(r.get("rennet_culture_raw")) else None
    rmin, rmax = r.get("ripening_days_min"), r.get("ripening_days_max")
    rmin = rmin if _known(rmin) else None
    rmax = rmax if _known(rmax) else None
    spec = {
        "leche": (milk,) + (exc if milk else none),
        "tratamiento_termico": (heat,) + (exc if heat else none),
        "cuajo_cultivo": (coag,) + (exc if coag else none),
        "maduracion": ((rmin, rmax),) + (exc if (rmin is not None or rmax is not None) else none),
    }
    for block, (val, est, orig, ref, why) in PROD.get(r.cheese_name_std, {}).items():
        if block == "maduracion":
            if val:
                a, _, b = val.partition("–")
                val = (float(a) if a else None, float(b) if b else None)
            else:
                val = (None, None)
        spec[block] = (val, est, orig, HD.REF.get(ref, "") if ref else None, why)
        CORR_LOG.append(dict(fase="2", tabla="dim_cheese", clave=r.cheese_name_std, campo=block,
                             valor_anterior=None, valor_nuevo=str(val), estado=est,
                             referencia=HD.REF.get(ref, "") if ref else "", criterio=why))
    SPEC_ROWS[r.cheese_name_std] = spec
    mval = spec["leche"][0]
    pm = parse_milk(mval) if mval else parse_milk(None)
    rmn, rmx = spec["maduracion"][0]
    out = dict(
        spec_milk=mval, spec_milk_cow=pm["milk_cow"], spec_milk_sheep=pm["milk_sheep"],
        spec_milk_goat=pm["milk_goat"], spec_milk_buffalo=pm["milk_buffalo"],
        spec_milk_status=spec["leche"][1], spec_milk_reference=spec["leche"][3],
        spec_heat_treatment=spec["tratamiento_termico"][0], spec_heat_status=spec["tratamiento_termico"][1],
        spec_heat_reference=spec["tratamiento_termico"][3],
        spec_coagulant_culture=spec["cuajo_cultivo"][0], spec_coagulant_status=spec["cuajo_cultivo"][1],
        spec_coagulant_reference=spec["cuajo_cultivo"][3],
        spec_ripening_days_min=rmn, spec_ripening_days_max=rmx,
        spec_ripening_class=ripening_class(rmn, rmx, "fresh" if rmx == 0 else None),
        spec_ripening_status=spec["maduracion"][1], spec_ripening_reference=spec["maduracion"][3],
    )
    out["spec_completeness"] = round(sum([out["spec_milk"] is not None, out["spec_heat_treatment"] is not None,
                                          out["spec_coagulant_culture"] is not None,
                                          rmn is not None or rmx is not None]) / 4, 2)
    for k, v in out.items():
        dim_cheese.loc[i, k] = v


# ----------------------------------------------------------------------------
# 7. EVIDENCIAS (fact_evidence + puentes)
# ----------------------------------------------------------------------------
STATUS_STD = {
    "CONFIRMED": "CONFIRMED_PRIMARY",
    "CONFIRMED (secondary)": "CONFIRMED_SECONDARY",
    "PROBABLE (text only)": "PROBABLE_TEXT_ONLY",
    "PROBABLE (table not legible)": "PROBABLE_TABLE_ILLEGIBLE",
    "NOT CONFIRMED (the source does not give the descriptor)": "NOT_CONFIRMED",
    "UNSUPPORTED": "UNSUPPORTED",
}
SCORE = {"CONFIRMED_PRIMARY": 1.0, "CONFIRMED_SECONDARY": 0.6, "PROBABLE_TEXT_ONLY": 0.4,
         "PROBABLE_TABLE_ILLEGIBLE": 0.4, "NOT_CONFIRMED": 0.0, "UNSUPPORTED": 0.0}
RV_KEYS = {"FD": r"\bFD\s*=?\s*([\d.]+)", "DF": r"\bDF\s*=\s*([\d.]+)",
           "OI": r"\bOI\s*=?\s*([\d.]+)", "OP": r"\bOP\s*=?\s*([\d.]+)",
           "c": r"\bc\s+([\d.]+)", "pct": r"%\s*([\d.]+)", "vol": r"\bvol\s+([\d.]+)"}
GCO_PAT = re.compile(r"charm|aeda|\bfd\b|\boav\b|gc-o|olfactometr|\bdf=|\boi\b|\bop\b|sniff", re.I)


def claim_scope(status, notes):
    n = fold(notes) or ""
    if status is None:
        return "not_verified"
    if status == "UNSUPPORTED":
        return "unsupported"
    if "does not say that the note was measured" in n:
        return "compound_odor_note_only"
    if status == "NOT_CONFIRMED" or "gives the compound in the cheese but not this descriptor" in n:
        return "compound_in_cheese_no_descriptor"
    return "descriptor_compound_in_cheese"


ev_rows, b_ev_cheese, b_ev_source, b_ev_proc = [], [], [], []
gen = 0
for idx, r in EV.iterrows():
    eid = clean(r["evidence_id"])
    generated = eid is None
    if generated:
        gen += 1
        eid = f"EVX_{gen:04d}"
    status = STATUS_STD.get(clean(r["verification_status"]))
    if clean(r["verification_status"]) and status is None:
        issue("Evidence", eid, "verification_status", "Estado no reconocido", r["verification_status"])
    scope = claim_scope(status, r["notes"])
    did = descriptor_id(r["descriptor"])
    cid_ = compound_id(r["iupac_compound"], r["cas"])
    rv = clean(r["reported_value"])
    text_all = " ".join(filter(None, [clean(r["evidence (PDF text)"]), rv, clean(r["location"])]))
    pv_raw = clean(r["Process and Volatiles"])
    pv_trunc = bool(pv_raw and pv_raw.endswith("…"))
    pv_ids = re.findall(r"[A-Z]{3}\d{2}-P\d{3}\*?", pv_raw or "")
    cps = cited_short(r["cited_primary_source"])
    split_status = clean(r["split_status"])
    row = OrderedDict(
        evidence_id=eid, evidence_id_generated=generated,
        master_row=to_int(r["source_row"]),
        descriptor_id=did, descriptor_label=clean(r["descriptor"]),
        compound_id=cid_, cas=clean_cas(r["cas"]), iupac_name=clean(r["iupac_compound"]),
        cheese_label_raw=clean(r["cheese_type"]),
        n_cheeses=to_int(r["n_cheeses"]), n_sources=to_int(r["n_sources"]),
        pathway_id=PW_ID.get(fold(r["biochemical pathway"])),
        claim_scope=scope,
        verification_status=status,
        evidence_level_raw=clean(r["evidence_level"]),
        evidence_score=SCORE.get(status),
        use_as_cheese_descriptor_label=(scope == "descriptor_compound_in_cheese"),
        use_as_compound_odor_label=scope in ("descriptor_compound_in_cheese", "compound_odor_note_only"),
        source_type=clean(r["source_type"]),
        location_in_source=clean(r["location"]),
        descriptor_in_source=clean(r["descriptor_in_source"]),
        evidence_text=clean(r["evidence (PDF text)"]),
        reported_value_raw=rv,
    )
    for k, pat in RV_KEYS.items():
        m = re.search(pat, rv or "")
        row[f"rv_{k}"] = float(m.group(1)) if m else None
    row.update(OrderedDict(
        method_hint_gc_olfactometry=bool(GCO_PAT.search(text_all)) if text_all else None,
        cited_primary_source_raw=clean(r["cited_primary_source"]),
        cited_primary_source_id=src_lookup(cps),
        n_cited_primary_sources=len(cited_parts(r["cited_primary_source"])),
        possible_double_count=clean(r["double_counting_alert"]) is not None,
        double_counting_alert_raw=clean(r["double_counting_alert"]),
        unsupporting_sources_raw=clean(r["unsupporting_sources (same master-file row)"]),
        split_status=split_status,
        process_refs_truncated=pv_trunc,
        n_process_refs_visible=len(pv_ids),
        notes=clean(r["notes"]),
    ))
    # contexto de producción asignado a la fila en la fuente
    ctx = parse_context(r["milk (species)"], r["milk treatment"], r["rennet / culture"],
                        r["ripening time"], r["other process factor"])
    for k, v in ctx.items():
        row["ctx_" + k] = v
    ev_rows.append(row)

    # puentes
    cit = HD.CHECK_IN_TABLE.get(eid)
    for t in split_list(r["cheese_type"]):
        if cit and fold(t) == "check in the table" and cit[0]:
            # Fase 1.1: queso identificado en el texto del PDF copiado en la evidencia
            for nm in split_list(cit[0]):
                b_ev_cheese.append(dict(evidence_id=eid, cheese_label_raw=t, cheese_id=CHEESE_ID.get(nm),
                                        cheese_name_std=nm, sample_qualifier=None,
                                        label_type=std_info.get(nm, {}).get("type", S),
                                        resolution_status=cit[1], resolution_criterion=cit[2]))
                if CHEESE_ID.get(nm) is None:
                    raise ValueError(f"Queso de resolución inexistente: {nm}")
            CORR_LOG.append(dict(fase="1.1", tabla="bridge_evidence_cheese", clave=eid, campo="cheese",
                                 valor_anterior=t, valor_nuevo=cit[0], estado=cit[1], referencia="",
                                 criterio=cit[2]))
            continue
        std, q, ty = cheese_std(t)
        b_ev_cheese.append(dict(evidence_id=eid, cheese_label_raw=t, cheese_id=CHEESE_ID.get(std),
                                cheese_name_std=std, sample_qualifier=q, label_type=ty,
                                resolution_status=(cit[1] if cit else None),
                                resolution_criterion=(cit[2] if cit else None)))
    for s_ in source_ids(r["source_raw"]):
        b_ev_source.append(dict(evidence_id=eid, source_id=s_))
    for p in pv_ids:
        b_ev_proc.append(dict(evidence_id=eid, process_effect_id=p.rstrip("*"),
                              marked_with_asterisk=p.endswith("*"), list_truncated_in_source=pv_trunc))

    # incidencias
    if generated:
        issue("Evidence", eid, "evidence_id", "Fila sin evidence_id en la fuente (ID generado EVX_)")
    if split_status and split_status.startswith("pending"):
        issue("Evidence", eid, "split_status", "Pendiente en la fuente", split_status)
    if "check in the table" in (fold(r["cheese_type"]) or ""):
        issue("Evidence", eid, "cheese_type", "Queso sin resolver ('check in the table')")
    if pv_trunc:
        issue("Evidence", eid, "Process and Volatiles", "Lista de referencias truncada con '…' en la fuente")
    if did is None:
        issue("Evidence", eid, "descriptor", "Descriptor sin ID", r["descriptor"])
    if cid_ is None:
        issue("Evidence", eid, "cas", "Compuesto sin ID", r["iupac_compound"])

fact_evidence = pd.DataFrame(ev_rows)
bridge_evidence_cheese = pd.DataFrame(b_ev_cheese)
# Si dos etiquetas originales de la misma evidencia apuntan al mismo queso, se fusionan
# (evita contar dos veces la misma evidencia para un queso).
_bk = bridge_evidence_cheese.assign(_k=bridge_evidence_cheese.cheese_id.fillna("NA:" + bridge_evidence_cheese.cheese_label_raw))


def _join(s):
    v = [x for x in dict.fromkeys(s.dropna().astype(str))]
    return " | ".join(v) if v else None


bridge_evidence_cheese = _bk.groupby(["evidence_id", "_k"], sort=False).agg(
    cheese_label_raw=("cheese_label_raw", _join), cheese_id=("cheese_id", "first"),
    cheese_name_std=("cheese_name_std", "first"), sample_qualifier=("sample_qualifier", _join),
    label_type=("label_type", "first"), resolution_status=("resolution_status", "first"),
    resolution_criterion=("resolution_criterion", "first")).reset_index().drop(columns="_k")
bridge_evidence_source = pd.DataFrame(b_ev_source).drop_duplicates()
bridge_evidence_process = pd.DataFrame(b_ev_proc).drop_duplicates()

# ----------------------------------------------------------------------------
# 8. PROCESO -> VOLÁTILES (fact_process_effect)
# ----------------------------------------------------------------------------
FACTOR_CAT = {
    "ripening time": "ripening_time", "ripening time (fall)": "ripening_time",
    "ripening time (winter)": "ripening_time", "ripening temperature": "ripening_temperature",
    "fat content": "fat_content", "adjunct culture": "adjunct_culture",
    "heat treatment of milk": "milk_heat_treatment", "milk treatment": "milk_heat_treatment",
    "season of the year": "season", "manufacturing season": "season",
    "high hydrostatic pressure (600 mpa)": "high_pressure",
    "culture type": "starter_culture", "starter culture": "starter_culture",
    "starter culture and rennet": "starter_culture_and_coagulant",
    "culture / added enzymes": "starter_culture_and_enzymes", "non-starter flora": "non_starter_flora",
    "packaging method": "packaging", "packaging material": "packaging",
    "storage temperature": "storage_temperature", "milk species": "milk_species",
    "cheese type": "cheese_type", "cheese type (mold)": "cheese_type",
    "rennet type": "coagulant", "rennet retention": "coagulant",
    "mold type": "mold_or_surface_culture", "surface culture": "mold_or_surface_culture",
    "surface culture (molds)": "mold_or_surface_culture",
    "lipase type (enzyme)": "lipase", "lipase origin": "lipase",
    "microbial contamination of the milk": "microbial_contamination",
    "animal feed": "animal_feed", "animal feed (grazing)": "animal_feed",
    "preservative (sorbate)": "preservative", "interaction between compounds": "compound_interaction",
    "excessive lipolysis": "lipolysis_extent", "animal breed": "animal_breed",
    "storage with herbs": "storage_with_herbs", "light exposure": "light_exposure",
    "enzyme-modified cheese (process)": "enzyme_modified_cheese_process",
    "moisture and salt": "moisture_and_salt", "brine": "brine", "ph and salt in brine": "brine",
    "process factors (general)": "general", "smoking": "smoking", "smoking and packaging": "smoking",
    "sal": "salt", "other factor (barrel ripening)": "ripening_container",
    "other factor (wooden utensils)": "wooden_utensils", "cooking temperature": "cooking_temperature",
    "redox potential": "redox_potential",
}
UNIT = {  # unidad cruda -> (unidad estándar, factor, tipo de valor)
    "mg/kg": ("ug/kg", 1000.0, "concentration"), "µg/kg": ("ug/kg", 1.0, "concentration"),
    "µg/100 g": ("ug/kg", 10.0, "concentration"),
    "aru": ("ARU", 1.0, "relative"), "aru × 10³": ("ARU", 1e3, "relative"),
    "aru × 10⁴": ("ARU", 1e4, "relative"), "tic": ("TIC", 1.0, "relative"),
    "tic × 10³": ("TIC", 1e3, "relative"), "au (arbitrary units)": ("AU", 1.0, "relative"),
    "ra (relative abundance)": ("RA", 1.0, "relative"),
}
UNIT = {fold(k): v for k, v in UNIT.items()}


def fat_std(s):
    f = fold(s)
    if unknown(s):
        return "unknown"
    if " vs " in f or "/" in f:
        return "comparison"
    if "full" in f:
        return "full_fat"
    if "50%" in f:
        return "reduced_50pct"
    if "low" in f:
        return "low_fat"
    return "other"


def season(factor, other, cond):
    for s_ in (factor, other, cond):
        f = fold(s_) or ""
        if " vs " in f:
            continue
        for w in ("spring", "summer", "fall", "winter"):
            if re.search(rf"\b{w}\b", f):
                return w
    return None


pv_rows = []
for _, r in PV.iterrows():
    pid = clean(r["id"])
    fac = clean(r["factor studied"])
    cat = FACTOR_CAT.get(fold(fac))
    if cat is None:
        issue("Process and Volatiles", pid, "factor studied", "Factor sin categoría", fac)
    std, q, ty = cheese_std(r["cheese"])
    iup = clean(r["iupac_compound"])
    v, vr = r["value"], r["reference condition value"]
    vn, vrn = to_num(v), to_num(vr)
    nd, ndr = fold(v) == "nd", fold(vr) == "nd"
    unit_raw = clean(r["unit"])
    u = UNIT.get(fold(unit_raw)) if unit_raw else None
    if unit_raw and u is None:
        issue("Process and Volatiles", pid, "unit", "Unidad no reconocida", unit_raw)
    ratio = vn / vrn if (vn is not None and vrn not in (None, 0)) else None
    is_ref = clean(r["condition"]) is not None and fold(r["condition"]) == fold(r["reference condition"])
    if is_ref:
        direction = "reference"
    elif ratio is not None:
        direction = "up" if ratio > 1 else ("down" if ratio < 1 else "equal")
    elif vn is not None and vn > 0 and ndr:
        direction = "appears_vs_ND"
    elif nd and vrn:
        direction = "not_detected_vs_reference"
    else:
        direction = None
    cps = cited_short(r["cited primary source"])
    row = OrderedDict(
        process_effect_id=pid,
        factor_studied_raw=fac, factor_category=cat,
        season=season(fac, r["other factor (season, packaging, storage, pressure)"], r["condition"]),
        cheese_label_raw=clean(r["cheese"]), cheese_id=CHEESE_ID.get(std), cheese_name_std=std,
        cheese_label_type=ty, sample_qualifier=q,
    )
    ctx = parse_context(r["milk (species)"], r["milk treatment"], r["rennet / culture"],
                        r["ripening time"], r["other factor (season, packaging, storage, pressure)"])
    row.update(ctx)
    row.update(OrderedDict(
        fat_content_raw=clean(r["fat content"]), fat_content=fat_std(r["fat content"]),
        condition=clean(r["condition"]), reference_condition=clean(r["reference condition"]),
        is_reference_row=(clean(r["condition"]) is not None and
                          fold(r["condition"]) == fold(r["reference condition"])),
        compound_or_family_raw=clean(r["compound or family"]),
        is_family_level=iup is None,
        compound_id=compound_id(iup, r["cas"]) if iup else None,
        cas=clean_cas(r["cas"]), iupac_name=iup,
        pathway_according_to_source=clean(r["biochemical pathway (according to the source)"]),
        value_raw=clean(v), value=vn, detected=(False if nd else (True if vn is not None else None)),
        reference_value_raw=clean(vr), reference_value=vrn,
        reference_detected=(False if ndr else (True if vrn is not None else None)),
        unit_raw=unit_raw, unit_std=u[0] if u else None, value_type=u[2] if u else None,
        value_std=vn * u[1] if (vn is not None and u) else None,
        reference_value_std=vrn * u[1] if (vrn is not None and u) else None,
        ratio_vs_reference=ratio,
        log2_ratio=float(np.log2(ratio)) if ratio and ratio > 0 else None,
        direction=direction,
        source_id="|".join(source_ids(r["source"])) or None,
        cited_primary_source_raw=clean(r["cited primary source"]),
        cited_primary_source_id=src_lookup(cps),
        location_in_source=clean(r["location"]),
        notes=clean(r["notes"]),
    ))
    if nd or ndr:
        pass
    if vn is None and not nd and clean(v):
        issue("Process and Volatiles", pid, "value", "Valor no numérico", v)
    pv_rows.append(row)
fact_process_effect = pd.DataFrame(pv_rows)

# ----------------------------------------------------------------------------
# 9. TABLAS DERIVADAS (agregadas, solo con lo que dicen las evidencias)
# ----------------------------------------------------------------------------
fe = fact_evidence
bec = bridge_evidence_cheese
rank = {"CONFIRMED_PRIMARY": 5, "CONFIRMED_SECONDARY": 4, "PROBABLE_TEXT_ONLY": 3,
        "PROBABLE_TABLE_ILLEGIBLE": 3, "NOT_CONFIRMED": 2, "UNSUPPORTED": 1}


def best_status(s):
    s = [x for x in s if isinstance(x, str)]
    return max(s, key=lambda x: rank.get(x, 0)) if s else None


# compuesto -> descriptor (propiedad del compuesto)
co = fe[fe.use_as_compound_odor_label & fe.compound_id.notna() & fe.descriptor_id.notna()]
co = co.merge(bridge_evidence_source, on="evidence_id", how="left")
fact_compound_odor = co.groupby(["compound_id", "descriptor_id"]).agg(
    n_evidence=("evidence_id", "nunique"),
    n_sources=("source_id", "nunique"),
    best_verification_status=("verification_status", best_status),
    max_evidence_score=("evidence_score", "max"),
    any_primary_confirmation=("verification_status", lambda s: (s == "CONFIRMED_PRIMARY").any()),
    all_possible_double_count=("possible_double_count", "all"),
    evidence_ids=("evidence_id", lambda s: "|".join(sorted(set(s)))),
).reset_index()
fact_compound_odor = fact_compound_odor.merge(
    dim_descriptor[["descriptor_id", "is_aroma_target", "aroma_family", "berodier_subfamily"]],
    on="descriptor_id", how="left")
# --- Fase 4: contraste independiente de cada par compuesto-descriptor con Flavornet ---
_cas = dim_compound.set_index("compound_id").cas_final
_terms = dim_descriptor.set_index("descriptor_id").aroma_terms


def _fn_cols(df):
    res = [P4.flavornet_check(_cas.get(c), _terms.get(d), f, FLAVORNET)
           for c, d, f in zip(df.compound_id, df.descriptor_id, df.aroma_family)]
    df["flavornet_support"] = [r[0] for r in res]
    df["flavornet_status"] = [r[1] for r in res]
    df["flavornet_odors"] = [r[2] for r in res]
    df["flavornet_matched_term"] = [r[3] for r in res]
    return df


fact_compound_odor = _fn_cols(fact_compound_odor)

# queso -> compuesto (presencia), desde evidencias + proceso
cc = fe[fe.claim_scope.isin(["descriptor_compound_in_cheese", "compound_odor_note_only",
                             "compound_in_cheese_no_descriptor"]) & fe.compound_id.notna()]
cc = cc.merge(bec[["evidence_id", "cheese_id"]], on="evidence_id").dropna(subset=["cheese_id"])
a = cc.groupby(["cheese_id", "compound_id"]).agg(
    n_evidence=("evidence_id", "nunique"),
    best_verification_status=("verification_status", best_status)).reset_index()
pvc = fact_process_effect.dropna(subset=["compound_id", "cheese_id"])
b = pvc.groupby(["cheese_id", "compound_id"]).agg(
    n_process_measurements=("process_effect_id", "nunique"),
    n_detected=("detected", lambda s: int((s == True).sum())),
    n_not_detected=("detected", lambda s: int((s == False).sum())),
).reset_index()
fact_cheese_compound = a.merge(b, on=["cheese_id", "compound_id"], how="outer")
fact_cheese_compound["reported_present"] = (fact_cheese_compound["n_evidence"].fillna(0) > 0) | \
                                           (fact_cheese_compound["n_detected"].fillna(0) > 0)

# queso -> descriptor
cd = fe[fe.use_as_cheese_descriptor_label & fe.descriptor_id.notna()]
cd = cd.merge(bec[["evidence_id", "cheese_id"]], on="evidence_id").dropna(subset=["cheese_id"])
fact_cheese_descriptor = cd.groupby(["cheese_id", "descriptor_id"]).agg(
    n_evidence=("evidence_id", "nunique"),
    n_linked_compounds=("compound_id", "nunique"),
    best_verification_status=("verification_status", best_status),
    max_evidence_score=("evidence_score", "max"),
    linked_compound_ids=("compound_id", lambda s: "|".join(sorted(set(s.dropna())))),
).reset_index()

# compuesto -> ruta
bridge_compound_pathway = fe.dropna(subset=["compound_id", "pathway_id"]).groupby(
    ["compound_id", "pathway_id"]).agg(n_evidence=("evidence_id", "nunique")).reset_index()

# ----------------------------------------------------------------------------
# 9b. FASE 4 — independencia de estudios, duplicados y pendientes
# ----------------------------------------------------------------------------
REVIEW_KEYS = {"curioni 2002"}  # Curioni & Bosset (2002), Int. Dairy J. 12:959-984: revisión (no estudio primario)
_PRIMARY_SRC = {r.source_id: f"{fold(r.first_author)} {int(r.year)}" for r in dim_source.itertuples()
                if r.source_type == "primary" and pd.notna(r.year)}


def _cited_keys(s_):
    keys = []
    for part in re.split(r"[;|]", s_ or ""):
        p_ = fold(part).strip() if part else ""
        p_ = re.sub(r"^(odor notes|notes)\s*:\s*", "", p_)
        if not p_ or p_.startswith("ch."):
            continue
        m = re.match(r"^([a-z][a-z\-' ]*?)(?:,|\s+and\s|\s*&|\s+et al|\s*\()[^0-9]*?(\d{4})", p_)
        if m:
            keys.append(f"{m.group(1).strip()} {m.group(2)}")
    return keys


_sid_by_ev = bridge_evidence_source.groupby("evidence_id").source_id.agg(list)
study_rows = []
for r in fact_evidence.itertuples():
    keys = _cited_keys(r.cited_primary_source_raw if isinstance(r.cited_primary_source_raw, str) else "")
    keys += [_PRIMARY_SRC[x] for x in _sid_by_ev.get(r.evidence_id, []) if x in _PRIMARY_SRC]
    keys = list(dict.fromkeys(keys))
    prim = [k for k in keys if k not in REVIEW_KEYS]
    study_rows.append(dict(
        evidence_id=r.evidence_id,
        independent_study_keys="|".join(prim) or None,
        n_independent_studies=len(prim),
        cites_curioni_review=any(k in REVIEW_KEYS for k in keys),
        only_via_review=(not prim) and any(k in REVIEW_KEYS for k in keys),
        study_group_key=prim[0] if prim else ("curioni 2002 [revisión]" if keys else "sin_estudio_primario")))
_study = pd.DataFrame(study_rows)
fact_evidence = fact_evidence.merge(_study, on="evidence_id", how="left")
fe = fact_evidence

# Fase 4 — pares por confirmar (Articles to Confirm): evidencia interna + Flavornet
_conf = fe[fe.verification_status.isin(["CONFIRMED_PRIMARY", "CONFIRMED_SECONDARY"])
           & fe.claim_scope.isin(["descriptor_compound_in_cheese", "compound_odor_note_only"])]
_conf_pairs = _conf.groupby(["descriptor_id", "compound_id"]).evidence_id.agg(lambda x: "|".join(sorted(x)))
_fam = dim_descriptor.set_index("descriptor_id").aroma_family


def _pair_resolution(did, cid_):
    ev_ids = _conf_pairs.get((did, cid_))
    fn = P4.flavornet_check(_cas.get(cid_), _terms.get(did), _fam.get(did), FLAVORNET)
    if ev_ids:
        return ("confirmado_por_otra_evidencia", P4.V, ev_ids, fn,
                "El mismo par descriptor–compuesto está confirmado en otra evidencia del Excel.")
    if fn[0] == "termino":
        return ("confirmado_externamente", P4.V, None, fn,
                f"Flavornet registra para el compuesto el olor '{fn[3]}', coincidente con el descriptor.")
    if fn[0] == "familia":
        return ("compatible_a_nivel_familia", P4.I, None, fn,
                "Flavornet registra para el compuesto olores de la misma familia de Bérodier, no el término exacto.")
    if fn[0] == "sin_coincidencia":
        return ("no_confirmado", P4.N, None, fn, f"Flavornet registra otros olores ({fn[2]}); ninguno de la familia.")
    return ("no_confirmado", P4.N, None, fn, "El compuesto no está en Flavornet y ninguna otra evidencia del Excel confirma el par.")


# Fase 4 — evidencias pendientes en la fuente (split_status 'pending')
pend_rows = []
for r in fe[fe.split_status.astype(str).str.startswith("pending")].itertuples():
    if r.evidence_id in HD.CHECK_IN_TABLE:
        d = HD.CHECK_IN_TABLE[r.evidence_id]
        pend_rows.append(dict(evidence_id=r.evidence_id, descriptor_label=r.descriptor_label, iupac_name=r.iupac_name,
                              cheese_label_raw=r.cheese_label_raw, pendiente=r.split_status,
                              resolucion="queso identificado en el texto del PDF (Fase 1)" if d[0] else "queso no identificable",
                              estado=d[1], evidencias_confirmatorias=None, flavornet_soporte=None, criterio=d[2]))
        continue
    res = _pair_resolution(r.descriptor_id, r.compound_id)
    pend_rows.append(dict(evidence_id=r.evidence_id, descriptor_label=r.descriptor_label, iupac_name=r.iupac_name,
                          cheese_label_raw=r.cheese_label_raw, pendiente=r.split_status,
                          resolucion=res[0] + "; asignación queso/fuente: no recuperable sin el documento original",
                          estado=res[1], evidencias_confirmatorias=res[2], flavornet_soporte=res[3][0],
                          criterio=res[4] + " El queso y la fuente concretos de esta fila no se pueden asignar: "
                          "la fila maestra lista varios quesos y fuentes sin indicar cuál corresponde."))
qa_pending_evidence = pd.DataFrame(pend_rows)

# Fase 4 — enlaces evidencia -> proceso recalculados de forma exacta (mismo compuesto)
_pvc = fact_process_effect.dropna(subset=["compound_id"])[["process_effect_id", "compound_id"]]
_rec = fe[["evidence_id", "compound_id"]].dropna().merge(_pvc, on="compound_id")[["evidence_id", "process_effect_id"]]
_rec["link_method"] = "mismo_compuesto (recalculado)"
bridge_evidence_process = bridge_evidence_process.assign(link_method="lista_original_visible")
bridge_evidence_process = pd.concat([bridge_evidence_process, _rec], ignore_index=True)
_trunc_ev = set(fe.loc[fe.process_refs_truncated == True, "evidence_id"])
bridge_evidence_process["evidence_list_truncated"] = bridge_evidence_process.evidence_id.isin(_trunc_ev)

# dim_source: estado bibliográfico verificado
dim_source["bibliographic_note"] = None
dim_source.loc[dim_source.short_citation == "Curioni 2002", ["source_type", "bibliographic_note"]] = [
    "review", "Revisión: Curioni & Bosset (2002), Int. Dairy J. 12(12):959–984, DOI 10.1016/S0958-6946(02)00124-3. "
              "No es un estudio primario: sus tablas compilan estudios de GC-O."]

# ----------------------------------------------------------------------------
# 10. TABLA PLANA PARA ML (una fila = evidencia x queso)
# ----------------------------------------------------------------------------
desc_info = dim_descriptor.set_index("descriptor_id")[
    ["family_l1_as_in_source", "is_off_flavor", "family_is_general_or_character",
     "is_aroma_target", "aroma_family", "berodier_subfamily", "aroma_terms", "harmonization_status"]]
CHEESE_SPEC_COLS = ["cheese_family", "secondary_technology", "country_iso", "pdo_pgi",
                    "spec_milk_cow", "spec_milk_sheep", "spec_milk_goat", "spec_milk_buffalo",
                    "spec_heat_treatment", "spec_coagulant_culture", "spec_ripening_days_min",
                    "spec_ripening_days_max", "spec_ripening_class", "spec_completeness"]
cheese_info = dim_cheese.set_index("cheese_id")[CHEESE_SPEC_COLS].add_prefix("cheese_")
cmp_info = dim_compound.set_index("compound_id")[["pubchem_cid", "chemical_class"]]
pw_info = dim_pathway.set_index("pathway_id")["pathway_label"]
src_one = bridge_evidence_source.groupby("evidence_id")["source_id"].agg(lambda s: "|".join(sorted(s)))

ml = fe.merge(bec[["evidence_id", "cheese_id", "cheese_name_std", "sample_qualifier", "label_type"]]
              .rename(columns={"label_type": "cheese_label_type"}), on="evidence_id", how="left")
ml = ml.join(desc_info, on="descriptor_id").join(cmp_info, on="compound_id").join(cheese_info, on="cheese_id")
ml["use_as_cheese_aroma_label"] = ml.use_as_cheese_descriptor_label & (ml.is_aroma_target == True)
ml["use_as_compound_aroma_label"] = ml.use_as_compound_odor_label & (ml.is_aroma_target == True)
# Fase 4: contraste con Flavornet y duplicados por estudio independiente
_fnr = [P4.flavornet_check(_cas.get(c), _terms.get(d), f, FLAVORNET) if isinstance(c, str) else ("no_en_flavornet", P4.N, None, None)
        for c, d, f in zip(ml.compound_id, ml.descriptor_id, ml.aroma_family)]
ml["flavornet_support"] = [x[0] for x in _fnr]
ml["_ord"] = -ml.evidence_score.fillna(0)
ml = ml.sort_values(["_ord", "evidence_id"])
_lab = ml.use_as_cheese_aroma_label & ml.cheese_id.notna()
_key = ml.cheese_id.astype(str) + "|" + ml.descriptor_id.astype(str) + "|" + ml.compound_id.astype(str) + "|" + ml.study_group_key.astype(str)
_first = ml[_lab].assign(_k=_key[_lab]).groupby("_k").evidence_id.first()
ml["duplicate_of_evidence"] = [(_first.get(k) if (l and _first.get(k) != e) else None) for k, l, e in zip(_key, _lab, ml.evidence_id)]
ml["use_as_cheese_aroma_label_dedup"] = _lab & ml.duplicate_of_evidence.isna()
ml = ml.sort_index().drop(columns="_ord")
ml["pathway_label"] = ml["pathway_id"].map(pw_info)
ml["source_ids"] = ml["evidence_id"].map(src_one)
ml.insert(0, "row_id", [f"ML_{i:05d}" for i in range(1, len(ml) + 1)])

ctx_ev = [c for c in fe.columns if c.startswith("ctx_")]
ML_ORDER = (
    ["row_id", "evidence_id", "evidence_id_generated",
     # objetivo (descriptor)
     "descriptor_id", "descriptor_label", "is_aroma_target", "aroma_family", "berodier_subfamily",
     "aroma_terms", "harmonization_status", "family_l1_as_in_source", "is_off_flavor",
     "family_is_general_or_character",
     # compuesto
     "compound_id", "cas", "pubchem_cid", "iupac_name", "chemical_class", "pathway_id", "pathway_label",
     # queso
     "cheese_id", "cheese_name_std", "cheese_label_type", "sample_qualifier", "cheese_label_raw",
     "n_cheeses"]
    + ["cheese_" + c for c in CHEESE_SPEC_COLS]
    + ctx_ev
    + ["claim_scope", "verification_status", "evidence_level_raw", "evidence_score",
       "use_as_cheese_descriptor_label", "use_as_compound_odor_label",
       "use_as_cheese_aroma_label", "use_as_compound_aroma_label", "use_as_cheese_aroma_label_dedup",
       "duplicate_of_evidence", "flavornet_support", "independent_study_keys", "n_independent_studies",
       "only_via_review", "study_group_key",
       "reported_value_raw", "rv_FD", "rv_DF", "rv_OI", "rv_OP", "rv_c", "rv_pct", "rv_vol",
       "method_hint_gc_olfactometry", "descriptor_in_source", "evidence_text", "location_in_source",
       "source_ids", "n_sources", "source_type", "cited_primary_source_id", "cited_primary_source_raw",
       "possible_double_count", "double_counting_alert_raw", "unsupporting_sources_raw",
       "split_status", "process_refs_truncated", "n_process_refs_visible", "master_row", "notes"]
)
ml = ml[ML_ORDER]

# ----------------------------------------------------------------------------
# 11. OTRAS MODALIDADES (sabor, trigeminal, textura) y QA
# ----------------------------------------------------------------------------
def dedupe_locations(s):
    return "; ".join(dedupe(split_list(s))) or None


na_rows, na_cheese, na_src, taste_cmp = [], [], [], []
for mod, df, fam_col, ctx_col, cmp_col, loc_col in [
        ("taste", TA, "Descriptor Family / Category", "Cheese Type / Context", "IUPAC- Chemical Compound(s)", "Exact Location"),
        ("trigeminal", TR, "Descriptor Family / Category", "Cheese Type / Context", "Chemical Compound(s)", "Exact Location"),
        ("texture", TX, "Descriptor Family / Category", "Cheese Type / Context", "Chemical Compound(s)", "Exact Location")]:
    for i, r in df.iterrows():
        rid = f"{mod[:2].upper()}_{i + 1:03d}"
        did = descriptor_id(r["Descriptor"])
        na_rows.append(dict(
            record_id=rid, sensory_modality=mod, descriptor_id=did, descriptor_label=clean(r["Descriptor"]),
            family_raw=clean(r[fam_col]), family_l1_as_in_source=(family_tokens(r[fam_col]) or [None])[0],
            cheese_context_raw=clean(r[ctx_col]), compounds_raw=clean(r[cmp_col]),
            chemical_family_raw=clean(r["Chemical Family"]) if "Chemical Family" in df.columns else None,
            source_raw=clean(r["Source"]), location_deduplicated=dedupe_locations(r[loc_col]),
            notes=clean(r["Notes"]) if "Notes" in df.columns else None))
        for t in split_list(r[ctx_col]):
            na_cheese.append(dict(record_id=rid, cheese_context=t))
        for s_ in source_ids(r["Source"]):
            na_src.append(dict(record_id=rid, source_id=s_))
        if mod == "taste":
            n = split_list(r[cmp_col])
            for name in n:
                taste_cmp.append(dict(record_id=rid, descriptor_id=did, compound_name_raw=name,
                                      compound_id=compound_id(name),
                                      is_reference_standard_only=bool(REF_STANDARD_PAT.search(name))))
nonaroma_descriptor = pd.DataFrame(na_rows)
nonaroma_context = pd.DataFrame(na_cheese)
nonaroma_source = pd.DataFrame(na_src).drop_duplicates()
taste_compound = pd.DataFrame(taste_cmp)

qa_pending = AC.rename(columns={
    "Descriptor": "descriptor_label", "Descriptor family": "descriptor_family_raw",
    "Compound (IUPAC)": "compound_name", "CAS": "cas_raw",
    "Cheeses of the master-file row": "cheeses_raw", "Sources of the master-file row": "sources_raw",
    "Reason": "reason", "Original row in sheet 1": "master_row"}).copy()
for c in qa_pending.columns:
    qa_pending[c] = qa_pending[c].map(clean)
qa_pending.insert(0, "descriptor_id", qa_pending["descriptor_label"].map(descriptor_id))
qa_pending.insert(1, "compound_id", [compound_id(n, c) for n, c in zip(qa_pending.compound_name, qa_pending.cas_raw)])

for _, r in dim_compound[dim_compound.pubchem_cid.isna()].iterrows():
    issue("dim_compound", r["compound_id"], "pubchem_cid", "Sin CID en la fuente", r["iupac_name"])
# Fase 4: resolución de los 138 pares por confirmar
_res = [_pair_resolution(d, c) if (isinstance(d, str) and isinstance(c, str)) else
        ("no_confirmado", P4.N, None, ("sin_id", None, None, None), "Descriptor o compuesto sin identificador.")
        for d, c in zip(qa_pending.descriptor_id, qa_pending.compound_id)]
qa_pending["resolucion"] = [x[0] for x in _res]
qa_pending["estado"] = [x[1] for x in _res]
qa_pending["evidencias_confirmatorias"] = [x[2] for x in _res]
qa_pending["flavornet_soporte"] = [x[3][0] for x in _res]
qa_pending["flavornet_olores"] = [x[3][2] for x in _res]
qa_pending["criterio"] = [x[4] for x in _res]
qa_pending["aroma_family"] = qa_pending.descriptor_id.map(_fam)

qa_issues = pd.DataFrame(ISSUES).drop_duplicates().sort_values(["table", "problem", "record_key"])

# ----------------------------------------------------------------------------
# 12. ESCRITURA
# ----------------------------------------------------------------------------
print("Escribiendo en", OUT)
write(ml, "ml_evidence_flat.csv")
write(fact_evidence, "fact_evidence.csv")
write(fact_process_effect, "fact_process_effect.csv")
write(fact_compound_odor, "fact_compound_odor.csv")
write(fact_cheese_compound, "fact_cheese_compound.csv")
write(fact_cheese_descriptor, "fact_cheese_descriptor.csv")
write(dim_cheese, "dim_cheese.csv")
write(cheese_alias, "cheese_alias.csv")
write(dim_compound, "dim_compound.csv")
write(compound_alias, "compound_alias.csv")
write(dim_descriptor, "dim_descriptor.csv")
write(descriptor_term, "descriptor_term.csv")
write(descriptor_family, "descriptor_family.csv")
write(dim_source, "dim_source.csv")
write(dim_pathway, "dim_pathway.csv")
write(pathway_steps, "pathway_steps.csv")
write(bridge_evidence_cheese, "bridge_evidence_cheese.csv")
write(bridge_evidence_source, "bridge_evidence_source.csv")
write(bridge_evidence_process, "bridge_evidence_process.csv")
write(bridge_compound_pathway, "bridge_compound_pathway.csv")
write(nonaroma_descriptor, "nonaroma_descriptor.csv")
write(nonaroma_context, "nonaroma_context.csv")
write(nonaroma_source, "nonaroma_source.csv")
write(taste_compound, "taste_compound.csv")
write(qa_pending, "qa_pending_confirmation.csv")
write(qa_issues, "qa_issues.csv")
write(compound_properties, "compound_properties.csv")
write(qa_pending_evidence, "qa_pending_evidence_resolution.csv")

# ----------------------------------------------------------------------------
# 12b. REGISTROS DE ARMONIZACIÓN (corrections/*.xlsx) — una fila por registro evaluado
# ----------------------------------------------------------------------------
CORR = os.path.join(ROOT, "corrections")
os.makedirs(CORR, exist_ok=True)


def save_xlsx(sheets, name):
    path = os.path.join(CORR, name)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        for sheet, df in sheets.items():
            df.to_excel(xw, sheet_name=sheet, index=False)
            ws = xw.sheets[sheet]
            ws.freeze_panes = "B2"
            ws.auto_filter.ref = ws.dimensions
            for j, col in enumerate(df.columns, start=1):
                ws.cell(row=1, column=j).font = ws.cell(row=1, column=j).font.copy(bold=True)
                width = max([len(str(col))] + [len(str(v)) for v in df[col].head(200).tolist()])
                ws.column_dimensions[ws.cell(row=1, column=j).column_letter].width = min(max(width + 2, 10), 60)
    print(f"  corrections/{name:43s} " + ", ".join(f"{k}: {len(v)} filas" for k, v in sheets.items()))


REC = {}
# --- Fase 1.1: 282 equivalencias ---
uses = bridge_evidence_cheese.cheese_label_raw.value_counts().add(PV["cheese"].map(clean).value_counts(), fill_value=0)
rows = []
for a in alias_rows:
    raw = a["cheese_label_raw"]
    v1n, v1q, v1t = _cheese_std_v1(raw)
    d = HD.ALIAS_DECISIONS.get(raw)
    if d:
        est, orig, ref, why = d[2], d[3], HD.REF.get(d[4], "") if d[4] else "", d[5]
    elif v1t == "not_cheese":
        est, orig, ref, why = HD.V, HD.TXT, "", "No es un queso (té, cacao o leche): se conserva como 'not_cheese'."
    elif v1t == "multi_cheese":
        est, orig, ref, why = HD.I, HD.TXT, "", "Etiqueta con varios quesos: la fuente da el dato para el grupo; separarla atribuiría datos a quesos concretos sin evidencia."
    elif v1t == "generic_category":
        est, orig, ref, why = HD.I, HD.TXT, "", "Etiqueta que designa un grupo de quesos, no un queso concreto: se agrupa en la categoría genérica correspondiente."
    elif fold(raw) == fold(v1n):
        est, orig, ref, why = HD.V, HD.TXT, "", "Mismo nombre (solo cambian mayúsculas, acentos o espacios)."
    elif v1q:
        est, orig, ref, why = HD.I, HD.TXT, "", "Variante del mismo queso: la información entre paréntesis o el adjetivo pasa a 'sample_qualifier' (condición de la muestra)."
    else:
        est, orig, ref, why = HD.I, HD.TXT, "", "Corrección de errata o variante ortográfica (p. ej. Mozzarrella, Grana Tretino, Emmentaler, Parmigiano-Reggiano)."
    rows.append(dict(cheese_label_raw=raw, n_filas_en_datos=int(uses.get(raw, 0)),
                     nombre_v1=v1n, tipo_v1=v1t, nombre_final=a["cheese_name_std"],
                     calificador_muestra=a["sample_qualifier"], tipo_final=a["label_type"],
                     cheese_id=CHEESE_ID.get(a["cheese_name_std"]),
                     cambio_respecto_v1="sí" if (v1n, v1t) != (a["cheese_name_std"], a["label_type"]) else "no",
                     estado=est, origen_evidencia=orig, referencia=ref, criterio=why))
REC["eq"] = pd.DataFrame(rows).sort_values(["cambio_respecto_v1", "n_filas_en_datos"], ascending=[False, False])
cit_rows = [dict(evidence_id=k, queso_resuelto=v[0], estado=v[1], criterio=v[2]) for k, v in HD.CHECK_IN_TABLE.items()]
cit_df = pd.DataFrame(cit_rows).merge(
    fact_evidence[["evidence_id", "descriptor_label", "iupac_name", "location_in_source", "evidence_text"]],
    on="evidence_id", how="left")
parent_df = pd.DataFrame([dict(variante=k, queso_padre=v[0], estado=v[1], referencia=HD.REF.get(v[2], "") if v[2] else "",
                               criterio=v[3]) for k, v in HD.PARENTS.items()])
save_xlsx({"equivalencias": REC["eq"], "check_in_the_table": cit_df, "padres_variantes": parent_df},
          "fase1_quesos_equivalencias.xlsx")

# --- Fase 1.4: 72 familias tecnológicas ---
n_lab_v1 = ml[ml.use_as_cheese_aroma_label].groupby("cheese_name_std").descriptor_id.nunique()
rows = []
for name in sorted(HD.CHEESE_FAMILY, key=fold):
    d = HD.CHEESE_FAMILY[name]
    v2 = RENAMED.get(name, name)
    rows.append(dict(cheese_name_v1=name, cheese_name_v2=v2, cheese_id=CHEESE_ID.get(v2),
                     n_descriptores_aroma=int(n_lab_v1.get(v2, 0)),
                     cheese_family=d[0], secondary_technology=d[1] or None, estado_familia=d[2],
                     referencia_familia=HD.REF.get(d[3], "") if d[3] else "", criterio_familia=d[4],
                     pais_iso=d[5], dop_igp=d[6], estado_dop_igp=d[7],
                     referencia_dop_igp=HD.REF.get(d[8], "") if d[8] else ""))
REC["fam"] = pd.DataFrame(rows)
fam_def = pd.DataFrame({"cheese_family": HD.FAMILIES, "nota": [
    "Fresco de coagulación ácida/láctica", "Fresco de cuajo", "Pasta hilada", "Madurado en salmuera",
    "Pasta blanda con corteza enmohecida", "Corteza lavada / flora de frotado", "Pasta azul",
    "Pasta semidura", "Pasta prensada dura no cocida (categoría añadida en la armonización)",
    "Pasta dura cocida", "Grana (extra duro, cocido, larga maduración)", "Tipo suizo con ojos (propiónica)",
    "Láctico de cabra", "Otra / no encaja"]})
save_xlsx({"familias": REC["fam"], "definicion_familias": fam_def}, "fase1_quesos_familia_tecnologica.xlsx")

# --- Fase 2: 160 registros (40 quesos x 4 bloques) ---
PROFILE_V1 = {}
for _, r in CP.iterrows():
    PROFILE_V1.setdefault(_cheese_std_v1(r["cheese (cheese_type_clean)"])[0], r)
COL_EXCEL = {"leche": "milk (species)", "tratamiento_termico": "milk treatment",
             "cuajo_cultivo": "rennet / culture", "maduracion": "ripening time"}
UNITS = {"leche": "especie(s)", "tratamiento_termico": "raw / thermized / pasteurized / alternativas",
         "cuajo_cultivo": "coagulante; cultivos", "maduracion": "días 'mín–máx' (vacío = abierto)"}
rows = []
for prio, name in enumerate(HD.PRODUCTION_TARGETS, start=1):
    prof = PROFILE_V1.get(name)
    for block in HD.BLOCKS:
        excel_val = clean(prof[COL_EXCEL[block]]) if prof is not None else None
        excel_src = clean(prof["source"]) if prof is not None else None
        excel_known = excel_val is not None and not unknown(excel_val)
        d = HD.PRODUCTION.get((name, block))
        if d:
            val, est, orig, ref, why = d[0], d[1], d[2], HD.REF.get(d[3], "") if d[3] else "", d[4]
        elif excel_known:
            val, est, orig, ref = excel_val, HD.V, HD.EXC, excel_src
            why = "Se conserva el valor del Excel con su fuente citada; no se encontró información que lo contradiga."
        else:
            val, est, orig, ref = None, HD.N, HD.NONE, ""
            why = ("El Excel no lo especifica" if not excel_known else "") + \
                  "; no se encontró un pliego ni una fuente verificable para este tipo de queso."
        rows.append(dict(prioridad=prio, cheese_name_v1=name, cheese_name_v2=RENAMED.get(name, name),
                         bloque=block, valor_excel=excel_val, fuente_excel=excel_src, valor_final=val,
                         unidad=UNITS[block],
                         value_scope="type_specification" if val else None,
                         estado=est, origen_evidencia=orig, referencia=ref, criterio=why))
REC["prod"] = pd.DataFrame(rows)
save_xlsx({"produccion": REC["prod"]}, "fase2_produccion_valores.xlsx")

# --- Fase 3: 169 descriptores de aroma ---
nfil = ml[ml.use_as_compound_odor_label | ml.use_as_cheese_descriptor_label].groupby("descriptor_id").row_id.count()
REC["desc"] = dim_descriptor[dim_descriptor.in_odor_aroma][
    ["descriptor_id", "descriptor_label", "family_l1_as_in_source", "is_aroma_target", "aroma_family",
     "berodier_family_fr", "berodier_subfamily", "aroma_terms", "split_terms", "berodier_term", "drake_term",
     "harmonization_status", "harmonization_criterion"]].copy()
REC["desc"].insert(2, "n_filas_etiqueta", REC["desc"].descriptor_id.map(nfil).fillna(0).astype(int))
REC["desc"] = REC["desc"].sort_values(["aroma_family", "berodier_subfamily", "descriptor_label"], na_position="last")
lex = pd.DataFrame([
    dict(nivel="1 (familia)", fuente="Bérodier et al. 1997, reproducido en ITA St-Hyacinthe, pp. 2–3",
         contenido="lactique, végétal, floral, fruité, torréfié, animal, épicé, autres"),
    dict(nivel="2 (subfamilia)", fuente="Bérodier et al. 1997 (misma fuente); '[proyecto] …' = subfamilia añadida",
         contenido="ver columna berodier_subfamily"),
    dict(nivel="3 (descriptor)", fuente="Términos de la fuente (inglés), separados por ';'", contenido="aroma_terms"),
    dict(nivel="equivalencia", fuente="Drake et al. 2001 (cheesescience.org)", contenido="drake_term"),
])
save_xlsx({"descriptores": REC["desc"], "lexico": lex}, "fase3_descriptores_mapeo.xlsx")

harmonization_log = pd.DataFrame(CORR_LOG)
write(harmonization_log, "harmonization_log.csv")

# ----------------------------------------------------------------------------
# 12c. CONTROL DE CALIDAD (falla si algo no cuadra)
# ----------------------------------------------------------------------------
QC = []


def check(name, ok, detail=""):
    QC.append(dict(comprobacion=name, resultado="OK" if ok else "FALLO", detalle=str(detail)))


check("Filas de Evidence conservadas", len(fact_evidence) == len(EV), f"{len(fact_evidence)} / {len(EV)}")
check("Filas de Process and Volatiles conservadas", len(fact_process_effect) == len(PV),
      f"{len(fact_process_effect)} / {len(PV)}")
for nm, df, key in [("dim_cheese", dim_cheese, "cheese_id"), ("dim_compound", dim_compound, "compound_id"),
                    ("dim_descriptor", dim_descriptor, "descriptor_id"), ("dim_source", dim_source, "source_id"),
                    ("fact_evidence", fact_evidence, "evidence_id"), ("ml_evidence_flat", ml, "row_id"),
                    ("fact_process_effect", fact_process_effect, "process_effect_id")]:
    check(f"Clave única {nm}.{key}", df[key].is_unique, f"{df[key].duplicated().sum()} duplicados")
check("Nombres de queso únicos", dim_cheese.cheese_name_std.is_unique)
for nm, df, col, dim, key in [
        ("ml", ml, "cheese_id", dim_cheese, "cheese_id"), ("ml", ml, "descriptor_id", dim_descriptor, "descriptor_id"),
        ("ml", ml, "compound_id", dim_compound, "compound_id"),
        ("bridge_evidence_cheese", bridge_evidence_cheese, "cheese_id", dim_cheese, "cheese_id"),
        ("bridge_evidence_source", bridge_evidence_source, "source_id", dim_source, "source_id"),
        ("fact_compound_odor", fact_compound_odor, "descriptor_id", dim_descriptor, "descriptor_id"),
        ("fact_cheese_descriptor", fact_cheese_descriptor, "cheese_id", dim_cheese, "cheese_id"),
        ("fact_process_effect", fact_process_effect, "cheese_id", dim_cheese, "cheese_id"),
        ("dim_cheese.parent", dim_cheese, "parent_cheese_id", dim_cheese, "cheese_id")]:
    miss = (~df[col].dropna().isin(dim[key])).sum()
    check(f"Integridad {nm}.{col} -> {key}", miss == 0, f"{miss} referencias rotas")
check("Todas las evidencias están en la tabla plana", set(fact_evidence.evidence_id) <= set(ml.evidence_id))
_dups = ml.dropna(subset=["cheese_id"]).duplicated(["evidence_id", "cheese_id"]).sum()
check("Sin duplicados evidencia x queso en la tabla plana", _dups == 0, f"{_dups} duplicados")
check("Fase 1.1: 282 equivalencias evaluadas", len(REC["eq"]) == 282 and REC["eq"].estado.notna().all(), len(REC["eq"]))
check("Fase 1.1: 11 'check in the table' evaluados", len(cit_df) == 11 and cit_df.estado.notna().all())
check("Fase 1.4: 72 quesos clasificados/evaluados", len(REC["fam"]) == 72 and REC["fam"].estado_familia.notna().all())
check("Fase 2: 160 registros evaluados", len(REC["prod"]) == 160 and REC["prod"].estado.notna().all())
check("Fase 2: todo valor final tiene estado verificado o inferido",
      REC["prod"][REC["prod"].valor_final.notna()].estado.isin([HD.V, HD.I]).all())
check("Fase 3: 169 descriptores evaluados", len(REC["desc"]) == 169 and REC["desc"].harmonization_status.notna().all())
check("Fase 3: términos de Drake dentro del léxico verificado",
      REC["desc"].drake_term.dropna().isin(HD.DRAKE_TERMS).all())
check("Fase 3: familias de nivel 1 dentro de Bérodier",
      REC["desc"][REC["desc"].is_aroma_target == True].berodier_family_fr.isin(HD.L1).all())
check("Valores de producción del tipo separados de los de muestra (ctx_ sin cambios)",
      all(c in fact_evidence.columns for c in ["ctx_ripening_days_min", "ctx_milk_heat_treatment"]))
# --- Fase 4 ---
check("Fase 4: 138 pares por confirmar evaluados", len(qa_pending) == 138 and qa_pending.estado.notna().all())
check("Fase 4: 53 evidencias pendientes evaluadas", len(qa_pending_evidence) == 53 and qa_pending_evidence.estado.notna().all(),
      len(qa_pending_evidence))
check("Fase 4: todos los compuestos con estado de CID", dim_compound.cid_status.notna().all())
check("Fase 4: propiedades PubChem sin compuestos duplicados", compound_properties.compound_id.is_unique)
check("Fase 4: todo CAS completado tiene dígito de control válido",
      dim_compound.cas_final.dropna().map(cas_checksum_ok).all())
check("Fase 4: etiquetas sin duplicar <= etiquetas totales",
      ml.use_as_cheese_aroma_label_dedup.sum() <= ml.use_as_cheese_aroma_label.sum())
check("Fase 4: enlaces evidencia-proceso apuntan a mediciones existentes",
      bridge_evidence_process.loc[bridge_evidence_process.link_method.str.startswith("mismo"), "process_effect_id"]
      .isin(fact_process_effect.process_effect_id).all())
qc = pd.DataFrame(QC)
write(qc, "qa_checks.csv")
if (qc.resultado == "FALLO").any():
    print(qc[qc.resultado == "FALLO"].to_string())
    raise SystemExit("Control de calidad NO superado")
print("  Control de calidad: todas las comprobaciones OK")

# ----------------------------------------------------------------------------
# 13. DICCIONARIO DE DATOS (se genera a partir de las tablas escritas)
# ----------------------------------------------------------------------------
DESC = {
    "row_id": "ID de fila de la tabla plana (una fila = evidencia x queso)",
    "evidence_id": "ID de la evidencia (original del Excel; EVX_ = generado porque faltaba)",
    "evidence_id_generated": "True si el ID no existía en el Excel y se generó",
    "master_row": "Fila de la hoja '1. Odor & Aroma' de la que procede (source_row)",
    "descriptor_id": "FK a dim_descriptor",
    "descriptor_label": "Descriptor tal como está en la fuente (sin espacios sobrantes)",
    "family_l1_as_in_source": "Primera familia de descriptor indicada en la fuente (no es una ontología nueva)",
    "is_off_flavor": "True si alguna familia de la fuente es Off-flavor/Defect/Oxidized/Rancid",
    "family_is_general_or_character": "True si todas las familias de la fuente son General/Character/Body/Stable",
    "compound_id": "FK a dim_compound",
    "cas": "Nº CAS (formato validado)",
    "cas_checksum_valid": "True si el dígito de control del CAS es correcto",
    "pubchem_cid": "CID de PubChem (de la hoja Synonyms)",
    "pubchem_cid_conflict": "True si hay CID distintos para el mismo CAS",
    "iupac_name": "Nombre IUPAC del compuesto tal como en la fuente",
    "chemical_class": "Clase química deducida por regla sobre el nombre IUPAC (vacía si la regla no aplica)",
    "chemical_class_method": "Método usado para chemical_class",
    "is_reference_standard_only": "True para patrones de panel sensorial (cafeína, quinina), no compuestos del queso",
    "only_in_taste_sheet": "True si el compuesto solo aparece en la hoja 2. Taste",
    "origin_sheets": "Hojas del Excel donde aparece",
    "pathway_id": "FK a dim_pathway",
    "pathway_label": "Ruta bioquímica asignada en la hoja Evidence",
    "cheese_id": "FK a dim_cheese",
    "cheese_name_std": "Nombre de queso estandarizado",
    "cheese_label_type": "specific | generic_category | multi_cheese | not_cheese | unresolved",
    "label_type": "specific | generic_category | multi_cheese | not_cheese | unresolved",
    "sample_qualifier": "Información de la muestra que venía dentro del nombre (p. ej. '12 months', 'cow milk')",
    "cheese_label_raw": "Texto original del queso en la fuente",
    "n_cheeses": "Nº de quesos en la celda original",
    "n_sources": "Nº de fuentes en la celda original",
    "claim_scope": ("Qué afirma la evidencia: descriptor_compound_in_cheese | compound_odor_note_only | "
                    "compound_in_cheese_no_descriptor | unsupported | not_verified"),
    "verification_status": "Estado de verificación normalizado del Excel",
    "evidence_level_raw": "Nivel de evidencia tal como en el Excel (S, B, C, A/B, B/C); la fuente no define su escala",
    "evidence_score": "Peso sugerido en el análisis (.md): 1.0 primaria, 0.6 secundaria, 0.4 probable, 0 resto",
    "use_as_cheese_descriptor_label": "True si sirve como etiqueta 'este queso tiene este descriptor'",
    "use_as_compound_odor_label": "True si sirve como etiqueta 'este compuesto huele a este descriptor'",
    "reported_value_raw": "Valor reportado en la fuente, sin interpretar",
    "rv_FD": "Número tras 'FD' en reported_value", "rv_DF": "Número tras 'DF='", "rv_OI": "Número tras 'OI'",
    "rv_OP": "Número tras 'OP'", "rv_c": "Número tras 'c'", "rv_pct": "Número tras '%'", "rv_vol": "Número tras 'vol'",
    "method_hint_gc_olfactometry": "True si el texto de evidencia menciona términos de GC-O (Charm, AEDA, FD, OAV, DF, OI, OP...)",
    "descriptor_in_source": "Descriptor literal en el documento fuente",
    "evidence_text": "Texto copiado del PDF",
    "location_in_source": "Página/tabla en la fuente",
    "source_ids": "Fuentes de la evidencia (separadas por |)",
    "source_id": "FK a dim_source",
    "source_type": "primary | review | book (según el Excel)",
    "short_citation": "Cita corta 'Autor año'", "first_author": "Primer autor", "year": "Año",
    "n_mentions": "Nº de veces que se menciona en el Excel",
    "cited_primary_source_id": "FK a dim_source si la celda cita UNA sola fuente primaria presente en la base",
    "cited_primary_source_raw": "Texto original de la fuente primaria citada",
    "n_cited_primary_sources": "Nº de citas primarias en la celda",
    "possible_double_count": "True si el Excel tiene alerta de doble conteo",
    "double_counting_alert_raw": "Texto de la alerta de doble conteo",
    "unsupporting_sources_raw": "Fuentes de la fila maestra que no confirman el par",
    "split_status": "Estado de desglose en el Excel",
    "process_refs_truncated": "True si la lista de IDs de proceso estaba cortada con '…' en el Excel",
    "n_process_refs_visible": "Nº de IDs de proceso legibles",
    "notes": "Notas originales",
    "milk_species_raw": "Texto original de especie de leche",
    "milk_cow": "1 = vaca mencionada; vacío = no mencionada", "milk_sheep": "1 = oveja mencionada",
    "milk_goat": "1 = cabra mencionada", "milk_buffalo": "1 = búfala mencionada",
    "milk_species_logic": "single | mixture | alternatives | mixture_or_alternatives | comparison | unknown",
    "milk_heat_treatment_raw": "Texto original del tratamiento de la leche",
    "milk_heat_treatment": ("raw | pasteurized | thermized | raw_or_pasteurized | raw_or_thermized | "
                            "comparison | other | unknown"),
    "rennet_culture_raw": "Texto original de cuajo/cultivo",
    "coag_rennet_unspecified": "1 = menciona 'rennet' sin tipo concreto",
    "ripening_raw": "Texto original de maduración",
    "ripening_days_min": "Días mínimos (1 mes = 30 d, 1 semana = 7 d); vacío si no se indica",
    "ripening_days_max": "Días máximos; vacío si es abierto (≥, >) o no se indica",
    "ripening_label": "fresh | aged | long | young | extended | unknown (texto cualitativo de la fuente)",
    "ripening_class": "Clase por punto medio de min/max: fresh, lt_1m, 1_3m, 3_6m, 6_12m, 12_24m, gt_24m",
    "other_process_factor_raw": "Texto original de otros factores",
    "curd_cooking_temp_c": "Temperatura de cocción citada (°C)",
    "parent_cheese_id": "Queso padre (variantes con perfil propio)",
    "has_profile": "True si existe en Cheese Profiles",
    "profile_name_original": "Nombre en Cheese Profiles",
    "profile_source_raw": "Fuente del perfil",
    "profile_source_ids": "Fuentes del perfil (|)",
    "profile_from_label_only": "True si el perfil cita 'cheese label in the source' (deducido de la etiqueta)",
    "profile_completeness": "Fracción de 4 bloques conocidos (leche, tratamiento térmico, cuajo/cultivo, maduración)",
    "process_effect_id": "ID original de la hoja Process and Volatiles",
    "factor_studied_raw": "Factor estudiado (texto original)",
    "factor_category": "Factor estudiado armonizado",
    "season": "Estación si se indica (spring/summer/fall/winter)",
    "fat_content_raw": "Grasa (texto original)",
    "fat_content": "full_fat | low_fat | reduced_50pct | comparison | other | unknown",
    "condition": "Condición medida", "reference_condition": "Condición de referencia",
    "is_reference_row": "True si la fila es la propia condición de referencia",
    "compound_or_family_raw": "Compuesto o familia (texto original)",
    "is_family_level": "True si es una familia (Esters, Alcohols...) y no un compuesto",
    "pathway_according_to_source": "Ruta bioquímica según la fuente",
    "value_raw": "Valor original", "value": "Valor numérico", "detected": "False si la fuente dice ND",
    "reference_value_raw": "Valor de referencia original", "reference_value": "Valor de referencia numérico",
    "reference_detected": "False si la referencia es ND", "unit_raw": "Unidad original",
    "unit_std": "ug/kg (concentración) o unidad relativa base (ARU, TIC, AU, RA)",
    "value_type": "concentration | relative", "value_std": "Valor en unit_std",
    "reference_value_std": "Referencia en unit_std",
    "ratio_vs_reference": "value / reference_value", "log2_ratio": "log2(ratio_vs_reference)",
    "direction": "reference | up | down | equal | appears_vs_ND | not_detected_vs_reference",
    "n_evidence": "Nº de evidencias que lo apoyan", "best_verification_status": "Mejor estado de verificación",
    "max_evidence_score": "Máximo evidence_score", "any_primary_confirmation": "True si alguna evidencia es CONFIRMED_PRIMARY",
    "all_possible_double_count": "True si todas sus evidencias tienen alerta de doble conteo",
    "evidence_ids": "IDs de evidencia (|)", "n_process_measurements": "Nº de mediciones en Process and Volatiles",
    "n_detected": "Nº de mediciones detectadas", "n_not_detected": "Nº de mediciones ND",
    "reported_present": "True si alguna evidencia o medición lo reporta presente",
    "n_linked_compounds": "Nº de compuestos asociados", "linked_compound_ids": "Compuestos asociados (|)",
    "alias": "Nombre alternativo visto en las fuentes", "is_preferred": "True si es el nombre preferido",
    "n_occurrences": "Nº de apariciones", "n_aliases": "Nº de nombres distintos",
    "term": "Término individual del descriptor (separado por '/')",
    "family_token": "Familia de descriptor (token de la fuente)", "order_in_source": "Orden en la fuente",
    "n_terms": "Nº de términos en el descriptor", "n_family_tokens": "Nº de familias",
    "in_odor_aroma": "Aparece en olor/aroma", "in_taste": "Aparece en sabor",
    "in_trigeminal": "Aparece en trigeminal", "in_texture": "Aparece en textura",
    "in_master_sheet": "Aparece en la hoja maestra 1. Odor & Aroma",
    "is_unassigned": "Ruta 'not assigned'",
    "process_effect_id_ref": "ID de proceso", "marked_with_asterisk": "El ID llevaba '*' en el Excel",
    "list_truncated_in_source": "La lista original estaba truncada",
    "record_id": "ID del registro", "sensory_modality": "taste | trigeminal | texture",
    "table": "Tabla", "record_key": "Clave del registro", "field": "Campo", "problem": "Problema detectado",
}
DESC.update({
    "is_aroma_target": "True si el descriptor es una nota de aroma utilizable como objetivo (Fase 3)",
    "aroma_family": "Familia de aroma armonizada (nivel 1, Bérodier et al. 1997): lactic, vegetal, floral, fruity, toasted, animal, spicy, other",
    "berodier_family_fr": "Familia de Bérodier en francés",
    "berodier_subfamily": "Nivel 2: subfamilia de Bérodier; '[proyecto] …' = subfamilia añadida por la armonización",
    "aroma_terms": "Nivel 3: término(s) del descriptor separados por ';'",
    "berodier_term": "Término literal de Bérodier equivalente (si existe)",
    "drake_term": "Término equivalente del léxico de Drake et al. (2001)",
    "split_terms": "True si el descriptor original agrupa notas distintas que conviene separar",
    "harmonization_status": "verificado_con_fuente | inferencia_documentada | no_verificado",
    "harmonization_criterion": "Justificación de la decisión de armonización",
    "use_as_cheese_aroma_label": "use_as_cheese_descriptor_label y además descriptor de aroma válido (Fase 3)",
    "use_as_compound_aroma_label": "use_as_compound_odor_label y además descriptor de aroma válido (Fase 3)",
    "cheese_family": "Familia tecnológica del queso (Fase 1.4)",
    "secondary_technology": "Tecnologías secundarias (separadas por ';')",
    "cheese_family_status": "Estado de la clasificación tecnológica",
    "cheese_family_reference": "Fuente de la clasificación tecnológica",
    "cheese_family_criterion": "Criterio de la clasificación tecnológica",
    "country_iso": "País de origen (ISO 3166)", "pdo_pgi": "Protección (PDO/PGI/none/unknown)",
    "pdo_pgi_status": "Estado de la verificación DOP/IGP", "pdo_pgi_reference": "Fuente de la DOP/IGP",
    "spec_milk": "Leche del TIPO de queso (especificación; no de la muestra)",
    "spec_milk_cow": "1 = vaca en la especificación", "spec_milk_sheep": "1 = oveja en la especificación",
    "spec_milk_goat": "1 = cabra en la especificación", "spec_milk_buffalo": "1 = búfala en la especificación",
    "spec_milk_status": "Estado (Fase 2)", "spec_milk_reference": "Fuente (Fase 2)",
    "spec_heat_treatment": "Tratamiento térmico del tipo de queso", "spec_heat_status": "Estado (Fase 2)",
    "spec_heat_reference": "Fuente (Fase 2)", "spec_coagulant_culture": "Coagulante/cultivos del tipo de queso",
    "spec_coagulant_status": "Estado (Fase 2)", "spec_coagulant_reference": "Fuente (Fase 2)",
    "spec_ripening_days_min": "Maduración mínima del tipo de queso (días)",
    "spec_ripening_days_max": "Maduración máxima del tipo de queso (días; vacío = abierto)",
    "spec_ripening_class": "Clase de maduración del tipo de queso", "spec_ripening_status": "Estado (Fase 2)",
    "spec_ripening_reference": "Fuente (Fase 2)", "spec_completeness": "Fracción de los 4 bloques del tipo de queso con valor",
    "resolution_status": "Estado de la resolución de 'check in the table' (Fase 1.1)",
    "resolution_criterion": "Criterio de la resolución de 'check in the table'",
    "fase": "Fase del plan", "tabla": "Tabla afectada", "clave": "Registro afectado", "campo": "Campo",
    "valor_anterior": "Valor en v1", "valor_nuevo": "Valor en v2", "estado": "Estado de la decisión",
    "referencia": "Fuente", "criterio": "Justificación",
    "comprobacion": "Comprobación de calidad", "resultado": "OK / FALLO", "detalle": "Detalle",
})
for _c in list(DESC):
    if _c.startswith("spec_") or _c in ("cheese_family", "secondary_technology", "country_iso", "pdo_pgi"):
        DESC["cheese_" + _c] = "Del tipo de queso (dim_cheese): " + DESC[_c]
PREFIX = {"coag_": "1 = mencionado en cuajo/cultivo: ", "cult_": "1 = mencionado en cuajo/cultivo: ",
          "mold_": "1 = mencionado en cuajo/cultivo: ", "flora_": "1 = mencionado en cuajo/cultivo: ",
          "enz_": "1 = mencionado en cuajo/cultivo: ", "proc_": "1 = mencionado en 'otros factores': "}
dd = []
_all = [(os.path.basename(d_), f) for d_ in (OUT_MODEL, OUT_SUPPORT) for f in sorted(os.listdir(d_))]
for sub, fname in _all:
    if not fname.endswith(".csv") or fname == "data_dictionary.csv":
        continue
    df = pd.read_csv(os.path.join(OUT, sub, fname), nrows=1000, low_memory=False)
    fname = f"{sub}/{fname}"
    for col in df.columns:
        base = col[4:] if col.startswith("ctx_") else col
        d = DESC.get(base)
        if d is None:
            for p_, txt in PREFIX.items():
                if base.startswith(p_):
                    d = txt + base
        if col.startswith("ctx_"):
            d = "Contexto de producción asignado a la fila en la fuente. " + (d or base)
        if d is None:
            d = ("Texto original de la fuente (sin interpretar)" if col.endswith("_raw")
                 else "Columna original del Excel, renombrada a snake_case")
        dd.append(dict(table=fname, column=col, dtype=str(df[col].dtype), description=d))
write(pd.DataFrame(dd), "data_dictionary.csv")
