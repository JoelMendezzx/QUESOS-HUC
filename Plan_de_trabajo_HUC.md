# Plan de trabajo — Cheese Types, Production Variables and Sensory Descriptor Harmonization for Data-Driven Aroma Prediction

**Punto de partida:** base limpia en [`clean/`](clean/) y [Auditoría de viabilidad](Auditoria_viabilidad_predictiva.md)
**Fecha:** 2026-11-08

---

## 0. Cómo leer el título del proyecto con los datos actuales

El título tiene dos partes, y la auditoría muestra que hoy están en situaciones distintas:

| Parte del título | Estado con la base actual | Qué se puede afirmar al final |
|---|---|---|
| **Harmonization** de tipos de queso, variables de producción y descriptores | **Alcanzable ya.** Es trabajo de curación sobre datos que existen. | Una base armonizada, documentada y reutilizable. Es un resultado publicable por sí mismo. |
| **Data-driven aroma prediction** | **Parcial.** Compuesto → familia aromática es viable; producción → aroma no (solo 9 combinaciones de producción). | Un modelo compuesto → familia validado y una prueba de concepto producción → compuestos → aroma. El modelo directo requiere datos por muestra (Fase 6). |

Por eso el plan va en este orden: **primero armonizar (Fases 1–4), después predecir con lo que alcanza (Fase 5), luego ampliar los datos (Fase 6) y por último integrar (Fases 7–8).**

```
 FASE 1        FASE 2          FASE 3           FASE 4
 Quesos   ──►  Producción ──►  Descriptores ──►  Pendientes QA
    └──────────────┴───────────────┴──────────────────┘
                          │  base armonizada v2
                          ▼
 FASE 5  Modelo B: compuesto → familia aromática   (viable hoy)
                          │
 FASE 6  Extracción por MUESTRA de estudios primarios   ◄── decisión clave
                          │
 FASE 7  Modelo A: producción → compuestos
                          │
 FASE 8  Integración A → B  vs  modelo directo C
                          │
 FASE 9  Publicación de la base y de los modelos
```

---

## Reglas para todo el proyecto

1. **Cada dato nuevo lleva su fuente** (columna `*_source`): ningún valor sin cita.
2. **Las propuestas automáticas se marcan como propuesta** hasta que una persona las revisa (`reviewed_by`, `reviewed_date`).
3. **El Excel original no se toca.** Los cambios van en tablas de corrección (`corrections/*.csv`) que lee el script, para que todo se pueda regenerar.
4. **Control de versiones:** inicializar git en la carpeta y etiquetar cada versión de la base (`v1-clean`, `v2-harmonized`…).

---

## FASE 1 — Armonización de tipos de queso

**Objetivo:** que cada queso tenga un nombre canónico, un tipo y una clasificación tecnológica con fuente.

| Paso | Tarea | Archivo de trabajo | Quién |
|---|---|---|---|
| 1.1 | Revisar las 282 equivalencias nombre original → queso canónico | `soporte/cheese_alias.csv` | Experto (yo puedo preparar la vista) |
| 1.2 | Resolver los 11 casos `check in the table` y "European" consultando los PDF | `soporte/qa_issues.csv` | Experto |
| 1.3 | Decidir si separar las 22 etiquetas con varios quesos ("Parmesan, Grana Padano") según lo que diga cada estudio | `soporte/dim_cheese.csv` (`label_type = multi_cheese`) | Experto |
| 1.4 | Añadir **familia tecnológica** a cada queso concreto (fresco, pasta filata, salmuera, corteza enmohecida, corteza lavada, azul, semiduro, duro cocido, grana, ojos/suizo, láctico de cabra), con fuente | nueva columna `cheese_family` + `cheese_family_source` | Experto; yo puedo proponer las obvias |
| 1.5 | Añadir país y DOP/IGP cuando el pliego de condiciones lo indique | `country`, `pdo_pgi` + fuente | Script + revisión |

**Terminado cuando:** el 100 % de los alias está revisado, no queda ningún queso `unresolved` y cada queso concreto tiene `cheese_family` con fuente.

