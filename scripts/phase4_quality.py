"""
Fase 4 — Control de calidad con fuentes externas (PubChem, Flavornet) y reglas verificables.

Funciones usadas por build_clean_db.py (lee solo la caché de data_external/; no accede a internet).
"""
import base64
import html
import json
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "data_external")
V, I, N = "verificado_con_fuente", "inferencia_documentada", "no_verificado"
PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/compound/{}"
FLAVORNET_URL = "http://www.flavornet.org/d_odors.html"

# ---------------------------------------------------------------------------
# Términos de olor de Flavornet -> familia de Bérodier (nivel 1)
# 'V' = el término (o su traducción directa) aparece en la rueda de Bérodier; 'I' = por analogía.
# Términos generales o sin familia clara (sweet, fresh, warm, alkane, amine, bitter, ester, lactone,
# yeast, soy, tea, tobacco, hummus, crushed bug, box tree, wet cloth, thiamin, fish…) no se asignan.
# ---------------------------------------------------------------------------
FN_FAMILY = {
    # lactique
    "butter": ("lactic", "V"), "cream": ("lactic", "V"), "hot milk": ("lactic", "V"), "cheese": ("lactic", "I"),
    # végétal
    "grass": ("vegetal", "V"), "green": ("vegetal", "I"), "green leaf": ("vegetal", "I"), "leaf": ("vegetal", "I"),
    "straw": ("vegetal", "I"), "cabbage": ("vegetal", "I"), "broccoli": ("vegetal", "I"),
    "boiled vegetable": ("vegetal", "V"), "cooked vegetable": ("vegetal", "V"), "cooked potato": ("vegetal", "V"),
    "potato": ("vegetal", "V"), "celery": ("vegetal", "V"), "pea": ("vegetal", "V"), "green bean": ("vegetal", "I"),
    "garlic": ("vegetal", "V"), "onion": ("vegetal", "V"), "mushroom": ("vegetal", "V"), "truffle": ("vegetal", "I"),
    "earth": ("vegetal", "I"), "moss": ("vegetal", "I"), "wood": ("vegetal", "V"), "pine": ("vegetal", "I"),
    "resin": ("vegetal", "I"), "balsamic": ("vegetal", "I"), "tomato": ("vegetal", "I"),
    "tomato leaf": ("vegetal", "I"), "cucumber": ("vegetal", "I"), "lettuce": ("vegetal", "I"),
    "green pepper": ("vegetal", "I"), "beet": ("vegetal", "I"), "carrot": ("vegetal", "I"), "herb": ("vegetal", "I"),
    "seaweed": ("vegetal", "I"),
    # floral
    "flower": ("floral", "V"), "rose": ("floral", "V"), "violet": ("floral", "V"), "jasmine": ("floral", "I"),
    "lavender": ("floral", "I"), "lilac": ("floral", "I"), "lily": ("floral", "I"), "magnolia": ("floral", "I"),
    "muguet": ("floral", "I"), "hyacinth": ("floral", "I"), "geranium": ("floral", "I"), "orris": ("floral", "I"),
    "camomile": ("floral", "I"), "hawthorne": ("floral", "I"), "honey": ("floral", "V"), "apple. rose": ("floral", "I"),
    # fruité
    "fruit": ("fruity", "I"), "apple": ("fruity", "V"), "apple peel": ("fruity", "I"), "apricot": ("fruity", "V"),
    "banana": ("fruity", "V"), "peach": ("fruity", "I"), "pear": ("fruity", "I"), "pineapple": ("fruity", "V"),
    "plum": ("fruity", "I"), "prune": ("fruity", "I"), "grape": ("fruity", "I"), "grapefruit": ("fruity", "V"),
    "lemon": ("fruity", "V"), "orange": ("fruity", "V"), "orange peel": ("fruity", "V"), "mandarin": ("fruity", "I"),
    "citrus": ("fruity", "V"), "tart lime": ("fruity", "I"), "melon": ("fruity", "I"), "watermelon": ("fruity", "I"),
    "strawberry": ("fruity", "I"), "raspberry": ("fruity", "I"), "black currant": ("fruity", "I"),
    "coconut": ("fruity", "I"), "almond": ("fruity", "V"), "bitter almond": ("fruity", "V"),
    "almond shell": ("fruity", "I"), "nut": ("fruity", "V"), "hazelnut": ("fruity", "V"), "walnut": ("fruity", "V"),
    "wine": ("fruity", "I"), "whiskey": ("fruity", "I"), "cognac": ("fruity", "I"), "alcohol": ("fruity", "I"),
    # torréfié
    "roast": ("toasted", "I"), "roasted nut": ("toasted", "V"), "roasted meat": ("toasted", "I"),
    "burnt": ("toasted", "V"), "burnt sugar": ("toasted", "V"), "caramel": ("toasted", "V"),
    "brown sugar": ("toasted", "I"), "butterscotch": ("toasted", "I"), "maple": ("toasted", "I"),
    "cocoa": ("toasted", "V"), "coffee": ("toasted", "V"), "smoke": ("toasted", "V"), "popcorn": ("toasted", "I"),
    "bread": ("toasted", "I"), "biscuit": ("toasted", "I"), "baked": ("toasted", "I"), "fried": ("toasted", "I"),
    "malt": ("toasted", "I"), "vanilla": ("toasted", "V"), "peanut butter": ("toasted", "I"), "tar": ("toasted", "I"),
    # animal
    "sweat": ("animal", "V"), "meat": ("animal", "V"), "cooked meat": ("animal", "V"), "meat broth": ("animal", "V"),
    "roast beef": ("animal", "I"), "foxy": ("animal", "I"), "cat": ("animal", "I"),
    # épicé
    "spice": ("spicy", "V"), "weak spice": ("spicy", "I"), "clove": ("spicy", "V"), "cinnamon": ("spicy", "I"),
    "nutmeg": ("spicy", "V"), "pepper": ("spicy", "V"), "curry": ("spicy", "I"), "anise": ("spicy", "I"),
    "fennel": ("spicy", "I"), "dill": ("spicy", "I"), "caraway": ("spicy", "I"), "coriander": ("spicy", "I"),
    "basil": ("spicy", "I"), "thyme": ("spicy", "I"), "licorice": ("spicy", "I"), "mint": ("spicy", "V"),
    "peppermint": ("spicy", "V"), "spearmint": ("spicy", "V"), "menthol": ("spicy", "I"),
    "wintergreen": ("spicy", "I"), "camphor": ("spicy", "I"), "horseradish": ("spicy", "I"), "mustard": ("spicy", "I"),
    # autres
    "rancid": ("other", "V"), "soap": ("other", "V"), "wax": ("other", "I"), "fat": ("other", "I"),
    "tallow": ("other", "I"), "oil": ("other", "I"), "solvent": ("other", "I"), "chemical": ("other", "I"),
    "plastic": ("other", "I"), "rubber": ("other", "V"), "paint": ("other", "I"), "gasoline": ("other", "I"),
    "medicine": ("other", "I"), "phenol": ("other", "I"), "sulfur": ("other", "V"), "putrid": ("other", "V"),
    "fecal": ("other", "I"), "urine": ("other", "I"), "sour": ("other", "V"), "acid": ("other", "I"),
    "pungent": ("other", "V"), "sharp": ("other", "I"), "metal": ("other", "I"), "mold": ("other", "V"),
    "mildew": ("other", "V"), "must": ("other", "V"), "dust": ("other", "I"), "paper": ("other", "I"),
    "cardboard": ("other", "I"), "ether": ("other", "I"), "vinyl": ("other", "I"), "pesticide": ("other", "I"),
    "mothball": ("other", "I"), "cotton candy": ("other", "I"), "marshmallow": ("other", "I"),
    "terpentine": ("other", "I"), "turpentine": ("other", "I"), "cologne": ("other", "I"),
}


