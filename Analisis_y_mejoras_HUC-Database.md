# Análisis y mejoras de la base de datos HUC (quesos · compuestos · descriptores)

**Archivo analizado:** `HUC-Database descriptor  compound  cheese English.xlsx`
**Objetivo del proyecto:** *Cheese Types, Production Variables and Sensory Descriptor Harmonization for Data-Driven Aroma Prediction*
**Fecha del análisis:** 2026-11-08

---

## 0. Resumen ejecutivo

La base de datos tiene un trabajo bibliográfico muy valioso (≈1.800 evidencias trazadas a fuente y página, 215 compuestos con CAS/CID, 74 perfiles de queso, 341 mediciones de proceso→volátiles). Pero **hoy está diseñada para lectura humana, no para Machine Learning**. Los cinco problemas principales son:

1. **Celdas con varios valores** ("cow; sheep; goat", 34 compuestos en una celda, "9–12 months; fresh"). Un modelo no puede usar estas celdas: hay que pasar a **formato largo** (una fila = un hecho).
2. **Sin vocabularios controlados**: 118 nombres de queso distintos en `Evidence` y solo 39 coinciden con `Cheese Profiles`; 65 familias de descriptor con duplicados ("Fruity; Fruity", "Toasted/Vegetable" vs "Vegetable / Toasted"); nombres de compuestos en español/inglés/IUPAC mezclados.
3. **Variables de producción en texto y mayormente desconocidas**: maduración "not specified" en 1.106 de 1.836 filas (60 %), tratamiento de la leche desconocido en 579 (32 %). Nada es numérico.
4. **El descriptor es, en gran parte, una propiedad del compuesto y no del queso**: ≈400 filas dicen literalmente que *"the table gives the aroma notes of the compound… it does not say that the note was measured in each cheese"*. Si se mezcla esto con lo que sí se midió en el queso, el modelo aprende ruido.
5. **Solo hay ejemplos positivos y con doble conteo**: 65 % de las filas son "CONFIRMED (secondary)" desde libros que recopilan los mismos estudios primarios (Curioni 2002 aparece duplicado 160 veces). No existen negativos explícitos ("se buscó y no se detectó").

**Propuesta central:** reorganizar en un **esquema relacional (tablas de dimensiones + tablas de hechos)** y separar el problema de predicción en dos pasos:

```
Variables de producción ──(modelo A)──► Perfil de compuestos volátiles ──(modelo B)──► Descriptores de aroma
 (leche, tratamiento, cuajo,           (presencia / concentración /          (multi-etiqueta, jerarquía
  cultivos, maduración, etc.)           OAV / FD por compuesto)               armonizada)
                      └──────────────────────(modelo C directo, end-to-end)──────────────────────┘
```

---

## 1. Inventario de la base de datos actual

| # | Hoja | Filas × columnas | Contenido | Uso para ML |
|---|------|------------------|-----------|-------------|
| 1 | `1. Odor & Aroma` | 125 × 11 | Hoja maestra: descriptor → quesos, ruta bioquímica, leche, cuajo, maduración, compuestos, CAS, CID, fuentes | Fuente original, pero **ancha y multivalor**. No usable directamente. |
| 2 | `Evidence` | 1.836 × 66 | Hoja "explotada": una fila por descriptor × compuesto (× queso), con verificación y nivel de evidencia | **La mejor base para ML.** Necesita limpieza. |
| 3 | `Articles to Confirm` | 138 × 8 | Pares pendientes de verificar | Tabla de trabajo (QA), no de modelado. |
| 4 | `Biochemical Pathways` | 106 × 8 | Rutas: sustrato → enzima → producto → familia | Conocimiento previo; útil para *features* de compuestos y para un grafo. |
| 5 | `Process and Volatiles` | 341 × 23 | Factor de proceso → cambio en compuesto (valor, unidad, ratio vs referencia) | **Único dato cuantitativo** para el modelo A. Muy valioso. |
| 6 | `Cheese Profiles` | 74 × 7 | Variables de producción por tipo de queso | Debe convertirse en la **tabla maestra de quesos**. |
| 7 | `Synonyms` | 215 × 3 | Nombre de compuesto → CAS → CID | Debe convertirse en la **tabla maestra de compuestos**. |
| 8 | `2. Taste` | 5 × 8 | Ácido, amargo, salado, dulce, umami | Fuera del alcance de "aroma"; tiene errores (ver §2.7). |
| 9 | `3. Trigeminal` | 48 × 9 | Sensaciones trigeminales y táctiles | Mezcla trigeminal con textura. |
| 10 | `4. Texture` | 215 × 8 | Descriptores de textura | Fuera del alcance de "aroma"; útil como covariable futura. |

---

## 2. Diagnóstico detallado (problemas encontrados)