**Por qué importa:** con solo 40 quesos con etiqueta, la **familia tecnológica** es la variable que permite agrupar quesos poco representados y que el modelo generalice.

---

## FASE 2 — Armonización de variables de producción

**Objetivo:** completar los 4 bloques básicos (leche, tratamiento térmico, cuajo/cultivo, maduración) en los quesos que tienen etiquetas de aroma.

| Paso | Tarea | Detalle |
|---|---|---|
| 2.1 | Lista de prioridad | Los 40 quesos con etiqueta (auditoría §2), ordenados por número de etiquetas fuertes. Hoy solo 13 tienen los 4 bloques. |
| 2.2 | Completar desde pliegos de condiciones DOP y literatura | En especial **maduración** (falta en 27 de 50 perfiles) y **tratamiento térmico** (19 sin ambigüedad). |
| 2.3 | Registrar cada valor con su fuente | Tabla `corrections/production_values.csv`: `cheese_id, variable, value, source, page, reviewed_by` |
| 2.4 | Distinguir "valor típico del tipo de queso" de "valor de la muestra" | Columna `value_scope = type_specification \| sample` (prepara la Fase 6) |
| 2.5 | Revisar los indicadores de cultivo propuestos por el script | Los 25 indicadores `coag_*`, `cult_*`, `mold_*`, `flora_*` en `dim_cheese` |

**Terminado cuando:** al menos 30 de los 40 quesos con etiqueta tienen los 4 bloques con fuente.

**Límite a tener presente:** esto mejora la descripción de los tipos de queso, **pero no crea variabilidad dentro de un mismo tipo**. Todas las filas de Grana Padano seguirán teniendo la misma producción. Eso solo se resuelve en la Fase 6.

---

## FASE 3 — Armonización de descriptores sensoriales (núcleo del proyecto)

**Objetivo:** convertir los 169 descriptores de aroma en una ontología jerárquica con referencia a un léxico publicado.

| Paso | Tarea | Detalle |
|---|---|---|
| 3.1 | **Elegir el léxico de referencia** | Por ejemplo, rueda de aromas de quesos de pasta dura (Bérodier et al., 1997) o léxico de Cheddar (Drake et al., 2001). Documentar la elección. |
| 3.2 | Generar la plantilla de mapeo | `corrections/descriptor_mapping.csv`: `descriptor_id, label, terms, families_in_source, level1, level2, level3, lexicon_term, is_aroma (sí/no), notes, reviewer_1, reviewer_2`. Puedo generarla con propuestas marcadas como tales. |
| 3.3 | Separar los descriptores agrupados | 62 descriptores unen varios términos con "/" (p. ej. `Coconut / Peach`). Separar cuando no son sinónimos. |
| 3.4 | Decidir fusiones de familias | Fruit/Fruity, Toasted/Vegetable cruzados, etc. (auditoría §4). |
| 3.5 | Excluir del objetivo lo que no es aroma | General, Body, Character, General intensity, Aged; marcar `is_aroma = no`. |
| 3.6 | **Doble revisión independiente** | Dos personas mapean por separado y se mide el acuerdo (kappa de Cohen). Objetivo: κ ≥ 0,7. Los desacuerdos se resuelven en una reunión. |
| 3.7 | Fijar las clases de predicción | Partir de las 8 familias con respaldo (Fruity, Lactic, Floral, Toasted, Vegetable, Green, Animal, Chemical) y ajustar tras las fusiones. |

**Terminado cuando:** el 100 % de los descriptores de aroma tiene nivel 1 y nivel 2 revisados, hay un acuerdo κ documentado y la lista de clases de predicción está cerrada.

**Por qué es el núcleo:** es lo que hace comparable la evidencia entre estudios, y la doble revisión con kappa le da rigor metodológico para publicar.

---

## FASE 4 — Cerrar pendientes de calidad que afectan al modelo

Solo los que tocan etiquetas útiles; el resto puede esperar.