def stem(w):
    """Normalización léxica mínima para comparar términos de olor (inglés)."""
    w = re.sub(r"[^a-z ]", " ", str(w).lower().replace("-like", "").replace(" like", ""))
    w = re.sub(r"\s+", " ", w).strip()
    out = []
    for t in w.split():
        if len(t) > 4 and t.endswith("y"):
            t = t[:-1]
            if len(t) > 3 and t[-1] == t[-2]:
                t = t[:-1]
        if len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        if len(t) > 4 and t.endswith("e"):
            t = t[:-1]
        out.append(t)
    return " ".join(out)


# ---------------------------------------------------------------------------
def load_flavornet():
    path = os.path.join(EXT, "flavornet", "d_odors.html")
    if not os.path.exists(path):
        return {}
    t = open(path, encoding="latin-1").read()
    m = {}
    for odor, cell in re.findall(r"<tr>\s*<td[^>]*>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>", t, re.S):
        odor = html.unescape(re.sub("<[^>]+>", "", odor)).strip()
        for cas, _name in re.findall(r"info/([0-9-]+)\.html[^>]*>([^<]+)</a>", cell):
            m.setdefault(cas, set()).add(odor)
    return m


def _json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _safe(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:120]


def _cas_ok(c):
    if not re.fullmatch(r"\d{2,7}-\d{2}-\d", c or ""):
        return False
    a, b, k = c.split("-")
    return sum((i + 1) * int(d) for i, d in enumerate((a + b)[::-1])) % 10 == int(k)


