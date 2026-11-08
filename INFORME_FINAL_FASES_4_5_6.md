# Informe final — Fases 4, 5 y 6 (QUESOS-HUC)

**Proyecto:** *Cheese Types, Production Variables and Sensory Descriptor Harmonization for Data-Driven Aroma Prediction*
**Versión de la base:** `v3-fases456`. Se conservan el Excel original, `v1-clean` y `v2-harmonized`.
**Fecha:** 2026-11-08 · **Instrucción seguida:** [`corrections/fases456.md`](corrections/fases456.md)

Documentos de detalle: [FASE4_Control_Calidad.md](FASE4_Control_Calidad.md) · [FASE5_Modelo_Compuesto_Aroma.md](FASE5_Modelo_Compuesto_Aroma.md) · [FASE6_Extraccion_Muestras.md](FASE6_Extraccion_Muestras.md)

---

## 1. Actividades ejecutadas

| Fase | Actividad | Estado |
|---|---|---|
| 4 | Verificación de las 53 evidencias pendientes y de los 138 pares por confirmar, con evidencia interna y Flavornet | Ejecutada |
| 4 | Comprobación y completado de CID y CAS con PubChem; propiedades y huellas moleculares de 199 compuestos | Ejecutada |
| 4 | Análisis de las 369 listas de referencias cortadas; enlaces exactos recalculados | Ejecutada (las listas originales no son reconstruibles) |
| 4 | Estatus de Curioni 2002, independencia de estudios y duplicados por estudio | Ejecutada |
| 4 | Contraste de los 484 pares compuesto–aroma con Flavornet | Ejecutada |
| 5 | Conjunto de entrenamiento, variables PubChem, etiquetas positivo/desconocido | Ejecutada |
| 5 | Dos líneas base, regresión logística y Random Forest; validación agrupada por estructura (10 × 5 pliegues); permutación (50); sensibilidad; validación externa (510 compuestos) | Ejecutada |
| 6 | Búsqueda de acceso a 10 estudios prioritarios y a las fuentes primarias del Excel (Europe PMC) | Ejecutada |
| 6 | Extracción de 7 estudios de acceso abierto en `sample`, `sample_compound` y `sample_descriptor` | Ejecutada |
| 6 | Reevaluación de la viabilidad de los modelos A y C con datos por muestra | Ejecutada |
| — | Integración reproducible, control de calidad (37/37 OK), diccionario de datos, auditoría y bitácora | Ejecutada |

**Scripts nuevos:**
- `scripts/fetch_external.py`: descargas en caché.
- `scripts/phase4_quality.py`: Fase 4.
- `scripts/phase5_model.py`: Fase 5.
- `scripts/article_tables.py`: tablas de artículos a CSV.
- `scripts/phase6_extract.py` y `scripts/phase6_viability.py`: Fase 6.

## 2. Registros investigados y corregidos

| Registro | Investigados | Resueltos con fuente | Por inferencia | Sin evidencia |
|---|---|---|---|---|
| Evidencias pendientes | 53 | 27 | 15 | 11 |
| Pares descriptor–compuesto por confirmar | 138 | 15 | 49 | 74 |
| Pares compuesto–aroma contrastados con Flavornet | 484 | 117 (mismo término) | 179 (misma familia) | 188 (otras notas o ausente) |
| CID (38 faltantes + 166 del Excel) | 204 | 165 confirmados + 22 completados | 11 completados por nombre (+1 conservado) | 5 |
| CAS faltantes | 16 | — | 11 completados | 5 |
| Listas de referencias de proceso cortadas | 369 | 73 con enlaces exactos | — | 296 |
| Etiquetas queso–aroma: independencia y duplicados | 974 | 31 duplicados marcados; 235 dependientes solo de una revisión | — | — |

Todas las correcciones están registradas en `clean/soporte/harmonization_log.csv`.

## 3. Fuentes científicas verificadas

- **Bases de datos:**
  - **PubChem PUG-REST** (NCBI): 1.926 respuestas en caché, en `data_external/pubchem/`.
  - **Flavornet** (Acree & Arn, Cornell University): 734 compuestos por CAS, con olores medidos por GC-O.
- **Bibliografía:**
  - **Curioni & Bosset (2002)**, Int. Dairy J. 12:959–984, DOI 10.1016/S0958-6946(02)00124-3: verificado como **revisión**.