| Paso | Pendiente | Cantidad | Acción |
|---|---|---|---|
| 4.1 | Listas de referencias cortadas con "…" | 369 | Recuperar del archivo de origen o regenerar desde los IDs de proceso |
| 4.2 | Evidencias `pending` | 53 | Revisar en el PDF |
| 4.3 | Pares por confirmar (Articles to Confirm) | 138 | Priorizar los de las 8 familias objetivo |
| 4.4 | Compuestos sin CAS / sin CID | 16 / 38 | Completar desde PubChem, con fuente |
| 4.5 | Significado de `evidence_level` (S, B, C) | — | Pedir o documentar la leyenda |
| 4.6 | Estatus de Curioni 2002 (¿primario o revisión?) | 30 % de las etiquetas | Decidirlo: cambia el conteo de estudios independientes |

**Terminado cuando:** `qa_issues.csv` no tiene pendientes en filas que se usan como etiqueta.

**Entregable de las Fases 1–4:** base **v2 armonizada**, regenerable con el script y con diccionario de datos. Es el primer resultado publicable (ver Fase 9).

---

## FASE 5 — Modelo B: compuesto → familia aromática (viable con la base actual)

**Objetivo:** predecir a qué familias huele un compuesto volátil del queso.

| Paso | Tarea | Detalle |
|---|---|---|
| 5.1 | Construir el dataset | `modelo/fact_compound_odor.csv` (488 pares, 144 compuestos) → mapear descriptores a familias de la Fase 3 → una fila por compuesto con varias etiquetas (multi-label) |
| 5.2 | Variables de entrada del compuesto | Ya existentes: `chemical_class`, ruta bioquímica. A añadir desde PubChem con fuente: estructura (SMILES), peso molecular, logP y huella molecular (fingerprint) |
| 5.3 | Línea base | Predecir solo con `chemical_class`. Si el modelo no supera esta línea base, no aporta. |
| 5.4 | Modelos | Simples e interpretables primero: regresión logística y random forest. Con 144 compuestos, nada más complejo. |
| 5.5 | Validación | Separar **por compuesto** (un compuesto nunca en entrenamiento y prueba a la vez). Métricas: F1 macro y AUPRC por familia. |
| 5.6 | Pesos de evidencia | Probar con y sin `evidence_score`, y con y sin filas de doble conteo. |
| 5.7 | (Opcional) Datos externos | Bases públicas de olores (Pyrfume, Good Scents) **en un conjunto separado**, para ver si mejoran el modelo sin mezclar con la evidencia de queso. |

**Terminado cuando:** hay un modelo que supera la línea base con validación por compuesto, y un informe de qué familias se predicen bien y cuáles no.

---

## FASE 6 — Extracción de datos por muestra (decisión clave del proyecto)

**Por qué:** la auditoría muestra que producción → aroma tiene solo **9 combinaciones distintas** de producción. El dato que falta (cada muestra con su propia maduración, leche, cultivo y resultado sensorial) **está en los estudios primarios ya citados**, pero el Excel lo resumió por tipo de queso.

| Paso | Tarea | Detalle |
|---|---|---|
| 6.1 | Diseñar la plantilla de muestra | Tabla `sample`: `sample_id, study_id, cheese_id, maduración (días), leche, tratamiento, cuajo, cultivos, grasa, método analítico` |
| 6.2 | Tabla de mediciones | `sample_compound`: `sample_id, compound_id, valor, unidad, detected (incluye ND)` |
| 6.3 | Tabla sensorial | `sample_descriptor`: `sample_id, descriptor_id, intensidad o presencia, método (GC-O, panel)`, **incluyendo lo buscado y no encontrado** |
| 6.4 | Piloto con 2 estudios | Por ejemplo Moio 2000 y Qian 2002: comprobar que la plantilla captura todo antes de escalar |
| 6.5 | Extraer los 10 estudios prioritarios | Moio 1998, Moio 2000, Qian 2002, Milo 1997, Boscaini 2003, Chen 2022, Suriyaphan 2001, Christensen 1995, Arora 1995, Larrayoz 2002 |
| 6.6 | Ampliar con estudios de proceso | Los de `fact_process_effect` con compuesto concreto (Poveda 2000, Drake 2010, Kondyli 2002) |

