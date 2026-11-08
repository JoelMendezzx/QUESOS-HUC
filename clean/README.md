# Base de datos HUC limpia (CSV)

Generada por [`scripts/build_clean_db.py`](../scripts/build_clean_db.py) a partir de
`HUC-Database descriptor  compound  cheese English.xlsx`, siguiendo
[`Analisis_y_mejoras_HUC-Database.md`](../Analisis_y_mejoras_HUC-Database.md).

**Regla aplicada: no se inventa información.** Solo se reorganiza, normaliza y separa lo que ya está en el Excel.
Lo que la fuente no dice queda vacío. El Excel original no se modifica.

Regenerar: `python scripts/build_clean_db.py`

Formato: CSV UTF-8 (con BOM, para que Excel muestre bien los acentos), separador `,`, decimal `.`.
Listas dentro de una celda (pocas, solo en columnas `*_ids`) van separadas por `|`.

---

## Estructura de carpetas

```
clean/
├── modelo/                      ← LO QUE SE USA PARA ENTRENAR
│   ├── ml_evidence_flat.csv       tabla principal (todo unido)
│   ├── fact_process_effect.csv    paso 1: proceso → compuestos
│   ├── fact_compound_odor.csv     paso 2: compuestos → descriptores
│   └── data_dictionary.csv        qué significa cada columna
└── soporte/                     ← respaldo: no hace falta para entrenar
    ├── dim_*, *_alias, descriptor_*   catálogos (quesos, compuestos, descriptores, fuentes, rutas)
    ├── bridge_*, fact_cheese_*        relaciones de las que se construye la tabla principal
    ├── fact_evidence.csv              hoja Evidence limpia (1 fila por evidencia)
    ├── nonaroma_*, taste_compound     sabor, trigeminal y textura (fuera del objetivo de aroma)
    └── qa_*                           control de calidad para revisar a mano
```

## Versión actual: `v2-harmonized`

Incluye las Fases 1–3 de armonización:
- **Quesos:** familia tecnológica, país y DOP/IGP.
- **Producción:** valores del tipo de queso en columnas `spec_*`.
- **Descriptores:** ontología de Bérodier (1997) en 3 niveles.

Los registros de cada decisión están en [`corrections/`](../corrections/) y la documentación en los archivos `FASE*_*.md`, `REFERENCIAS_VERIFICADAS.md` e `INFORME_FINAL_FASES_1_2_3.md` de la raíz del proyecto. La versión anterior se conserva en git con la etiqueta `v1-clean`.

Archivos nuevos en `soporte/`:
- `harmonization_log.csv`: cada cambio aplicado.
- `qa_checks_v2.csv`: 30 comprobaciones de calidad, todas OK.

## Novedades de la versión `v3-fases456` (Fases 4–6)

- **`modelo/compound_properties.csv`**: propiedades químicas de PubChem (SMILES, InChIKey, peso molecular, XLogP, TPSA, Fingerprint2D de 881 bits) para 199 compuestos.
- **`soporte/dim_compound.csv`**: CID y CAS verificados o completados (`*_final`, `*_status`, `*_note`) y olores de Flavornet.
- **`modelo/fact_compound_odor.csv`** y la tabla plana: `flavornet_support` (término / familia / sin coincidencia / no en Flavornet).
- **Tabla plana**:
  - `independent_study_keys`, `only_via_review` y `study_group_key`: Curioni 2002 se cuenta como revisión, no como estudio primario.
  - `duplicate_of_evidence` y **`use_as_cheese_aroma_label_dedup`**: etiqueta recomendada, sin duplicados por estudio (943 filas).
- **`soporte/qa_pending_confirmation.csv`** y **`soporte/qa_pending_evidence_resolution.csv`**: resolución de los 138 pares y las 53 evidencias pendientes.
- **`soporte/bridge_evidence_process.csv`**: enlaces exactos evidencia → proceso por compuesto (`link_method`).
- **Carpeta nueva `muestras/`** (Fase 6): datos experimentales **por muestra** de 7 estudios de acceso abierto: `study.csv`, `sample.csv`, `sample_compound.csv`, `sample_descriptor.csv` y su diccionario.
- Control de calidad: `soporte/qa_checks.csv` (37 comprobaciones).

Documentación: `FASE4_Control_Calidad.md`, `FASE5_Modelo_Compuesto_Aroma.md`, `FASE6_Extraccion_Muestras.md` e `INFORME_FINAL_FASES_4_5_6.md`.

## Archivo principal para Machine Learning

**`modelo/ml_evidence_flat.csv`** — 2.023 filas × 128 columnas. Una fila = una evidencia × un queso.
Une descriptor + compuesto + queso + variables de producción + calidad de la evidencia.

Columnas clave para filtrar:

| Columna | Uso |
|---|---|
| `claim_scope` | Qué afirma la fila (ver abajo). **Filtrar siempre por esto.** |
| **`use_as_cheese_aroma_label`** | `True` → "este queso tiene esta nota de aroma" (974 filas). **Recomendado** (v2) |
| **`use_as_compound_aroma_label`** | `True` → "este compuesto huele a esta nota" (1.402 filas). **Recomendado** (v2) |
| `aroma_family` | Familia de aroma armonizada (Bérodier). Clases recomendadas para ML: fruity, vegetal, lactic, floral, toasted, animal |
| `berodier_subfamily`, `aroma_terms` | Niveles 2 y 3 de la ontología |
| `cheese_cheese_family`, `cheese_spec_*` | Familia tecnológica y producción del **tipo** de queso (no de la muestra) |
| `ctx_*` | Producción asignada a la evidencia en la fuente (sin cambios) |
| `use_as_cheese_descriptor_label` | Etiqueta de la v1, sin excluir los términos que no son aroma (980 filas) |
| `use_as_compound_odor_label` | Ídem para compuestos (1.408 filas) |
| `evidence_score` | Peso sugerido: 1.0 primaria, 0.6 secundaria, 0.4 probable, 0 resto |
| `possible_double_count` | Alerta de doble conteo del Excel |
| `cheese_label_type` | `specific`, `generic_category`, `multi_cheese`, `not_cheese`, `unresolved` |

`claim_scope`:
- `descriptor_compound_in_cheese`: la fuente da el descriptor para ese compuesto en ese queso.
- `compound_odor_note_only`: la nota de olor es del compuesto; la fuente **no** dice que se midiera en ese queso (según las notas del propio Excel).
- `compound_in_cheese_no_descriptor`: el compuesto está en el queso, pero la fuente no da ese descriptor (`NOT CONFIRMED`).
- `unsupported` / `not_verified`: sin apoyo o sin verificar.

Filtros recomendados antes de entrenar:
- Aroma del queso: `use_as_cheese_aroma_label_dedup == True` (v3, sin duplicados por estudio).
- Olor del compuesto: `use_as_compound_aroma_label == True` (o `fact_compound_odor.csv` con `is_aroma_target == True`).
- Opcional: quitar `cheese_label_type` en (`not_cheese`, `unresolved`) y usar `evidence_score` como peso.

## Todas las tablas

**En `modelo/`:**

| Archivo | Filas | Contenido |
|---|---|---|
| `ml_evidence_flat.csv` | 2.023 | Tabla principal (ver arriba) |
| `fact_process_effect.csv` | 341 | Proceso → volátiles, con valores numéricos, unidades estandarizadas, `ratio_vs_reference`, `log2_ratio`, `direction` (modelo A) |
| `fact_compound_odor.csv` | 488 | Pares compuesto → descriptor, con `aroma_family` (modelo B) |
| `data_dictionary.csv` | 571 | Descripción de cada columna de cada tabla |

**En `soporte/`:**

| Archivo | Filas | Contenido |
|---|---|---|
| `fact_evidence.csv` | 1.836 | Hoja Evidence limpia, 1 fila por evidencia (mismas filas que el Excel) |
| `fact_cheese_compound.csv` | 747 | Pares queso → compuesto (presencia; incluye ND de la hoja de proceso) |
| `fact_cheese_descriptor.csv` | 528 | Pares queso → descriptor |
| `dim_cheese.csv` | 127 | Quesos estandarizados + perfil del Excel + familia tecnológica, país/DOP y producción del tipo (`spec_*`) |
| `cheese_alias.csv` | 282 | Cada nombre original de queso → `cheese_id` |
| `dim_compound.csv` | 204 | Un compuesto por CAS (antes 215 nombres con duplicados) |
| `compound_alias.csv` | 239 | Todos los nombres vistos de cada compuesto |
| `dim_descriptor.csv` | 426 | Descriptores de aroma (169), sabor, trigeminal y textura |
| `descriptor_term.csv` | 661 | Términos individuales de cada descriptor (separados por `/`) |
| `descriptor_family.csv` | 801 | Familias de cada descriptor, sin duplicados internos |
| `dim_source.csv` | 87 | Fuentes bibliográficas con ID (p. ej. `CUR02`, `TUN23`) |
| `dim_pathway.csv` | 20 | Rutas bioquímicas |
| `pathway_steps.csv` | 106 | Hoja Biochemical Pathways limpia |
| `bridge_*.csv` | — | Relaciones evidencia↔queso, evidencia↔fuente, evidencia↔ID de proceso, compuesto↔ruta |
| `nonaroma_*.csv`, `taste_compound.csv` | — | Sabor, trigeminal y textura, separados del dataset de aroma |
| `qa_pending_confirmation.csv` | 138 | Hoja Articles to Confirm con IDs |
| `qa_issues.csv` | 603 | **Problemas detectados que requieren revisión humana** |

