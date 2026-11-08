# Fase 5 — Modelo compuesto → familia aromática

**Script:** [`scripts/phase5_model.py`](scripts/phase5_model.py) · **Resultados:** [`results/fase5/`](results/fase5/): métricas, predicciones, gráficos y modelos entrenados (`models/*.pkl`) · **Registro de la ejecución:** `results/fase5/ejecucion.log`

## Resultado en una frase

Un **Random Forest con huellas moleculares de PubChem** predice las familias de aroma de compuestos que no vio en el entrenamiento mejor que el azar y mejor que la línea base por clase química en **fruity, vegetal, floral y animal**. En **lactic** y **toasted** no supera claramente a la línea base dentro de la base, aunque toasted sí generaliza bien a compuestos externos. Los valores son exploratorios por el tamaño de la base (144 compuestos).

## 1. Datos

| Elemento | Valor |
|---|---|
| Compuestos (con propiedades de PubChem y al menos una etiqueta de aroma) | **144**, todos con estructura distinta |
| Familias objetivo | 6: fruity, vegetal, lactic, floral, toasted, animal (Fase 3) |
| Positivos por familia | fruity 69 · vegetal 56 · toasted 29 · floral 26 · lactic 20 · animal 20 |
| Variables de entrada | 282 bits informativos de la huella Fingerprint2D de PubChem (de 881) + 8 fisicoquímicas: peso molecular, XLogP (+ indicador de dato faltante), TPSA, donantes y aceptores de H, enlaces rotables, átomos pesados |
| Fuente de etiquetas | `fact_compound_odor.csv` (pares de aroma), sin duplicados; un compuesto es positivo en una familia si algún descriptor de esa familia está registrado para él |

### Etiquetas positivas, negativas y desconocidas

- **Positivo:** la base registra la familia para el compuesto.
- **Negativo explícito:** **no existe ninguno** en la fuente. El Excel no registra que un compuesto *no* tenga un olor.
- **Desconocido:** todo lo demás. **No se convierte en negativo.** En el entrenamiento, los desconocidos se tratan como «no etiquetados» (aprendizaje positivo–no etiquetado). Por eso el AUPRC observado es una **cota inferior** del real: algunos «falsos positivos» pueden ser olores no registrados.

La tabla [`etiquetas_compuesto_familia.csv`](results/fase5/etiquetas_compuesto_familia.csv) guarda el estado de cada celda.

## 2. Diseño de la evaluación

- **Validación agrupada por estructura** (GroupKFold de 5 pliegues por esqueleto InChIKey, **10 repeticiones**): un compuesto, o sus estereoisómeros, nunca está a la vez en entrenamiento y en prueba. Así se mide la generalización a **compuestos no vistos**.
- **Umbral de decisión** para el F1, elegido con validación cruzada interna dentro del entrenamiento; nunca con el pliegue de prueba.
- **Desbalance:** pesos de clase equilibrados en la regresión logística y el Random Forest. Se reportan AUPRC por familia frente a su prevalencia y macro-F1.
- **Dependencia entre evidencias:** la unidad de análisis es el compuesto, no la evidencia, así que varias evidencias del mismo par no inflan los datos.
- **Modelos:**
  - Prevalencia (azar informado).
  - Clase química (línea base pedida): frecuencia de cada familia dentro de la clase química, con suavizado.
  - Regresión logística L2 (C = 0,05).
  - Random Forest (400 árboles, hojas mínimas de 2).
- **Prueba de permutación:** se barajan las etiquetas entre compuestos y se repite la evaluación 50 veces.
- **Sensibilidad:** solo etiquetas de mayor calidad (`max_evidence_score ≥ 0,6` y sin doble conteo).
- **Validación externa:** se entrena con toda la base y se predicen **510 compuestos de Flavornet que no están en la base** (estructuras distintas, comprobado por InChIKey). Sus etiquetas salen de los olores de Flavornet asignados a familias de Bérodier en la Fase 4.

## 3. Resultados (reales)

### Validación cruzada agrupada (10 repeticiones)

| Modelo | macro-AUPRC | macro-ROC-AUC | macro-F1 |
|---|---|---|---|
| Prevalencia | 0,22 | 0,39 | 0,39 |
| Clase química (línea base) | 0,46 ± 0,01 | 0,75 | 0,53 |
| Regresión logística | 0,54 ± 0,02 | 0,77 | 0,52 |
| **Random Forest** | **0,57 ± 0,01** | **0,78** | **0,54** |

AUPRC por familia (media ± DE de 10 repeticiones):

| Familia | Positivos | Prevalencia | Clase química | Reg. logística | Random Forest |
|---|---|---|---|---|---|
| fruity | 69 | 0,48 | 0,69 | 0,77 ± 0,02 | **0,79 ± 0,01** |
| vegetal | 56 | 0,39 | 0,51 | 0,61 ± 0,02 | **0,71 ± 0,03** |
| animal | 20 | 0,14 | 0,52 | 0,55 ± 0,03 | **0,63 ± 0,04** |
| toasted | 29 | 0,20 | 0,44 | **0,50 ± 0,03** | 0,46 ± 0,03 |
| lactic | 20 | 0,14 | 0,37 | **0,43 ± 0,05** | 0,39 ± 0,06 |
| floral | 26 | 0,18 | 0,24 | 0,37 ± 0,04 | **0,42 ± 0,05** |

![AUPRC por familia](results/fase5/auprc_por_familia.png)