### 2.1 Problemas de estructura (todas las hojas)

| Problema | Dónde | Ejemplo / dato | Impacto en ML |
|---|---|---|---|
| Celdas multivalor separadas por `;` | Odor & Aroma, Taste, Texture, Evidence (`cheese_type`, `source_raw`) | Media de 3,8 compuestos por celda, máximo 34; 10 combinaciones distintas de leche | Imposible codificar; rompe joins |
| Listas de quesos, leches, cuajos y maduraciones **independientes** en la misma fila | Odor & Aroma | Fila "Alcohol": 13 quesos, 3 leches, 8 cuajos, 3 maduraciones. No se sabe qué leche va con qué queso | Producto cartesiano falso → etiquetas incorrectas |
| 36 columnas vacías (`R`–`BA`) | Evidence | `Unnamed: 17` … `Unnamed: 52` 100 % nulas | Ruido; confunde al exportar |
| Columna `reviewed (yes/no)` 100 % vacía | Evidence | 1.836 nulos | Control de calidad no registrado |
| Encabezados con espacios finales | Odor & Aroma, Evidence | `'Descriptor Family '`, `'Cheese Type '`, `'Milk type '`, `'biochemical pathway '` | Errores de `KeyError` en código |
| Fórmulas (XLOOKUP, INDEX/MATCH, fórmulas de matriz) en columnas clave | CAS, CID, cheese_type, n_cheeses, split_status | `=IFERROR(INDEX(Synonyms!…),"??")` | Al leer con Python/R sin Excel, aparecen vacíos o "??" |
| Listas truncadas con `…` | Evidence → `Process and Volatiles` | **369 celdas** terminan en `…` | **Pérdida de datos** (referencias cortadas) |
| Filas sin identificador | Evidence | 80 filas sin `evidence_id`, 69 sin `source_row` | Imposible trazar o deduplicar |
| Hojas con propósito de trabajo mezcladas con datos | `Articles to Confirm` | — | Separar "datos" de "QA" |

### 2.2 Quesos (`cheese_type`, `Cheese Profiles`)

- **118 nombres de queso** distintos en `Evidence`; solo **39** existen en `Cheese Profiles`.
- Variantes del mismo queso: `Cheddar`, `Farmhouse Cheddar`, `Cheddar (British Farmhouse)`, `British Cheddar`, `Cheddar (mild, regular and low-fat)`, `Cheddar (regular//low fat)`; `Parmesan`, `Parmigiano Reggiano`, `Parmesan (Parmigiano-Reggiano)`; `Gruyere` y `Gruyère` (duplicado en Profiles).
- Variables de proceso escondidas en el nombre: `Grana Padano (12 months)`, `Pecorino (6 months)`, `Low-fat Cheddar`, `Formaella (smoked)`, `Mozzarella (buffalo)`.
- Categorías genéricas mezcladas con quesos reales: `Blue cheeses (generic)`, `Washed-rind cheeses (generic)`, `Sheep/goat cheeses with vegetable rennet (La Serena, Torta del Casar…)`.
- Valor basura usado como queso: `check in the table` (11 filas).
- Erratas: `Mozzarrella`, `Grana Tretino`.
- **Desbalance fuerte**: Cheddar (324) + Camembert (300) = 34 % de las evidencias; ~60 quesos tienen < 5 filas.

### 2.3 Variables de producción

| Variable | Estado actual | Problema |
|---|---|---|
| Especie de leche | 13 valores texto: `cow`, `sheep / goat`, `goat / sheep`, `sheep or goat`, `buffalo or buffalo/cow`, `sheep (≥ 60%) and cow`, `goat (Palmera breed)` | Sinónimos, mezclas sin proporción, raza dentro de especie |
| Tratamiento térmico | `raw or pasteurized` (488), `raw (PDO) or pasteurized` (285), `not specified` (579) | 74 % ambiguo o desconocido |
| Cuajo / cultivo | 23 valores en Evidence, 42 en Process, 87 en Odor & Aroma; mezcla coagulante + cultivo iniciador + flora de superficie en un campo | Son **3 variables distintas** en una |
| Maduración | Texto: `9–12 months`, `≥ 15 months`, `4 weeks to > 52 weeks`, `long`, `aged`, `fresh (shelf life ~10 days)`; en Process: `60 days`, `peak at day 70` | No numérico; 60 % desconocido |
| Grasa | Solo en Process: `low fat`, `reduced 50%`, `low fat (6%)` | No existe en las demás hojas |
| Otros factores | `cooking at 57 °C`, `pasta filata`, `smoked`, `brine`, `no silage in the feed` en un solo campo libre | Cada uno debería ser una variable propia |

### 2.4 Descriptores sensoriales