def enrich_compounds(dim_compound):
    """Completa/verifica CID y CAS con PubChem y añade propiedades. Devuelve (dim_compound, props, log)."""
    pc = os.path.join(EXT, "pubchem")
    log, props = [], []
    dc = dim_compound.copy()
    for c in ["pubchem_cid_final", "cid_status", "cid_note", "cas_final", "cas_status", "cas_note"]:
        dc[c] = None
    for i, r in dc.iterrows():
        cid_x = int(r.pubchem_cid) if pd.notna(r.pubchem_cid) else None
        cid_cas = None
        if pd.notna(r.cas):
            d = _json(os.path.join(pc, f"cas_{_safe(r.cas)}.json"))
            ids = (d or {}).get("IdentifierList", {}).get("CID", [])
            cid_cas = ids[0] if ids else None
        cid_name = None
        if pd.isna(r.cas):
            d = _json(os.path.join(pc, f"name_{_safe(r.iupac_name)}.json"))
            ids = (d or {}).get("IdentifierList", {}).get("CID", [])
            cid_name = ids[0] if ids else None
        # --- CID final
        if cid_x and cid_cas and cid_x == cid_cas:
            cid, st, note = cid_x, V, "CID del Excel confirmado: PubChem devuelve el mismo CID para el CAS."
        elif cid_x and cid_cas and cid_x != cid_cas:
            cid, st, note = cid_cas, I, f"CID del Excel ({cid_x}) distinto del CID que PubChem asigna al CAS ({cid_cas}); se usa el del CAS (p. ej. estereoisómero o sal)."
        elif cid_x and not cid_cas:
            cid, st, note = cid_x, I, "CID del Excel conservado; PubChem no devolvió CID para el CAS."
        elif cid_cas:
            cid, st, note = cid_cas, V, "CID completado: PubChem lo asigna al CAS del compuesto."
        elif cid_name:
            cid, st, note = cid_name, I, "CID obtenido por búsqueda del nombre IUPAC en PubChem (sin CAS)."
        else:
            cid, st, note = None, N, "PubChem no encontró el compuesto por CAS ni por nombre."
        dc.loc[i, ["pubchem_cid_final", "cid_status", "cid_note"]] = [cid, st, note]
        # --- CAS final
        cas, cst, cnote = r.cas, (V if pd.notna(r.cas) else None), None
        if pd.isna(r.cas) and cid:
            syn = _json(os.path.join(pc, f"syn_{cid}.json"))
            names = ((syn or {}).get("InformationList", {}).get("Information") or [{}])[0].get("Synonym", [])
            cands = [s for s in names if _cas_ok(s)]
            if cands:
                cas, cst = cands[0], I
                cnote = f"CAS tomado del primer sinónimo con formato y dígito de control válidos en PubChem (candidatos: {', '.join(cands[:3])})."
            else:
                cst, cnote = N, "PubChem no lista ningún número CAS válido para este compuesto."
        elif pd.isna(r.cas):
            cst, cnote = N, "Sin CID: no se pudo buscar el CAS."
        dc.loc[i, ["cas_final", "cas_status", "cas_note"]] = [cas, cst, cnote]
        if (cid != cid_x) or (pd.isna(r.cas) and cas is not None):
            log.append(dict(fase="4", tabla="dim_compound", clave=r.compound_id, campo="CID/CAS",
                            valor_anterior=f"{cid_x} / {r.cas}", valor_nuevo=f"{cid} / {cas}",
                            estado=st if cid != cid_x else cst, referencia=PUBCHEM_URL.format(cid) if cid else "",
                            criterio=note if cid != cid_x else cnote))
        # --- propiedades
        if cid:
            d = _json(os.path.join(pc, f"prop_{cid}.json"))
            p = ((d or {}).get("PropertyTable", {}).get("Properties") or [{}])[0]
            if p:
                props.append(dict(
                    compound_id=r.compound_id, pubchem_cid=cid, iupac_name_pubchem=p.get("IUPACName"),
                    molecular_formula=p.get("MolecularFormula"),
                    molecular_weight=float(p["MolecularWeight"]) if p.get("MolecularWeight") else None,
                    smiles=p.get("SMILES"), connectivity_smiles=p.get("ConnectivitySMILES"),
                    inchikey=p.get("InChIKey"), xlogp=p.get("XLogP"), tpsa=p.get("TPSA"),
                    hbond_donors=p.get("HBondDonorCount"), hbond_acceptors=p.get("HBondAcceptorCount"),
                    rotatable_bonds=p.get("RotatableBondCount"), heavy_atoms=p.get("HeavyAtomCount"),
                    fingerprint2d_b64=p.get("Fingerprint2D"), source=PUBCHEM_URL.format(cid)))
    return dc, pd.DataFrame(props), log


def fingerprint_bits(b64):
    """Decodifica el Fingerprint2D de PubChem (CACTVS, 881 bits; 4 bytes de longitud + datos)."""
    if not isinstance(b64, str):
        return None
    raw = base64.b64decode(b64)[4:]
    bits = []
    for byte in raw:
        bits.extend((byte >> (7 - k)) & 1 for k in range(8))
    return bits[:881]


def flavornet_check(cas, terms, family, fn):
    """Compara un par compuesto-descriptor con Flavornet.
    Devuelve (soporte, estado, términos Flavornet, término coincidente)."""
    if not isinstance(cas, str) or cas not in fn:
        return "no_en_flavornet", N, None, None
    odors = sorted(fn[cas])
    st_terms = {stem(t) for t in str(terms or "").split(";") if t.strip()}
    for o in odors:
        so = stem(o)
        if so in st_terms or any(so == x or (len(so) > 3 and (so in x.split() or x in so.split())) for x in st_terms):
            return "termino", V, "; ".join(odors), o
    fams = {FN_FAMILY[o][0] for o in odors if o in FN_FAMILY}
    if family and family in fams:
        return "familia", I, "; ".join(odors), None
    return "sin_coincidencia", N, "; ".join(odors), None