- **Estudios con datos por muestra** (acceso abierto, texto completo y tablas):
  - Duensing et al. 2024a (10.1021/acs.jafc.4c01814) y 2024b (10.1021/acs.jafc.4c01813).
  - Santamarina-García et al. 2023 (10.1016/j.crfs.2022.100425).
  - Dopieralska et al. 2020 (10.3390/ani10112103).
  - Natrella et al. 2020 (10.3390/foods9101446).
  - Torri et al. 2021 (10.3390/foods10112791).
  - Chen et al. 2022 (10.1016/j.fochx.2022.100416).
- **Estudios prioritarios no accesibles** (de pago): Moio 1998 y 2000, Qian 2002, Milo 1997, Boscaini 2003, Suriyaphan 2001, Christensen 1995, Arora 1995, Larráyoz 2002 y Jo 2018. De ellos solo se verificó la cita y el resumen; **no se extrajo ningún dato**.

Las URL, la fecha de consulta y la ubicación de cada dato están en `data_external/meta.json`, en los documentos de cada fase y en la columna `source_location`.

## 4. Resultados reales del entrenamiento (Fase 5)

Validación agrupada por estructura, 5 pliegues × 10 repeticiones, sobre 144 compuestos:

| Modelo | macro-AUPRC | macro-ROC-AUC | macro-F1 |
|---|---|---|---|
| Prevalencia | 0,22 | 0,39 | 0,39 |
| Clase química (línea base) | 0,46 | 0,75 | 0,53 |
| Regresión logística L2 | 0,54 | 0,77 | 0,52 |
| **Random Forest** | **0,57** | **0,78** | **0,54** |

- **Por familia (RF frente a clase química):** fruity 0,79 frente a 0,69 · vegetal 0,71 frente a 0,51 · animal 0,63 frente a 0,52 · floral 0,42 frente a 0,24 · toasted 0,46 frente a 0,44 · lactic 0,39 frente a 0,37.
- **Prueba de permutación:** p = 0,02 (con etiquetas barajadas, macro-AUPRC 0,27 ± 0,02).
- **Validación externa** (510 compuestos de Flavornet no vistos):
  - generaliza en **toasted** (AUPRC 0,52 frente a prevalencia 0,09; ROC 0,88) y **fruity** (0,49 frente a 0,27);
  - débil en floral y vegetal;
  - **no generaliza** en animal ni lactic (12 y 3 positivos externos).

Los modelos entrenados, las predicciones y los gráficos están en `results/fase5/`.

## 5. Métricas y limitaciones

- **AUPRC como cota inferior:** no existen negativos explícitos. Los datos son positivo–no etiquetado, así que algunos «falsos positivos» son probablemente olores no registrados (p. ej. las pirazinas en toasted).
- **Base pequeña:** 144 compuestos, con 20 positivos en lactic y animal. La varianza es grande en esas familias.
- **Alcance del modelo:** predice el olor de **compuestos aislados**, no el aroma de un queso. No usa la concentración ni el OAV.
- **Mejora acotada sobre la clase química:** es moderada en 4 familias e incierta en lactic y toasted.
- **Fase 6:** la mayoría de los estudios prioritarios son de pago. Los 7 estudios extraídos usan unidades y métodos de aroma distintos.
- **Sin validación interjueces:** las asignaciones de los términos de Flavornet y de los descriptores de las muestras a familias de Bérodier no se revisaron por un segundo evaluador (como en la Fase 3).

## 6. Nuevas muestras experimentales recuperadas (Fase 6)

| Indicador | Valor |
|---|---|
| Estudios | 7 |
| Muestras | 64 |
| Unidades de producción independientes | 30 |
| Muestras con producción y compuestos | 58 |
| Muestras con producción y descriptores de aroma | 20 (3 estudios) |
| Mediciones de compuestos / no detecciones explícitas | 2.192 / 341 |
| Registros de descriptores de aroma | 425 |
| Variables de producción que cambian dentro de un estudio | tratamiento térmico (DUE24A/B), días de maduración (DUE24A, IDI23, TOR21), almacenamiento (DOP20, NAT20), conservante (NAT20), estilo y proceso (TOR21), categoría de maduración (CHE22) |
| Variables que más faltan | especie de leche (54 de 64), tratamiento (38), coagulante y cultivo (38), días de maduración (36) |

## 7. Comparación con la base anterior