**Prueba de permutación** ([`prueba_permutacion.csv`](results/fase5/prueba_permutacion.csv)): con las etiquetas barajadas, el macro-AUPRC medio es 0,27 (máximo 0,34 en 50 permutaciones), frente a 0,55 del Random Forest y 0,52 de la regresión logística. **p = 0,02**, el mínimo posible con 50 permutaciones: ninguna permutación se acercó al resultado observado.

### Validación externa con Flavornet (510 compuestos no vistos)

| Familia | Positivos externos | Prevalencia | AUPRC RF | ROC-AUC RF | ¿Generaliza? |
|---|---|---|---|---|---|
| fruity | 136 | 0,27 | 0,49 | 0,72 | Sí |
| vegetal | 192 | 0,38 | 0,49 | 0,66 | Moderadamente |
| toasted | 44 | 0,09 | **0,52** | **0,88** | Sí, claramente |
| floral | 63 | 0,12 | 0,23 | 0,70 | Débil |
| animal | 12 | 0,02 | 0,03 | 0,57 | **No** (12 positivos externos) |
| lactic | 3 | 0,01 | 0,01 | 0,57 | **No evaluable** (3 positivos) |

Además, en los 129 compuestos de la base que también están en Flavornet, las predicciones fuera de pliegue coinciden con las etiquetas de Flavornet en **fruity** (AUPRC 0,84 frente a prevalencia 0,33), **vegetal** (0,66 frente a 0,32) y **toasted** (0,65 frente a 0,21). En **lactic**, la coincidencia es débil (0,17 frente a 0,08).

### Sensibilidad (solo etiquetas de mayor calidad)

El orden de los modelos se mantiene: el Random Forest es el mejor en 5 de 6 familias. El rendimiento de toasted baja (de 0,46 a 0,37): una parte de sus etiquetas venía de evidencia de menor calidad. Ver [`sensibilidad_etiquetas_alta_calidad.csv`](results/fase5/sensibilidad_etiquetas_alta_calidad.csv).

## 4. Análisis de errores

Archivos: [`analisis_errores.csv`](results/fase5/analisis_errores.csv) y [`rendimiento_por_clase_quimica.csv`](results/fase5/rendimiento_por_clase_quimica.csv).

- **El modelo aprende sobre todo la química de cada familia:** ésteres → fruity (AUPRC 0,88 dentro de los ésteres), alcoholes → vegetal (0,94), pirazinas → toasted.
- **Posibles «falsos positivos»** (probablemente olores no registrados en la base, por el carácter positivo–no etiquetado de los datos):
  - 2,5-dimetilpirazina y 2,3,5-trimetilpirazina en **toasted**: Flavornet y la bibliografía les atribuyen notas tostadas.
  - decanal y dodecanal en **vegetal**.
  - 3-metilbutil 2-metilpropanoato en **fruity**.
- **Falsos negativos que revelan los límites del enfoque:**
  - **lactic:** ácido 3-metilbutanoico y (4Z)-hept-4-enal. Las notas lácticas o «a queso» las dan compuestos químicamente heterogéneos (ácidos, aldehídos, cetonas) y dependen de la matriz y la concentración, no solo de la estructura.
  - **animal:** heptan-2-ona y metional, que la fuente asocia a notas animales en contexto de queso.
  - **Ácidos grasos:** se predicen como animal o lactic (ácido dodecanoico 0,92 en animal) por su parecido con el ácido butanoico.

## 5. Interpretación honesta

1. **La evaluación mide generalización real a compuestos no vistos:** agrupa por estructura, elige el umbral dentro del entrenamiento, la permutación da p = 0,02 y la validación externa usa 510 compuestos nuevos.
2. **El modelo supera a la clase química en 4 de 6 familias**, con una ganancia moderada: +0,10 a +0,20 de AUPRC en fruity, vegetal, animal y floral. En **lactic** y **toasted**, la ganancia sobre la clase química es pequeña (≤ 0,06) e incierta.
3. **Lo que no se puede afirmar:**
   - que el modelo predice el aroma de un **queso**: predice la familia de olor de un **compuesto aislado**;
   - que la familia **animal** o la **lactic** se generalicen fuera de la base;
   - valores de precisión absolutos: con datos positivo–no etiquetado, el AUPRC es una cota inferior y el F1 depende del umbral.
4. **Uso recomendado:** como componente B del enfoque A → B. Primero se estiman los compuestos de un queso (con su concentración u OAV) y después este modelo les asigna familias, ponderando por OAV. Además sirve para proponer olores a compuestos sin etiqueta, siempre como hipótesis.

## 6. Limitaciones

- Son 144 compuestos y algunas familias tienen 20 positivos, por eso la varianza entre repeticiones es grande en lactic (DE 0,06).
- No hay negativos explícitos (aprendizaje positivo–no etiquetado).
- La huella Fingerprint2D de PubChem no tiene en cuenta la estereoquímica, que importa en algunos odorantes (p. ej. lactonas, carvona).
- Las etiquetas externas de Flavornet dependen de la asignación de sus términos a familias de Bérodier (Fase 4), en parte interpretativa.
- El modelo no usa la concentración ni el umbral de olor. Un compuesto con una familia correcta puede no influir en el aroma del queso si su OAV es menor que 1.

## 7. Cómo reutilizar los modelos

```python
import pickle
m = pickle.load(open("results/fase5/models/random_forest.pkl", "rb"))
# m["models"]: un clasificador por familia (m["families"]); m["keep_bits"]: bits usados;
# m["phys"], m["phys_median"], m["phys_mu"], m["phys_sd"]: preprocesado de las variables fisicoquímicas.
```