- **169 descriptores** en `Evidence` frente a 124 en la hoja maestra; 45 aparecen solo en Evidence (`Truffle`, `Hay`, `Petrichor`, `Nacho cheese`, `Tootsie Rolls`, `Circus`, `Baby vomit`…).
- 62 descriptores son en realidad **grupos de sinónimos** unidos con `/`: `Fruit / Fruity / Pineapple / Banana`, `Coconut / Coconut-like / Peach` (coco y melocotón no son sinónimos).
- Espacios finales que crean duplicados: `Fermented ` vs `Fermented`, `Earthy / Musty `, `Nut / Nutty / Hazelnut `.
- **65 familias** con duplicados internos (`Fruity; Fruity`, `Earthy; Earthy; Mineral`, `Toasted; Toasted; Maillard`) y órdenes distintos (`Toasted/Vegetable` vs `Vegetable/ Toasted; Savory`).
- Descriptores que no son notas de aroma: `General intensity`, `Character`, `Body / Stable`, `Aged`; y la hoja Texture incluye `Aged / Age` y `Astringent` (trigeminal).
- 10 descriptores repetidos entre Texture y Trigeminal (`Astringent`, `Creamy`, `Fatty`, `Rubbery`, `Mouthfeel`…).
- Distribución muy larga: 90 de 169 descriptores tienen < 5 filas; solo 38 tienen ≥ 10 filas confirmadas.

### 2.5 Compuestos químicos (`Synonyms`, columnas CAS/CID)

- **46 filas comparten CAS** con otra: el mismo compuesto con 2–3 nombres (`heptan-1-ol`, `1-heptanol`, `heptanol`; `3-methylbutan-1-ol`, `3-methyl-butan-1-ol`, `3-methyl-1-butanol`).
- Nombres no IUPAC o en español: `2-feniletanal`, `1-octen-3-ona`, `3-metilbutanal`, `butan-2-ona`, `1,3-pentadieno`, `Sal`.
- CAS inválidos o vacíos: `?`, `2305-05-7;` (con `;` final), 1 vacío; 23 CID vacíos.
- En `Process and Volatiles`, **241 de 341 filas** son familias ("Esters", "Alcohols", "Total volatile compounds") y no compuestos con CAS.
- Falta información química útil para ML: SMILES, InChIKey, peso molecular, logP, presión de vapor, umbral de olor, clase química.

### 2.6 Datos cuantitativos (`Process and Volatiles`, `reported_value`)

- 10 unidades incomparables: `mg/kg`, `µg/kg`, `µg/100 g` (comparables entre sí) frente a `ARU × 10³`, `ARU × 10⁴`, `TIC`, `TIC × 10³`, `AU`, `RA` (relativas, dependen del equipo).
- Texto `ND` dentro de columnas numéricas (`value`, `reference condition value`).
- 115 filas sin valor.
- `reported_value` en Evidence mezcla tipos en un mismo texto: `DF=3`, `FD 81`, `OI 4 | OP 243 | FD 27`, `c 200, % 6.9`, `15//ne`, `+++`, `tr//tr`.
- Lo positivo: `ratio vs reference` ya es **adimensional y comparable** entre estudios → es la variable objetivo ideal para el modelo A.

### 2.7 Hojas Taste / Trigeminal / Texture

- `2. Taste` incluye **cafeína** (`1,3,7-Trimethylpurine-2,6-dione`) y **quinina** como compuestos: son **patrones de referencia del panel sensorial**, no compuestos del queso. Deben marcarse como `reference_standard` o eliminarse.
- CAS en Taste con `?` y `??`.
- `Exact Location` con el mismo texto repetido 6 veces dentro de la celda.
- Texture: 184 de 215 filas sin compuesto (es lógico: la textura depende de la matriz, no de volátiles).

### 2.8 Calidad de la evidencia y sesgos

| Indicador | Valor |
|---|---|
| `CONFIRMED (secondary)` | 1.186 (65 %) |
| `CONFIRMED` (fuente primaria) | 150 (8 %) |
| `NOT CONFIRMED` (la fuente da el compuesto pero no el descriptor) | 325 |
| `PROBABLE` | 56 |
| `UNSUPPORTED` | 39 |
| Sin estado | 80 |
| `source_type = book` | 1.135 (62 %) |
| Alertas de doble conteo | 258 filas |
| `evidence_level` con valores mixtos | `A/B`, `B/C` (no ordinales) |

**Sesgo clave:** la mayoría de las filas confirmadas vienen de tablas de libros que listan "el olor del compuesto" y "los quesos donde se encontró". Eso no prueba que ese olor se percibiera en ese queso.

---

## 3. Modelo de datos propuesto (esquema relacional "tidy")

Regla general: **una fila = un hecho, una columna = una variable, una celda = un valor**. Todo identificador en `snake_case`, sin espacios, sin fórmulas (valores calculados guardados como valores).

