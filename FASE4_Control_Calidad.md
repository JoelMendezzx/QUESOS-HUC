# Fase 4 — Control de calidad

**Base resultante:** `v3-fases456` (parte de la Fase 4). Se parte de `v2-harmonized`, que se conserva.
**Código:**
- [`scripts/fetch_external.py`](scripts/fetch_external.py): descarga y guarda en caché las fuentes externas.
- [`scripts/phase4_quality.py`](scripts/phase4_quality.py): reglas de verificación.
- [`scripts/build_clean_db.py`](scripts/build_clean_db.py): integración en la base.

**Fuentes externas** (guardadas en caché, con URL y fecha, en [`data_external/`](data_external/)):
- PubChem PUG-REST (NCBI): identificadores, propiedades y sinónimos.
- Flavornet (Acree & Arn, Cornell University, http://www.flavornet.org/d_odors.html): índice de olores de compuestos detectados por cromatografía con olfacción (GC-O), con 734 compuestos identificados por CAS.

## Resumen

| Problema pendiente | Total | Resuelto con fuente | Resuelto por inferencia | Sin evidencia suficiente |
|---|---|---|---|---|
| Evidencias `pending` en la fuente | 53 | 27 | 15 | 11 |
| Pares descriptor–compuesto por confirmar | 138 | 15 | 49 | 74 |
| Compuestos sin CID | 38 | 33 completados | — | 5 |
| Compuestos sin CAS | 16 | — | 11 completados | 5 |
| CID del Excel comprobados con PubChem | 166 | 165 confirmados | 1 conservado (PubChem no resuelve su CAS) | — |
| Listas de referencias de proceso cortadas («…») | 369 | 73 con enlaces exactos recalculados | — | 296 (las listas originales no son reconstruibles) |
| Estatus de Curioni 2002 | 1 | Revisión, confirmado | — | — |
| Duplicados por estudio en las etiquetas | — | 31 detectados y marcados | — | — |

---

## 1. Evidencias pendientes (53)

Archivo: [`clean/soporte/qa_pending_evidence_resolution.csv`](clean/soporte/qa_pending_evidence_resolution.csv)

| Resolución | n | Estado |
|---|---|---|
| El mismo par descriptor–compuesto está confirmado en otra evidencia del Excel | 24 | `verificado_con_fuente` |
| Flavornet confirma el olor exacto del compuesto | 3 | `verificado_con_fuente` |
| Queso identificado en el texto del PDF (Fase 1, «check in the table») | 8 | `inferencia_documentada` |
| Flavornet registra un olor de la misma familia de Bérodier | 7 | `inferencia_documentada` |
| Sin confirmación (Flavornet no lo registra, o el compuesto no figura) | 8 | `no_verificado` |
| Queso no identificable en el texto | 3 | `no_verificado` |

**Límite:** en las 42 evidencias del tipo «pending: assign cheese/source», el **par** descriptor–compuesto se pudo verificar, pero **el queso y la fuente concretos de la fila no**. La fila maestra del Excel lista varios quesos y fuentes sin indicar cuál corresponde, y sin los documentos originales no se pueden asignar. Por eso estas filas siguen sin servir como etiqueta queso–aroma; sí sirven como etiqueta compuesto–olor.

## 2. Pares descriptor–compuesto por confirmar (138)

Archivo: [`clean/soporte/qa_pending_confirmation.csv`](clean/soporte/qa_pending_confirmation.csv) (columnas `resolucion`, `estado`, `flavornet_olores`, `criterio`)

| Resolución | n | Estado |
|---|---|---|
| Confirmado externamente: Flavornet da el mismo término de olor | 15 | `verificado_con_fuente` |
| Compatible al nivel de familia: Flavornet da un olor de la misma familia | 49 | `inferencia_documentada` |
| No confirmado | 74 | `no_verificado` |

**Método:** cada término de olor de Flavornet (197 términos) se asignó a una familia de Bérodier. Las asignaciones están en `FN_FAMILY` de [`phase4_quality.py`](scripts/phase4_quality.py), marcadas «V» si el término aparece en la rueda de Bérodier e «I» si se asignó por analogía. La comparación de términos usa una normalización léxica mínima: singular/plural, sufijos «-y» y «-like».

**Por qué Flavornet:** recoge olores observados en cromatografía con olfacción e identifica los compuestos por número CAS. Cubre **155 de los 188 compuestos con CAS** de la base y es independiente de las fuentes del Excel.

**Límite:** Flavornet suele dar 1–3 notas por compuesto. Que no registre una nota **no prueba** que el compuesto no la tenga, así que «no confirmado» no es un negativo.

### Contraste de todos los pares compuesto–familia (modelo B)

Los 484 pares compuesto–descriptor de aroma de [`fact_compound_odor.csv`](clean/modelo/fact_compound_odor.csv) tienen ahora la columna `flavornet_support`:

| Soporte en Flavornet | n | % |
|---|---|---|
| Mismo término de olor | 117 | 24 % |
| Misma familia de Bérodier | 179 | 37 % |
| El compuesto tiene otras notas en Flavornet | 151 | 31 % |
| El compuesto no está en Flavornet | 37 | 8 % |

Es decir, un **61 %** de los pares de la base coincide con Flavornet al menos en la familia de aroma.

## 3. Identificadores químicos (PubChem)

Columnas nuevas en [`dim_compound.csv`](clean/soporte/dim_compound.csv): `pubchem_cid_final`, `cid_status`, `cid_note`, `cas_final`, `cas_status`, `cas_note`, `in_flavornet`, `flavornet_odors`.

- **CID:**
  - **165 de los 166** CID que traía el Excel **coinciden** con el que PubChem asigna a su CAS. El otro (lactona 5-[(2Z)-oct-2-en-1-yl]oxolan-2-one) se conserva porque PubChem no resuelve su CAS.
  - Se completaron **33 CID** que faltaban: 22 a partir del CAS (`verificado_con_fuente`) y 11 buscando el nombre IUPAC (`inferencia_documentada`).
  - Quedan **5 sin CID:** «1,3-pentadieno», «mineral salts», quinina clorhidrato, sacarosa (nombre mal escrito en el Excel: «fructofuranosy») y glutamato (anión).
- **CAS:** se completaron **11** con el primer sinónimo de PubChem que tiene formato y dígito de control válidos (`inferencia_documentada`, se listan los candidatos). Por ejemplo, ácido cítrico 77-92-9 y cafeína 58-08-2. Quedan **5 sin CAS**: los mismos 5 compuestos.
- **Propiedades** de 199 compuestos en [`clean/modelo/compound_properties.csv`](clean/modelo/compound_properties.csv): fórmula, peso molecular, SMILES, InChIKey, XLogP, TPSA, donantes y aceptores de puentes de H, enlaces rotables, átomos pesados y la huella molecular **Fingerprint2D** de PubChem (CACTVS, 881 bits).

## 4. Referencias de proceso cortadas (369)

- **Por qué no se reconstruyen las listas originales:** se comprobó si la lista original se puede regenerar con una regla. La regla «mismo CAS» reproduce **695 de las 874 listas completas**; el resto incluye enlaces marcados con «*» a filas de familias químicas, cuyo criterio no se puede deducir. Inventar la parte oculta de las 369 listas cortadas sería especular, así que **no se hizo**.
- **Qué se hizo:**
  - Se añadieron a [`bridge_evidence_process.csv`](clean/soporte/bridge_evidence_process.csv) los **enlaces exactos y verificables** evidencia → medición de proceso con el **mismo compuesto**: 3.181 enlaces, columna `link_method = mismo_compuesto (recalculado)`.
  - Se conservan los IDs visibles de las listas originales (`lista_original_visible`).
  - Se marcan las evidencias con lista cortada (`evidence_list_truncated`).
- **Resultado:** 73 de las 369 evidencias con lista cortada tienen ahora enlaces exactos a mediciones de su compuesto. En las otras 296, el compuesto no tiene mediciones de proceso propias: sus enlaces eran a familias químicas.

## 5. Estatus de Curioni 2002 e independencia de los estudios

- **Verificación:** Curioni, P.M.G. & Bosset, J.O. (2002). *Key odorants in various cheese types as determined by gas chromatography-olfactometry*. International Dairy Journal 12(12):959–984, DOI 10.1016/S0958-6946(02)00124-3. **Es una revisión**: compila en nueve tablas los odorantes descritos por GC-O en distintos quesos. Se registró en `dim_source.bibliographic_note`.
- **Corrección:** en el Excel, Curioni 2002 aparecía como «fuente primaria citada». Ahora `fact_evidence` y la tabla plana tienen:
  - `independent_study_keys`: estudios primarios reales citados, **excluyendo la revisión**. Al separar las citas múltiples aparecen estudios antes ocultos, como Carbonell 2002, Barron 2005 o Le Quéré 1998.
  - `only_via_review`: la evidencia solo se apoya en la revisión. Ocurre en **235 de 974 etiquetas** queso–aroma.
  - `study_group_key`: estudio para agrupar en la validación.

## 6. Duplicados bibliográficos

- **Duplicado:** misma combinación queso + descriptor + compuesto + estudio de agrupación. Se conserva la evidencia de mayor `evidence_score` y las demás se marcan con `duplicate_of_evidence`.
- **Resultado:** **31 duplicados**. La etiqueta recomendada pasa a `use_as_cheese_aroma_label_dedup` (943 filas, antes 974).

## 7. Asociaciones compuesto–queso–descriptor

- La tabla plana incluye `flavornet_support` en cada fila, para filtrar o ponderar etiquetas según su respaldo externo.
- **Coherencia por familia** (pares compuesto–descriptor con al menos la familia confirmada por Flavornet):

| Familia | Coincide (término o familia) | Total con Flavornet |
|---|---|---|
| fruity | 89 | 121 |
| vegetal | 60 | 86 |
| other | 79 | 106 |
| toasted | 26 | 41 |
| floral | 16 | 31 |
| animal | 16 | 34 |
| lactic | 8 | 23 |

Las familias **lactic** y **animal** son las que menos coinciden con Flavornet. Probable explicación: sus notas («cheesy», «buttery», «goaty») dependen más del contexto del queso que del compuesto aislado. Es una limitación a tener en cuenta en la Fase 5.

## Limitaciones

- Ninguno de los artículos originales de las evidencias pendientes estaba disponible en acceso abierto (Moio 1998/2000, Milo 1997, Boscaini 2003). Por eso las asignaciones queso/fuente de esas filas no se recuperaron.
- Flavornet es una base resumida, no exhaustiva; su ausencia no equivale a un negativo.
- Las asignaciones de los términos de Flavornet a familias de Bérodier marcadas «I» son interpretativas y están documentadas en el código.