**Punto de decisión al terminar la Fase 6:**
- **Si hay ≥ 50–100 muestras de ≥ 10 estudios** con producción y aroma propios → seguir con el modelo directo en la Fase 8.
- **Si no** → el proyecto se centra en la armonización (Fases 1–4), el modelo B y la vía indirecta A → B. El modelo directo queda como trabajo futuro, con la plantilla de muestra ya diseñada.

(El umbral de 50–100 es una regla práctica para modelos simples con unas 10–15 variables, no un valor exacto.)

---

## FASE 7 — Modelo A: producción → compuestos

| Paso | Tarea | Detalle |
|---|---|---|
| 7.1 | Datos | `modelo/fact_process_effect.csv` (`log2_ratio`, `direction`) + mediciones por muestra de la Fase 6 |
| 7.2 | Objetivo | Empezar por **familias químicas** (ésteres, ácidos, metilcetonas…), que es donde hay datos; compuestos individuales solo si hay suficientes |
| 7.3 | Modelos | Regresión con regularización o modelos jerárquicos por estudio. Interpretables: el objetivo es entender qué factor mueve qué compuesto. |
| 7.4 | Validación | Dejando fuera un estudio cada vez (*leave-one-study-out*) |
| 7.5 | Contraste con la bioquímica | Comprobar que los efectos encontrados son coherentes con las rutas de `soporte/pathway_steps.csv` (p. ej. más maduración → más ácidos grasos libres y metilcetonas) |

---

## FASE 8 — Integración y predicción de aroma

| Paso | Tarea |
|---|---|
| 8.1 | **Vía indirecta (A → B):** producción → compuestos esperados (A) → familias aromáticas de esos compuestos (B) |
| 8.2 | **Vía directa (C):** producción → familias aromáticas, solo si la Fase 6 alcanzó el umbral |
| 8.3 | Comparar ambas con validación por estudio, y con una línea base que prediga las familias más frecuentes del tipo de queso |
| 8.4 | Análisis de sensibilidad: repetir sin Curioni 2002, Moio 1998 y Moio 2000 (50 % de las etiquetas actuales) |
| 8.5 | Interpretación: qué variables de producción empujan cada familia aromática y si coincide con la literatura |

**Terminado cuando:** hay una comparación honesta entre vías, con validación por estudio y análisis de sensibilidad.

---

## FASE 9 — Publicación

| Entregable | Contenido |
|---|---|
| **Base armonizada** (data paper) | Tablas CSV v2, diccionario de datos, ontología de descriptores con κ, script de regeneración. Depósito con DOI (p. ej. Zenodo). |
| **Artículo de modelos** | Modelo B; modelo A y la integración si la Fase 6 lo permite; limitaciones (concentración de la evidencia, ausencia de negativos). |
| **Código** | `scripts/` con instrucciones para reproducir todas las cifras. |

---

## Resumen: qué se puede automatizar y qué requiere experto

| Puedo hacerlo yo (script) | Requiere criterio experto |
|---|---|
| Plantillas de mapeo prellenadas (quesos, descriptores, producción) | Validar equivalencias de quesos y familias tecnológicas |
| Completar CID, SMILES y propiedades desde PubChem, con fuente | Elegir el léxico de referencia y mapear descriptores |
| Leer las tablas de corrección y regenerar la base | Doble revisión y cálculo del kappa |
| Calcular el kappa entre revisores | Resolver casos en los PDF (`check in the table`, `pending`) |
| Modelos, validación y análisis de sensibilidad | Extraer datos por muestra de los estudios primarios |
| Repetir la auditoría tras cada fase | Interpretar los resultados frente a la bioquímica del queso |

## Siguiente paso inmediato

1. Inicializar git y etiquetar la versión actual (`v1-clean`).
2. Generar las **plantillas de corrección** (`corrections/`) para las Fases 1–3, con propuestas automáticas marcadas como propuesta.
3. Elegir el léxico de referencia de descriptores (Fase 3.1): es la decisión que más condiciona el resto.
