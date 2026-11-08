# Informe final — Fases 1, 2 y 3 (QUESOS-HUC)

**Proyecto:** *Cheese Types, Production Variables and Sensory Descriptor Harmonization for Data-Driven Aroma Prediction*
**Versión de la base:** `v2-harmonized` (la anterior, `v1-clean`, se conserva en git)
**Fecha:** 2026-11-08

---

## 1. Resumen

Las tres fases de armonización están **ejecutadas e integradas** en la base. Cada uno de los 683 registros previstos en el plan (282 + 72 + 160 + 169) tiene una decisión con estado, fuente y criterio. La base v2 se regenera con un solo script y pasa **30 comprobaciones de calidad**.

| Fase | Qué se armonizó | Documento |
|---|---|---|
| 1 | Nombres y tipos de queso; clasificación tecnológica; país y DOP/IGP | [FASE1_Armonizacion_Quesos.md](FASE1_Armonizacion_Quesos.md) |
| 2 | Leche, tratamiento térmico, cuajo/cultivos y maduración del tipo de queso | [FASE2_Armonizacion_Produccion.md](FASE2_Armonizacion_Produccion.md) |
| 3 | Ontología de descriptores de aroma en 3 niveles (Bérodier 1997 + Drake 2001) | [FASE3_Armonizacion_Descriptores.md](FASE3_Armonizacion_Descriptores.md) |
| — | Fuentes, URL y ubicación de cada dato | [REFERENCIAS_VERIFICADAS.md](REFERENCIAS_VERIFICADAS.md) |

## 2. Registros revisados

| Registro | Revisados | Cambian respecto a v1 | `verificado_con_fuente` | `inferencia_documentada` | `no_verificado` |
|---|---|---|---|---|---|
| Equivalencias de nombres de queso | 282 | 11 | 107 | 174 | 1 |
| Evidencias «check in the table» | 11 | 8 resueltas | 0 | 8 | 3 |
| Relaciones padre → variante | 6 | 1 nueva (Grana Trentino) | 1 | 5 | 0 |
| Familia tecnológica | 72 | 72 (nueva) | 20 | 45 | 7 |
| País / DOP-IGP | 72 | 72 (nuevo) | 32 | 18 | 22 |
| Valores de producción | 160 | 53 | 96 | 20 | 44 |
| Descriptores de aroma | 169 | 169 (nuevos niveles) | 61 | 108 | 0 |
| **Total** | **772** | | **317** | **378** | **77** |

(Los registros pedidos en el plan son 683: 282 + 72 + 160 + 169. Además se evaluaron las 11 evidencias «check in the table», las 6 relaciones padre → variante y el país y la DOP de los 72 quesos, por lo que el total de decisiones es 772.)

**Cómo leer los estados:**
- `verificado_con_fuente`: la fuente lo dice directamente o el término coincide literalmente con el léxico. Incluye 62 valores de producción que ya estaban en el Excel con su cita, conservados sin volver a consultar la obra (`origen_evidencia = fuente_citada_en_excel`).
- `inferencia_documentada`: se deduce de una fuente o de un criterio explícito, que queda escrito.
- `no_verificado`: no hay evidencia suficiente; el motivo queda escrito y **no se rellenó ningún valor**.

## 3. Metodología

### Procedimiento automatizado (transparencia)

La revisión la hizo un **asistente de IA (Claude)** a petición de la responsable del proyecto, que no contaba con revisores humanos. El procedimiento fue:

1. **Investigación documental:** búsquedas web dirigidas a pliegos DOP/IGP, normas (21 CFR, legislación brasileña), fichas de consorcios y léxicos sensoriales. El protocolo del ITA (rueda de Bérodier), el léxico de Drake y la lista de quesos protegidos de la UE se leyeron completos. Del resto se usaron los extractos de búsqueda con su URL.
2. **Decisión por registro:** valor, estado, fuente y criterio, registrados en [`scripts/harmonization_decisions.py`](scripts/harmonization_decisions.py).
3. **Integración reproducible:** [`scripts/build_clean_db.py`](scripts/build_clean_db.py) aplica las decisiones sobre el Excel original (que no se modifica). Escribe los registros completados en `corrections/*.xlsx`, el registro de cambios `clean/soporte/harmonization_log.csv` (116 cambios) y las comprobaciones `clean/soporte/qa_checks_v2.csv`.
4. **Reglas de no invención:** ningún dato sin fuente. Cuando las fuentes discrepan se registra `no_verificado`, salvo que una sea oficial. No se citan páginas ni DOI que no se hayan visto.

### Decisiones metodológicas principales

1. **Léxico principal: Bérodier et al. (1997)**, verificado en sus tres niveles. **Drake et al. (2001)** se usa para equivalencias. Las subfamilias que no son de Bérodier llevan la marca `[proyecto]`.
2. **Una categoría tecnológica añadida (`hard_pressed`)** a las 13 aprobadas, porque los pliegos describen como «pasta prensada» quesos que no encajaban (Cheddar, Manchego, Idiazabal…). Las características adicionales van en `secondary_technology`.
3. **El tipo de queso y la muestra se separan.** Los valores de pliego van en columnas `spec_*`; las condiciones de cada evidencia (`ctx_*`) no se tocan. Nunca se atribuye a una muestra un valor que solo describe el tipo de queso.
4. **Se separan los genéricos de los quesos concretos** (Pecorino, Chèvre, Fresco). Las etiquetas con varios quesos no se separan sin evidencia.
5. **Se fusionan duplicados de una misma evidencia** cuando dos etiquetas originales apuntan al mismo queso. Así no se cuenta dos veces la misma evidencia.