| Indicador | v2-harmonized | v3-fases456 |
|---|---|---|
| Etiquetas queso–aroma (recomendadas) | 974 | 943 sin duplicados por estudio |
| Estudios primarios independientes (todas / fuertes) | 44 / 20, con Curioni contado como primario | 42 / 19, con Curioni como revisión; el mayor peso pasa del 30 % (Curioni) al 9,5 % (Moio 2000) |
| Pares compuesto–aroma con contraste externo | 0 | 484 (61 % coinciden con Flavornet al menos en la familia) |
| Compuestos sin CID / sin CAS | 38 / 16 | 5 / 5 |
| Compuestos con estructura (SMILES) y huella molecular | 0 | 199 |
| Evidencias pendientes / pares por confirmar resueltos | 0 / 0 | 42 de 53 / 64 de 138 (con fuente o inferencia) |
| Datos por muestra | 0 | 64 muestras de 7 estudios |
| Modelo compuesto → familia | no entrenado | entrenado y validado (macro-AUPRC 0,57) |
| Comprobaciones de calidad | 30 | 37, todas OK |

## 8. Viabilidad actualizada de los modelos A, B y C

| Modelo | Viabilidad | Fundamento |
|---|---|---|
| **A — producción → compuestos** | **Parcial: direcciones sí, concentraciones no** | La maduración cambia en la misma dirección 14 de 16 compuestos medidos en ≥ 2 series de dos tipos de queso. La pasteurización tiene efectos consistentes en 8 de 8 pares (cruda → más ácidos grasos libres y ésteres etílicos; pasteurizada → más diacetilo y compuestos de Strecker). Solo 3 estudios tienen series con compuestos, y en unidades incompatibles. |
| **B — compuesto → familia** | **Viable con limitaciones** | Supera a la clase química y al azar con validación agrupada, y generaliza a compuestos externos en fruity y toasted. No es fiable en lactic ni animal. |
| **C — producción → aroma directo** | **No viable todavía** | 20 muestras con producción y aroma, de 3 estudios con 3 métodos de aroma distintos. Dentro de cada estudio hay efectos coherentes (Gouda madurado → más notas animales y afrutadas por GC-O; Gorgonzola más madurado → más «moldy» y «ammonia»), pero no hay datos para un modelo supervisado. |

## 9. Recomendación para las Fases 7 y 8

**Fase 7 — producción → compuestos (modelo A): direcciones, no concentraciones.**

1. Modelar el **signo y la magnitud relativa** del cambio, no valores absolutos. Por ejemplo, log2 del cambio frente a la primera muestra, o rangos dentro de cada estudio. Así se pueden combinar estudios con unidades distintas.
2. Ajustar un **modelo jerárquico** (efectos aleatorios por estudio) con 2 factores bien representados, maduración y tratamiento térmico. Se puede usar `fact_process_effect.csv` (log2_ratio) junto con `sample_compound.csv`.
3. **Requisito previo:** conseguir el texto completo de Jo et al. 2018, Qian & Reineccius 2002 y Moio et al. 1998/2000. Por ejemplo, mediante la biblioteca universitaria; los PDF se pueden poner en `data_external/articles/` y el script los procesa. **Es la acción con más impacto**: Jo 2018 aporta 36 Gouda de edad conocida con panel descriptivo.

**Fase 8 — integración A → B, frente a C:**

1. **Vía indirecta:** perfil de compuestos de la muestra (concentración × 1/umbral = OAV) × probabilidad de familia del modelo B = **perfil de familias esperado**. Validarlo **solo** en las 20 muestras con aroma medido. Por ejemplo, comprobar si predice que los Gouda madurados (CHE22) tienen más notas animales y afrutadas, y que la leche cruda (DUE24B) da más notas afrutadas por los ésteres.
2. **Requisito:** completar los **umbrales de olor** de los compuestos (fuente bibliográfica, uno por compuesto) para pasar de presencia a OAV.
3. **Modelo C directo:** posponerlo hasta tener al menos unas 50 unidades de producción independientes con un mismo método de aroma (orden de magnitud orientativo; ver el plan). Con los datos accesibles hoy (20 muestras, 3 métodos) **no es recomendable**.
4. **Validación:** dejar fuera un estudio cada vez y reportar los resultados por familia, separando las familias fiables (fruity, vegetal, toasted) de las no fiables (lactic, animal).

**Conclusión:** el proyecto puede presentar ahora una base armonizada y depurada, un modelo compuesto → familia validado con prueba de permutación y validación externa, y evidencia por muestra de que la maduración y la pasteurización tienen efectos químicos coherentes. La predicción del aroma a partir de la producción depende sobre todo de **acceder a más estudios primarios con datos por muestra**.