```
dim_cheese ──┐
dim_compound ├──► fact_cheese_compound   (queso contiene compuesto, con cantidad)
dim_source ──┤
             ├──► fact_compound_odor     (compuesto huele a descriptor — propiedad química)
dim_descriptor ┤
             ├──► fact_cheese_descriptor (descriptor percibido en el queso — panel sensorial / GC-O)
dim_process ─┴──► fact_process_effect    (factor de proceso cambia compuesto: ratio vs referencia)
dim_pathway ────► bridge_compound_pathway
```

### 3.1 `dim_cheese` — tabla maestra de quesos (sustituye a Cheese Profiles)

Orden de columnas recomendado (identificación → origen → leche → coagulación → cultivos → tecnología → maduración → composición → calidad del dato):

| # | Columna | Tipo | Valores permitidos / ejemplo |
|---|---|---|---|
| 1 | `cheese_id` | str (PK) | `CH_0001` |
| 2 | `cheese_name_std` | str | `Cheddar`, `Grana Padano` (un nombre canónico) |
| 3 | `cheese_name_aliases` | str (tabla aparte ideal) | `Farmhouse Cheddar|British Cheddar` |
| 4 | `is_generic_category` | bool | `true` para "Blue cheeses (generic)" |
| 5 | `parent_cheese_id` | str (FK) | variante → queso padre (Farmhouse Cheddar → Cheddar) |
| 6 | `country` | str ISO-3166 | `IT`, `FR`, `GB` |
| 7 | `pdo_pgi` | enum | `PDO`, `PGI`, `TSG`, `none`, `unknown` |
| 8 | `cheese_family` | enum | `fresh`, `pasta_filata`, `brined`, `soft_bloomy`, `soft_washed`, `blue`, `semi_hard`, `hard_cooked`, `extra_hard_grana`, `swiss_eyes`, `goat_lactic` |
| 9 | `milk_cow_frac` | float 0–1 | `1.0` |
| 10 | `milk_sheep_frac` | float 0–1 | `0.6` |
| 11 | `milk_goat_frac` | float 0–1 | `0.0` |
| 12 | `milk_buffalo_frac` | float 0–1 | `0.0` |
| 13 | `milk_species_known` | bool | `false` si no se sabe |
| 14 | `milk_heat_treatment` | enum ordinal | `raw`=0, `thermized`=1, `pasteurized`=2, `UHT`=3, `mixed`, `unknown` |
| 15 | `milk_standardization` | enum | `whole`, `partially_skimmed`, `natural_creaming`, `skimmed`, `unknown` |
| 16 | `animal_feed` | enum | `pasture`, `hay`, `silage`, `no_silage`, `mixed`, `unknown` |
| 17 | `coagulation_type` | enum | `enzymatic`, `acid`, `mixed_lactic` |
| 18 | `coagulant_source` | enum | `calf`, `adult_bovine`, `lamb_kid_paste`, `vegetable_cynara`, `microbial`, `fermentation_produced_chymosin`, `none`, `unknown` |
| 19 | `has_pregastric_esterase` | bool | `true` en pasta de cuajo de cordero/cabrito |
| 20 | `starter_type` | enum | `mesophilic`, `thermophilic`, `mixed`, `natural_whey`, `natural_milk`, `none`, `unknown` |
| 21 | `starter_citrate_positive` | bool | `true` (Lc. lactis biovar diacetylactis) |
| 22 | `adjunct_culture` | enum/bool | `lactobacillus`, `probiotic`, `none` |
| 23 | `flag_p_roqueforti` | bool | blue |
| 24 | `flag_p_camemberti` | bool | bloomy rind |
| 25 | `flag_b_linens_smear` | bool | washed rind |
| 26 | `flag_propionibacteria` | bool | Emmental |
| 27 | `flag_geotrichum` | bool | |
| 28 | `curd_cooking_temp_c` | float | `57` |
| 29 | `is_pasta_filata` | bool | |
| 30 | `salting_method` | enum | `dry`, `brine`, `milk_salting`, `curd_salting`, `mixed` |
| 31 | `is_brined_storage` | bool | Feta, Domiati |
| 32 | `is_smoked` | bool | |
| 33 | `rind_type` | enum | `none`, `natural`, `bloomy`, `washed`, `waxed`, `coated` |
| 34 | `ripening_days_min` | int | `270` |
| 35 | `ripening_days_max` | int | `365` |
| 36 | `ripening_days_typical` | int | `300` (centro o valor más citado) |
| 37 | `ripening_class` | enum ordinal | `fresh`(0) `<1m`(1) `1–3m`(2) `3–6m`(3) `6–12m`(4) `12–24m`(5) `>24m`(6) |
| 38 | `ripening_temp_c` | float | |
| 39 | `ripening_rh_pct` | float | |
| 40 | `fat_in_dry_matter_pct` | float | |
| 41 | `moisture_pct` | float | |
| 42 | `moisture_class` | enum | `extra_hard`, `hard`, `semi_hard`, `semi_soft`, `soft` (Codex) |
| 43 | `salt_pct` | float | |
| 44 | `ph` | float | |
| 45 | `source_ids` | str (FK) | fuentes de este perfil |
| 46 | `profile_completeness` | float 0–1 | % de campos 9–44 conocidos |
| 47 | `notes` | str | |