## 4. Comprobaciones de consistencia (30/30 OK)

- Sin pérdida de registros: 1.836 evidencias y 341 mediciones de proceso, igual que en el Excel.
- Claves únicas en las 7 tablas principales y nombres de queso únicos.
- Integridad referencial en 9 relaciones (queso, descriptor, compuesto, fuente, queso padre): 0 referencias rotas.
- Sin duplicados evidencia × queso en la tabla plana (se corrigieron 14 que aparecieron al unificar nombres).
- Todos los registros de las Fases 1–3 tienen estado.
- Todos los términos de Drake pertenecen al léxico verificado, y todas las familias de nivel 1 a Bérodier.

Detalle: [`clean/soporte/qa_checks_v2.csv`](clean/soporte/qa_checks_v2.csv).

## 5. Resultados de la auditoría con la base v2

| Indicador | v1 | v2 |
|---|---|---|
| Quesos concretos con los 4 bloques de producción | 12 | **20** |
| Combinaciones de producción con etiquetas de aroma (todas / fuertes) | 8 / 5 | **15 / 11** |
| Familias de aroma candidatas para ML | 8 (sin armonizar) | **6 de Bérodier**: fruity, vegetal, lactic, floral, toasted, animal |
| Pares compuesto → familia | — | **284** (144 compuestos) |

## 6. Limitaciones científicas

1. **No hay validación interjueces.** No hubo dos revisores humanos independientes, así que no se calculó un kappa de Cohen. Las 378 inferencias deberían revisarse por un experto, al menos por muestreo, antes de publicar.
2. **Fuentes leídas en extracto.** La mayoría de los pliegos se consultaron mediante extractos de búsqueda, no completos. Algunos tienen modificaciones recientes cuyo texto vigente no se confirmó (Pecorino Romano 2024, Formaggio di Fossa 2025, Manchego 2025).
3. **Bérodier a través de una reproducción.** La guía original de 1997 no se consultó directamente. Además, la rueda está pensada para quesos de pasta dura y semidura.
4. **Producción del tipo, no de la muestra.** Para varios quesos (Farmhouse Cheddar, Camembert, Gruyère, Emmental, Mozzarella de búfala) no se sabe si las muestras de los estudios son la variante DOP/AOP cuyo pliego se usó.
5. **La familia «other/autres» es heterogénea.** Mezcla notas químicamente distintas y no sirve como clase única.
6. **La armonización no crea datos nuevos.** Persisten la concentración de la evidencia (el 30 % de las etiquetas depende de Curioni 2002), la falta de negativos y el número limitado de estudios primarios (20 en el nivel fuerte).

## 7. Estado real de preparación para las siguientes fases

| Fase siguiente | Estado | Comentario |
|---|---|---|
| **4 — Pendientes de calidad** | Parcial | Siguen sin recuperar las 369 listas cortadas y sin revisar las 53 evidencias `pending` y los 138 pares por confirmar. Los compuestos sin CAS o sin CID no se tocaron en estas fases. |
| **5 — Modelo compuesto → familia** | **Listo para empezar** | Dataset: `clean/modelo/fact_compound_odor.csv` filtrando `is_aroma_target`, con 6 familias objetivo. Falta añadir las propiedades químicas (SMILES, etc.) desde PubChem. |
| **6 — Extracción por muestra** | No iniciada | Imprescindible para el modelo producción → aroma directo |
| **7–8 — Producción → compuestos y modelo integrado** | Exploratorio | Con los datos actuales, solo como prueba de concepto |
| **9 — Publicación de la base armonizada** | Casi lista | Base, diccionario, ontología y referencias completos. Falta la validación de un segundo experto. |

## 8. Archivos producidos o actualizados

- **Registros completados:** `corrections/fase1_quesos_equivalencias.xlsx`, `corrections/fase1_quesos_familia_tecnologica.xlsx`, `corrections/fase2_produccion_valores.xlsx`, `corrections/fase3_descriptores_mapeo.xlsx`.
- **Base regenerada:** `clean/modelo/*` y `clean/soporte/*`, con nuevas columnas `aroma_family`, `berodier_subfamily`, `cheese_family`, `spec_*`, `use_as_*_aroma_label`; además, `harmonization_log.csv` y `qa_checks_v2.csv`.
- **Diccionario de datos:** `clean/modelo/data_dictionary.csv`, con todas las columnas descritas.
- **Auditoría:** `clean/auditoria/*` y `Auditoria_viabilidad_predictiva.md`, con una sección v2.
- **Documentación:** los cinco documentos de este cierre y la [BITACORA.md](BITACORA.md).
