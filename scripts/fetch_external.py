"""
Descarga (y guarda en caché) datos externos verificables para la Fase 4 y la Fase 5.

- PubChem PUG-REST: CID por CAS o por nombre, propiedades, SMILES, InChIKey, Fingerprint2D
  y sinónimos (para recuperar números CAS que faltan).
- Flavornet (Acree & Arn, Cornell): índice de olores -> compuestos (por CAS).

Cada respuesta se guarda en data_external/ con su URL y fecha (meta.json), para que el
proceso sea reproducible sin volver a consultar internet.

Uso: python scripts/fetch_external.py   (solo descarga lo que no está en caché)
"""
import datetime
import json
import os
import re
import time
import urllib.parse
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "data_external")
PC = os.path.join(EXT, "pubchem")
FN = os.path.join(EXT, "flavornet")
for d in (PC, FN):
    os.makedirs(d, exist_ok=True)
META_PATH = os.path.join(EXT, "meta.json")
META = json.load(open(META_PATH, encoding="utf-8")) if os.path.exists(META_PATH) else {}
API = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PROPS = ("MolecularFormula,MolecularWeight,ConnectivitySMILES,SMILES,InChIKey,IUPACName,XLogP,TPSA,"
         "HBondDonorCount,HBondAcceptorCount,RotatableBondCount,HeavyAtomCount,Fingerprint2D")


def get(url, path, binary=False):
    if os.path.exists(path):
        return open(path, "rb" if binary else "r", encoding=None if binary else "utf-8").read()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                data = b'{"Fault": {"Code": "PUGREST.NotFound"}}'
                break
            time.sleep(2 + attempt * 3)
        except Exception:
            time.sleep(2 + attempt * 3)
    else:
        return None
    with open(path, "wb") as f:
        f.write(data)
    META[os.path.relpath(path, EXT).replace("\\", "/")] = dict(url=url, retrieved=datetime.date.today().isoformat())
    time.sleep(0.25)  # respeta el límite de PubChem (≤ 5 peticiones/s)
    return data if binary else data.decode("utf-8", "replace")


def safe(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:120]


# ---------------------------------------------------------------- Flavornet
get("http://www.flavornet.org/d_odors.html", os.path.join(FN, "d_odors.html"))

# ---------------------------------------------------------------- PubChem
cmp = pd.read_csv(os.path.join(ROOT, "clean", "soporte", "dim_compound.csv"))
for _, r in cmp.iterrows():
    cid = int(r.pubchem_cid) if pd.notna(r.pubchem_cid) else None
    # 1) CID a partir del CAS (comprueba o completa el CID del Excel)
    if pd.notna(r.cas):
        get(f"{API}/compound/name/{urllib.parse.quote(r.cas)}/cids/JSON",
            os.path.join(PC, f"cas_{safe(r.cas)}.json"))
    # 2) CID a partir del nombre IUPAC (para compuestos sin CAS)
    if pd.isna(r.cas):
        get(f"{API}/compound/name/{urllib.parse.quote(r.iupac_name)}/cids/JSON",
            os.path.join(PC, f"name_{safe(r.iupac_name)}.json"))

# CIDs a consultar: los del Excel + los encontrados
cids = set(int(x) for x in cmp.pubchem_cid.dropna())
for fn in os.listdir(PC):
    if fn.startswith(("cas_", "name_")):
        try:
            d = json.load(open(os.path.join(PC, fn), encoding="utf-8"))
            cids.update(d.get("IdentifierList", {}).get("CID", [])[:3])
        except json.JSONDecodeError:
            pass
for cid in sorted(cids):
    get(f"{API}/compound/cid/{cid}/property/{PROPS}/JSON", os.path.join(PC, f"prop_{cid}.json"))
    get(f"{API}/compound/cid/{cid}/synonyms/JSON", os.path.join(PC, f"syn_{cid}.json"))

json.dump(META, open(META_PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("Archivos en caché:", len(os.listdir(PC)), "PubChem;", len(os.listdir(FN)), "Flavornet")

# ---------------------------------------------------------------- Fase 5: compuestos de Flavornet (validación externa)
import sys
if "--flavornet" in sys.argv:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import phase4_quality as P4
    fn = P4.load_flavornet()
    known = set(cmp.cas.dropna())
    new_cids = set()
    for cas in sorted(fn):
        if cas in known:
            continue
        d = get(f"{API}/compound/name/{urllib.parse.quote(cas)}/cids/JSON", os.path.join(PC, f"cas_{safe(cas)}.json"))
        try:
            ids = json.loads(d).get("IdentifierList", {}).get("CID", []) if d else []
        except json.JSONDecodeError:
            ids = []
        if ids:
            new_cids.add(ids[0])
    for cid in sorted(new_cids):
        get(f"{API}/compound/cid/{cid}/property/{PROPS}/JSON", os.path.join(PC, f"prop_{cid}.json"))
    json.dump(META, open(META_PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("Compuestos externos de Flavornet con CID:", len(new_cids))