> **Importante:** toda variable desconocida debe ir como `NA`/`unknown` + una columna o flag que lo indique (no "not specified" como texto). Para ML, el hecho de "no saberlo" es informativo y se puede imputar de forma explícita.

### 3.2 `dim_compound` — tabla maestra de compuestos (sustituye a Synonyms)

| # | Columna | Tipo | Ejemplo |
|---|---|---|---|
| 1 | `compound_id` | str (PK) | `CP_0001` |
| 2 | `cas` | str validado (checksum) | `123-51-3` |
| 3 | `pubchem_cid` | int | `31260` |
| 4 | `inchikey` | str | identificador único inequívoco |
| 5 | `iupac_name` | str | `3-methylbutan-1-ol` |
| 6 | `common_name_en` | str | `isoamyl alcohol` |
| 7 | `synonyms` | tabla aparte `compound_alias` | todos los alias vistos en las fuentes |
| 8 | `smiles_canonical` | str | `CC(C)CCO` |
| 9 | `molecular_formula` | str | `C5H12O` |
| 10 | `molecular_weight` | float | `88.15` |
| 11 | `chemical_class` | enum | `acid`, `alcohol`, `aldehyde`, `ketone`, `methyl_ketone`, `ester`, `lactone`, `sulfur`, `pyrazine`, `phenol`, `terpene`, `indole`, `hydrocarbon`, `furan` |
| 12 | `carbon_number` | int | `5` |
| 13 | `is_branched` | bool | |
| 14 | `logp` | float | |
| 15 | `vapor_pressure_pa` | float | |
| 16 | `boiling_point_c` | float | |
| 17 | `odor_threshold_water_ug_kg` | float | permite calcular OAV |
| 18 | `odor_threshold_oil_ug_kg` | float | matriz grasa (queso) |
| 19 | `retention_index_polar` / `_apolar` | float | ayuda a casar datos GC |
| 20 | `is_reference_standard_only` | bool | `true` para cafeína, quinina |
| 21 | `is_family_placeholder` | bool | `true` para "Esters", "Total volatile compounds" |

Fuentes externas recomendadas para completar: **PubChem** (SMILES, InChIKey, propiedades), **The Good Scents Company**, **FlavorDB2**, **Pyrfume** (umbrales y descriptores de olor estandarizados), **Leffingwell**.

### 3.3 `dim_descriptor` — ontología armonizada de descriptores

Propuesta jerárquica de 3 niveles + tabla de alias:

| # | Columna | Tipo | Ejemplo |
|---|---|---|---|
| 1 | `descriptor_id` | str (PK) | `DS_0042` |
| 2 | `sensory_modality` | enum | `orthonasal_odor`, `retronasal_aroma`, `taste`, `trigeminal`, `texture` |
| 3 | `level1_family` | enum (≈10–12) | `lactic`, `fruity`, `floral`, `vegetal`, `roasted`, `animal`, `sulfur`, `fatty`, `spicy`, `chemical`, `earthy_fungal`, `sweet_caramel` |
| 4 | `level2_subfamily` | enum (≈30–40) | `fruity → tropical`, `fruity → citrus`, `fruity → stone_fruit` |
| 5 | `level3_descriptor` | str (≈100) | `pineapple`, `banana`, `peach` |
| 6 | `preferred_label_en` | str | `Pineapple` |
| 7 | `preferred_label_es` | str | `Piña` |
| 8 | `aliases` | tabla `descriptor_alias` | `Fruit`, `Fruity`, `Pineapple-like` |
| 9 | `is_off_flavor` | bool | `rancid`, `baby vomit` |
| 10 | `hedonic_valence` | enum | `positive`, `neutral`, `negative` |
| 11 | `is_hedonic_or_intensity_term` | bool | `General intensity`, `Character` → excluir del target |
| 12 | `reference_standard` | str | sustancia de referencia del léxico |
| 13 | `lexicon_mapping` | str | término equivalente en léxicos publicados |