---

## Qué se hizo

**Estructura**
- Fórmulas → valores. Se eliminaron las 36 columnas vacías de Evidence y se quitaron los espacios de los encabezados.
- Las celdas con varios valores pasan a formato largo (tablas puente).
- IDs estables para quesos (`CH_`), compuestos (`CP_`), descriptores (`DS_`), fuentes y rutas.
- Las 80 evidencias sin ID reciben un ID `EVX_` y quedan marcadas con `evidence_id_generated = True`.

**Quesos**
- Se corrigieron erratas (`Mozzarrella`, `Grana Tretino`, `Gruyere`, `Emmentaler`) y se unificaron mayúsculas.
- La información que iba dentro del nombre ("12 months", "cow milk", "smoked") pasa a `sample_qualifier`.
- Cada nombre se clasifica como queso concreto, categoría genérica, etiqueta con varios quesos, no-queso o sin resolver.
- Las variantes con perfil propio (`Cheddar (aged)`, `Farmhouse Cheddar`…) enlazan a su queso padre.

**Variables de producción** (el texto original siempre se conserva en `*_raw`)
- Leche: columnas `milk_cow/sheep/goat/buffalo` y `milk_species_logic` (mezcla, alternativas…).
- Tratamiento térmico: valores controlados (`raw`, `pasteurized`, `raw_or_pasteurized`…).
- Cuajo y cultivos: 25 indicadores (`coag_calf_rennet`, `mold_p_roqueforti`, `flora_washed_rind_smear`…).
- Maduración: `ripening_days_min/max` (1 mes = 30 d, 1 semana = 7 d) y `ripening_class`.
- Otros factores: indicadores `proc_smoked`, `proc_pasta_filata`, `proc_brine`… y `curd_cooking_temp_c`.

**Compuestos**
- Un registro por CAS (los 46 nombres duplicados se fusionaron) y validación del dígito de control del CAS.
- `chemical_class` se deduce por regla a partir del nombre IUPAC; el método queda indicado.
- Cafeína y quinina quedan marcadas como `is_reference_standard_only`.

**Descriptores**
- Se quitaron los espacios que creaban duplicados (`Fermented ` = `Fermented`) y las familias repetidas ("Fruity; Fruity").
- Cada descriptor se separa en sus términos y se marcan off-flavors y términos generales.

**Fuentes**
- Se unificaron 5 erratas de autor: Boscani→Boscaini, Le Quéret→Le Quéré, Rammirez→Ramirez, Fuchsmann→Fuchsman, Bintis→Bintsis.

**Proceso → volátiles**
- `ND` → `detected = False`.
- Unidades estandarizadas: mg/kg y µg/100 g → µg/kg; ARU/TIC × 10ⁿ → unidad base.
- Se recalcularon el ratio y el `log2_ratio`.
- Los 50 factores originales se agrupan en 36 categorías.

## Decisiones importantes

1. **Los CID de PubChem de la hoja `1. Odor & Aroma` no se usan.** En 26 filas, el número de CID no coincide con el número de compuestos, así que están desalineados. El CID se toma de `Synonyms`, que es consistente (cada CAS tiene un solo CID).
2. **Los indicadores (flags) valen `1` o vacío, nunca `0`.** "No mencionado" no significa "no". Cada uno debe decidir cómo imputar antes de entrenar.
3. Las etiquetas con varios quesos ("Parmesan, Grana Padano") **no se separan**: la fuente no dice qué dato corresponde a qué queso.
4. `evidence_level` (S, B, C, A/B, B/C) se deja tal cual, porque el Excel no define su escala.
5. Los valores reportados sin etiqueta (`15//ne`, `210//600`) se dejan en `reported_value_raw`, sin interpretar.

## Pendiente (requiere información que NO está en el Excel)

Estas mejoras del `.md` no se aplicaron porque habría que inventar o traer datos externos:

| Pendiente | Qué hace falta |
|---|---|
| Recuperar las 369 listas de IDs de proceso cortadas con `…` | Archivo de origen |
| Resolver 11 quesos `check in the table` y 53 filas `pending` | Revisar los PDF |
| Ontología de 3 niveles de descriptores (familia → subfamilia → descriptor) | Criterio sensorial experto + léxico de referencia |
| Rellenar maduración desconocida (≈63 % de las filas) y tratamiento térmico | Pliegos de condiciones DOP / literatura |
| País, DOP, humedad, grasa, pH y sal por queso | Fuentes externas |
| SMILES, InChIKey, umbral de olor, logP (para calcular OAV) | PubChem, Good Scents, Pyrfume |
| 16 compuestos sin CAS y 38 sin CID | PubChem |
| Significado de `evidence_level` (S, B, C) | Leyenda del autor |

Todos los casos concretos están listados en **`soporte/qa_issues.csv`**.