Recomendaciones de armonización:
- Basar `level1/level2` en léxicos y ruedas publicados de queso (p. ej. Bérodier et al. 1997 para quesos de pasta dura; léxico de Cheddar de Drake et al. 2001; ISO 5492 para vocabulario general) y documentar la decisión.
- **Separar sinónimos reales de agrupaciones**: `Fruit / Fruity / Pineapple / Banana` → tres nodos hijos de `fruity`, no un solo descriptor. `Coconut / Peach` → dos descriptores distintos.
- Pasar los descriptores raros (`Tootsie Rolls`, `Circus`, `Nacho cheese`) a `aliases` de un nodo más general o marcarlos como referencias de léxico.
- Mover `Aged`, `General intensity`, `Body`, `Character` fuera de los targets de aroma.
- Resolver solapamientos Texture/Trigeminal asignando una sola `sensory_modality`.
- Modelar a **varios niveles**: predecir `level1` (10–12 clases, suficientes datos), luego `level2`; `level3` solo donde haya ≥ 10–20 ejemplos.

### 3.4 `dim_source` — fuentes bibliográficas

| Columna | Ejemplo |
|---|---|
| `source_id` | `CUR02` |
| `short_citation` | `Curioni 2002` |
| `doi` | |
| `source_type` | `primary_gc_o`, `primary_panel`, `primary_gc_ms`, `review`, `book_chapter` |
| `analytical_method` | `GC-O AEDA`, `GC-O CharmAnalysis`, `GC-MS SPME`, `QDA panel` |
| `is_compilation_of` | lista de `source_id` primarios que recopila (para detectar doble conteo) |
| `year` | |

### 3.5 `dim_pathway` + `bridge_compound_pathway`

Normalizar las 18 rutas de `Evidence` y las 21 de `Biochemical Pathways` en un único catálogo (`PW_LIPOLYSIS_FFA`, `PW_BCAA_EHRLICH`, `PW_MET_SULFUR`, `PW_BETA_OX_METHYLKETONE`, `PW_ESTERIFICATION`, `PW_LACTONES`, `PW_CITRATE`, `PW_PHE`, `PW_TRP`, `PW_TYR`, `PW_MAILLARD`, `PW_LIPID_OXIDATION`, `PW_FORAGE_TERPENES`, `PW_SMOKE`, `PW_MOLD_SECONDARY`…). Un compuesto puede tener varias rutas → tabla puente con columna `is_primary_route`.

### 3.6 Tablas de hechos

#### `fact_compound_odor` (propiedad del compuesto, independiente del queso)
`compound_id`, `descriptor_id`, `source_id`, `method` (GC-O, base de datos de olores), `odor_threshold`, `concentration_tested`, `evidence_level`.
→ Aquí van las ≈400 filas cuya nota dice que el olor es del compuesto y no medido en el queso.

#### `fact_cheese_compound` (el queso contiene el compuesto)
| Columna | Tipo |
|---|---|
| `obs_id` | PK |
| `cheese_id` | FK |
| `compound_id` | FK |
| `source_id` | FK |
| `sample_condition` | texto controlado (p. ej. `12_months`, `low_fat`) |
| `ripening_days` | int (la del **muestreo**, no la del tipo de queso) |
| `detected` | bool — **permite negativos** (`ND` → `false`) |
| `value_type` | enum: `concentration`, `relative_area`, `FD_factor`, `OAV`, `charm`, `odor_intensity`, `detection_frequency`, `qualitative` |
| `value` | float |
| `unit_std` | enum: `ug_kg`, `relative`, `dimensionless` |
| `value_ug_kg` | float (convertido si es concentración) |
| `oav` | float = `value_ug_kg / odor_threshold` |
| `rank_within_study` | int (permite comparar estudios con unidades relativas) |
| `location_in_source` | `Table 3, p. 7` |
| `evidence_level` | ordinal |

#### `fact_cheese_descriptor` (descriptor percibido en el queso)
`cheese_id`, `descriptor_id`, `source_id`, `method` (`panel_QDA`, `GC-O`, `review_statement`), `intensity` (escala normalizada 0–1 si existe), `present` (bool), `linked_compound_id` (opcional, si la fuente lo atribuye).

#### `fact_process_effect` (de `Process and Volatiles`)
| Columna | Comentario |
|---|---|
| `effect_id` | `AND15-P001` (ya existe, mantener) |
| `factor_category` | enum armonizado: `milk_species`, `milk_heat_treatment`, `fat_content`, `ripening_time`, `ripening_temp`, `season`, `feed`, `starter`, `adjunct`, `coagulant`, `mold`, `lipase`, `packaging`, `storage_temp`, `hpp`, `smoking`, `brine`, `light`… (hoy hay 50 variantes, p. ej. `Ripening time (fall)` debería ser `ripening_time` + `season=fall`) |
| `factor_level_treatment` | valor de la condición estudiada (numérico si se puede: `60` días, `600` MPa) |
| `factor_level_reference` | valor de la condición de referencia |
| `cheese_id`, `compound_id` (o `compound_family`) | FKs |
| `value_treatment`, `value_reference`, `unit_std` | numéricos, `ND` → `NA` + `detected=false` |
| `log2_ratio` | `log2(treatment/reference)` — **target recomendado** (simétrico, sin unidades) |
| `direction` | `up`, `down`, `no_change` (target de clasificación alternativo) |
| `source_id`, `cited_primary_source_id` | |

---

## 4. Orden y nombres de columnas para la tabla `Evidence` limpia (si se quiere mantener una sola hoja)

Si a corto plazo se prefiere una sola tabla plana, este es el orden recomendado (claves → objeto de estudio → contexto → valor → evidencia → QA):

```
 1 evidence_id              14 starter_type               27 value_type
 2 descriptor_id            15 ripening_days_min          28 value
 3 descriptor_std           16 ripening_days_max          29 unit_std
 4 descriptor_level1        17 ripening_class             30 detected (bool)
 5 descriptor_level2        18 is_smoked                  31 claim_scope  ← NUEVO
 6 compound_id              19 is_pasta_filata            32 verification_status
 7 cas                      20 curd_cooking_temp_c        33 evidence_score (0–1)
 8 iupac_name               21 other_process_flags        34 source_id
 9 chemical_class           22 pathway_id                 35 source_type
10 cheese_id                23 descriptor_in_source       36 cited_primary_source_id
11 cheese_name_std          24 evidence_text              37 is_duplicate_of
12 milk_*_frac (4 cols)     25 location_in_source         38 reviewed_by / reviewed_date
13 milk_heat_treatment      26 coagulant_source           39 notes
```

Columna nueva clave — **`claim_scope`**:
- `compound_odor` → la fuente dice que el compuesto huele así (no medido en el queso).
- `compound_in_cheese` → el compuesto se detectó en el queso (sin descriptor).
- `descriptor_in_cheese_gco` → GC-O en ese queso asoció el olor al compuesto (**el dato más fuerte**).
- `descriptor_in_cheese_panel` → panel sensorial describe el queso así.

---

## 5. Limpieza: pasos concretos, en orden de prioridad

| Prioridad | Acción | Hoja | Esfuerzo |
|---|---|---|---|
| 1 | Hacer copia y **convertir todas las fórmulas a valores** | Todas | Bajo |
| 2 | Eliminar las 36 columnas vacías y quitar espacios de encabezados; pasar a `snake_case` | Evidence, Odor & Aroma | Bajo |
| 3 | Recuperar las **369 listas truncadas con `…`** desde el archivo de origen | Evidence | Medio |
| 4 | Asignar `evidence_id` a las 80 filas sin ID y resolver las 53 `pending` y las 11 `check in the table` | Evidence | Medio |
| 5 | Construir `dim_compound`: un registro por CAS (fusionar los 46 duplicados), validar checksum CAS, completar 23 CID, añadir InChIKey/SMILES desde PubChem | Synonyms | Medio (automatizable) |
| 6 | Construir `dim_cheese`: mapear los 118 nombres a nombres canónicos + `parent_cheese_id`; mover "(12 months)", "low-fat", "smoked" a columnas | Cheese Profiles + Evidence | Alto |
| 7 | Convertir variables de producción a los enums/numéricos de §3.1 (fracción de leche, días de maduración, flags de cultivos) | Cheese Profiles | Alto |
| 8 | Construir `dim_descriptor` jerárquica; separar grupos con `/`; mapear 169 → ~100 descriptores `level3` → ~35 `level2` → ~12 `level1` | Evidence, Odor & Aroma | Alto (requiere criterio sensorial) |
| 9 | Etiquetar `claim_scope` en cada evidencia (las notas existentes permiten automatizar gran parte) | Evidence | Medio |
| 10 | Parsear `reported_value` a (`value_type`, `value`) y `ND` → `detected=false` | Evidence, Process | Medio |
| 11 | Armonizar `factor studied` (50 → ~20 categorías) y calcular `log2_ratio` | Process and Volatiles | Medio |
| 12 | Marcar doble conteo con `is_duplicate_of` y deduplicar por (queso, compuesto, descriptor, fuente primaria) | Evidence | Medio |
| 13 | Retirar cafeína/quinina de compuestos de queso (marcar como `reference_standard`) | Taste | Bajo |
| 14 | Separar Taste/Trigeminal/Texture del dataset de aroma (otra fase del proyecto) | — | Bajo |
| 15 | Pasar de Excel a CSV/Parquet versionados (o SQLite) + diccionario de datos | Todas | Bajo |

---

## 6. Recomendaciones específicas para Machine Learning

### 6.1 Definir bien la tarea
| Tarea | Entrada (X) | Salida (y) | Datos disponibles hoy |
|---|---|---|---|
| **A. Proceso → compuestos** | variables de `dim_cheese` + factor de proceso | `log2_ratio` o `direction` por compuesto/familia | 341 filas en Process (≈100 con compuesto único) |
| **B. Compuestos → descriptores** | perfil de compuestos (presencia, OAV) + descriptores químicos (SMILES/fingerprints) | descriptores multi-etiqueta (`level1`/`level2`) | ≈600 pares descriptor–CAS únicos; ampliable con Pyrfume/Good Scents |
| **C. Proceso → descriptores (directo)** | variables de `dim_cheese` | descriptores del queso multi-etiqueta | ≈73 quesos con confirmación; poco para un modelo complejo |

Con el tamaño actual, lo más realista es: **B con modelos sobre fingerprints moleculares** (transfer learning con bases de olor públicas) + **A con modelos simples interpretables** (regresión regularizada, árboles, modelos bayesianos jerárquicos) + composición A∘B para predecir aroma desde el proceso.

### 6.2 Construcción de etiquetas
- Usar **multi-etiqueta jerárquica** (un queso/compuesto puede tener varios descriptores).
- Etiquetas con **peso de confianza** (`evidence_score`), p. ej.: `CONFIRMED` primaria GC-O = 1.0; `CONFIRMED (secondary)` = 0.6; `PROBABLE` = 0.4; `NOT CONFIRMED` = no etiquetar (desconocido, no negativo); `UNSUPPORTED` = excluir.
- Convertir `evidence_level` mixto (`A/B`, `B/C`) a una escala numérica única.
- **Negativos**: crear negativos explícitos solo cuando la fuente analizó el queso y el compuesto **no se detectó** (`ND`). Lo demás debe tratarse como *positive-unlabeled* (PU learning), no como 0.

### 6.3 Evitar fugas de información (data leakage)
- Dividir train/test **por fuente primaria** y **por queso** (`GroupKFold`), nunca por fila: las filas del mismo estudio son casi copias.
- Deduplicar las filas de libros que recopilan a Curioni 2002, Moio 1998/2000, Milo 1997 antes de entrenar.

### 6.4 Desbalance
- Cheddar + Camembert = 34 % de los datos; 90 descriptores con < 5 filas.
- Usar pesos por clase, predecir a nivel `level1/level2`, agrupar quesos raros por `cheese_family`, y reportar métricas macro (macro-F1, AUPRC por etiqueta), no solo exactitud.

### 6.5 Valores faltantes
- 60 % sin maduración y 32 % sin tratamiento térmico: completar desde especificaciones PDO / literatura de la denominación (muchas son conocidas: Grana Padano ≥ 9 meses, leche cruda, cuajo de ternero, suero-injerto natural).
- Mantener indicadores `*_known` para que el modelo distinga "desconocido" de "no".

### 6.6 Features adicionales de alto valor
- **OAV** (concentración / umbral) en lugar de concentración bruta: es lo que mejor predice impacto aromático.
- Fingerprints moleculares (Morgan/ECFP), grupos funcionales, nº de carbonos, ramificación.
- Codificar las rutas bioquímicas como features del compuesto (one-hot o embeddings de grafo).
- Un **grafo de conocimiento** (queso–proceso–ruta–compuesto–descriptor) aprovecha bien un dataset pequeño y muy relacional.

---

## 7. Diccionario de datos y gobierno

- Crear una hoja/archivo `data_dictionary` con: nombre de columna, tipo, unidades, valores permitidos, descripción, ejemplo, obligatoria (sí/no).
- Validación con listas desplegables (Excel) o con esquemas (`pandera`, `Great Expectations`) si se pasa a Python.
- Versionar los datos (fecha + cambios) y registrar quién revisó cada evidencia (`reviewed_by`, `reviewed_date`) — hoy la columna `reviewed` está vacía.
- Un solo idioma (inglés) en valores controlados; traducciones solo en columnas de etiqueta (`preferred_label_es`).

---

## 8. Resultado esperado tras las mejoras

| Métrica | Hoy | Objetivo |
|---|---|---|
| Nombres de queso distintos | 118 (39 enlazados a perfil) | ~60 canónicos, 100 % enlazados |
| Descriptores | 169 sin jerarquía | ~100 `level3` / ~35 `level2` / ~12 `level1` |
| Compuestos | 215 nombres, 46 duplicados por CAS | ~190 únicos por CAS/InChIKey con propiedades |
| Variables de producción numéricas/categóricas | 0 | ~35 columnas codificadas |
| Filas con maduración conocida | 40 % | > 80 % (completando con especificaciones PDO) |
| Evidencias con alcance claro (`claim_scope`) | 0 % | 100 % |
| Negativos explícitos | 0 | todos los `ND` de las fuentes |
| Formato | Excel con fórmulas | CSV/Parquet + diccionario + validación |
