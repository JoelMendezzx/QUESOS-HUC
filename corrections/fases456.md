# Continuación del proyecto QUESOS-HUC — Ejecución completa de las Fases 4, 5 y 6

Quiero que continúes el proyecto **“Cheese Types, Production Variables and Sensory Descriptor Harmonization for Data-Driven Aroma Prediction”**, partiendo de la base `v2-harmonized`.

Las Fases 1, 2 y 3 ya fueron ejecutadas. No quiero que vuelvas a comenzar la armonización ni que repitas innecesariamente el trabajo anterior.

**Tu responsabilidad es investigar, revisar, resolver, implementar, ejecutar y documentar las Fases 4, 5 y 6 de manera autónoma.**

No quiero únicamente recomendaciones, propuestas, scripts sin ejecutar ni listas de tareas para que yo las realice.

## REGLAS GENERALES

1. Realiza directamente todas las actividades que puedas completar con los archivos, herramientas y fuentes disponibles.
2. Busca bibliografía científica adicional cuando sea necesario. Prioriza estudios primarios, documentos oficiales y bases científicas reconocidas.
3. No inventes datos, resultados experimentales, fuentes, DOI, páginas, concentraciones, descriptores ni condiciones de fabricación.
4. Verifica que cada fuente respalde específicamente la afirmación que se registra.
5. No me asignes tareas de comprobación, clasificación, extracción o revisión que puedas realizar por tu cuenta.
6. No detengas todo el proceso porque algunos registros sean imposibles de verificar. Continúa con los datos respaldados y documenta los casos restantes.
7. Conserva el Excel original, `v1-clean` y `v2-harmonized`. Implementa las mejoras de forma reproducible y versionada.
8. Documenta las decisiones en archivos Markdown, indicando metodología, fuentes, resultados y limitaciones.
9. No presentes inferencias como mediciones experimentales ni resultados simulados como resultados reales.
10. No declares una fase terminada sin haber ejecutado y comprobado sus entregables.

---

## FASE 4 — Resolver los problemas pendientes de calidad

Revisa `clean/soporte/qa_issues.csv`, `qa_pending_confirmation.csv`, `fact_evidence.csv` y las demás tablas necesarias.

### Actividades

- Investiga las 53 evidencias pendientes de verificación.
- Revisa los 138 pares descriptor–compuesto pendientes de confirmar.
- Resuelve las incidencias de las 369 referencias de proceso truncadas cuando sea posible recuperar sus identificadores.
- Completa los CAS y CID faltantes utilizando PubChem y otras fuentes químicas verificables.
- Comprueba el estatus bibliográfico de Curioni 2002 y la independencia de los estudios primarios.
- Revisa las posibles duplicaciones bibliográficas que puedan afectar las etiquetas.
- Comprueba las asociaciones entre compuestos, quesos y descriptores.
- Prioriza las evidencias correspondientes a las seis familias aromáticas armonizadas: `fruity`, `vegetal`, `lactic`, `floral`, `toasted` y `animal`.

### Resultados

Actualiza las tablas pertinentes y genera `FASE4_Control_Calidad.md`, incluyendo las incidencias resueltas, las fuentes consultadas, las correcciones realizadas y los casos sin evidencia suficiente.

**No quiero que dejes pendientes únicamente porque requieren consulta bibliográfica. Investiga y resuelve todo lo que esté documentalmente a tu alcance.**

---

## FASE 5 — Desarrollar y evaluar el modelo compuesto → familia aromática

Utiliza la base armonizada y corregida de la Fase 4.

### Preparación

- Construye el conjunto de entrenamiento a partir de `fact_compound_odor.csv`.
- Utiliza la ontología armonizada de la Fase 3.
- Conserva las seis familias aromáticas seleccionadas, salvo que la evidencia justifique modificar esa selección.
- Identifica compuestos únicos y controla posibles duplicaciones.
- Obtén propiedades químicas verificables desde PubChem, incluyendo SMILES y otras variables relevantes.
- Calcula fingerprints moleculares cuando sea técnicamente posible.
- Diferencia etiquetas positivas, negativas explícitas y desconocidas. No conviertas automáticamente etiquetas ausentes en negativas.

### Entrenamiento

Entrena y compara modelos adecuados para el tamaño de la base:

- Modelo de referencia basado en la clase química.
- Regresión logística regularizada.
- Random Forest.
- Otros modelos sencillos únicamente si están justificados por los resultados.

Utiliza validación agrupada por compuesto y evita que un mismo compuesto aparezca simultáneamente en entrenamiento y prueba.

Controla el desbalance, la dependencia entre evidencias y las etiquetas incompletas.

### Evaluación

Calcula las métricas que puedan estimarse válidamente, incluyendo macro-F1 y AUPRC por familia cuando existan etiquetas evaluables.

Compara los modelos con la línea base y analiza sus errores.

No afirmes que un modelo es predictivo o superior simplemente porque alcanza una métrica alta. Comprueba que la evaluación realmente mida generalización a compuestos no vistos.

### Resultados

Entrega modelos entrenados, scripts ejecutables, predicciones, métricas, tablas y gráficos, junto con `FASE5_Modelo_Compuesto_Aroma.md`.

Si las etiquetas disponibles no permiten una evaluación supervisada fiable, implementa la mejor evaluación metodológicamente defendible, documenta la limitación y conserva los resultados exploratorios sin atribuirles una validez que no tienen.

---

## FASE 6 — Extraer información experimental por muestra

Esta fase es fundamental para el objetivo final de predecir aromas desde variables de producción.

### Investigación bibliográfica

Localiza y consulta los estudios primarios ya citados, empezando por:

- Moio 1998 y 2000.
- Qian 2002.
- Milo 1997.
- Boscaini 2003.
- Chen 2022.
- Suriyaphan 2001.
- Christensen 1995.
- Arora 1995.
- Larrayoz 2002.

Amplía la búsqueda a otros estudios experimentales cuando sea necesario.

No te limites a los resúmenes: consulta tablas, materiales suplementarios, metodología y resultados completos cuando estén accesibles.

### Extracción

Construye las tablas:

**`sample.csv`**

Identificación de estudio y muestra, tipo de queso, leche, tratamiento, cuajo, cultivos, maduración y demás condiciones de producción documentadas.

**`sample_compound.csv`**

Compuestos medidos en cada muestra, valores, unidades, método analítico y resultados de no detección.

**`sample_descriptor.csv`**

Descriptores sensoriales asociados a cada muestra, intensidad o presencia, método de evaluación y correspondencia con la ontología armonizada.

### Criterios científicos

- Cada muestra debe tener un identificador único.
- Cada medición debe estar asociada con su muestra real.
- No atribuyas condiciones típicas del queso a una muestra experimental.
- Distingue resultados de panel sensorial, GC-O y propiedades odorantes de compuestos aislados.
- No inventes negativos cuando un artículo simplemente omite un compuesto o descriptor.
- Conserva las unidades originales y documenta cualquier conversión.
- Registra para cada dato la fuente, página, tabla o sección.
- Distingue réplicas técnicas, réplicas biológicas y muestras independientes cuando la fuente permita identificarlas.

### Resultados

Entrega las tres tablas por muestra, sus diccionarios de datos y `FASE6_Extraccion_Muestras.md`.

Calcula cuántas muestras independientes y estudios distintos se recuperaron, cuántos registros tienen producción y aroma vinculados y qué variables siguen faltando.

Vuelve a evaluar la viabilidad de los modelos producción → aroma y producción → compuestos.

No supongas que alcanzarás 50 o 100 muestras. Reporta la cantidad real obtenida.

---

## DOCUMENTACIÓN FINAL

Actualiza la bitácora, el diccionario de datos y la auditoría predictiva.

Genera un informe `INFORME_FINAL_FASES_4_5_6.md` con:

- Actividades ejecutadas.
- Registros investigados y corregidos.
- Fuentes científicas verificadas.
- Resultados reales del entrenamiento.
- Métricas y limitaciones.
- Nuevas muestras experimentales recuperadas.
- Comparación con la base anterior.
- Viabilidad actualizada de los modelos A, B y C.
- Recomendación fundamentada para las Fases 7 y 8.

## CRITERIO DE FINALIZACIÓN

Quiero que avances hasta obtener resultados concretos y reproducibles, no solo archivos vacíos o planes.

No me pidas que revise manualmente artículos, complete celdas o clasifique datos. Realiza esas actividades directamente siempre que tengas acceso a los recursos necesarios.

Cuando un artículo no esté accesible o un dato no exista, indica la limitación y continúa con las demás fuentes.

**Prioriza completar el máximo trabajo científicamente verificable. No sacrifiques la exactitud para aparentar que el 100 % de la información está disponible.**

El objetivo es dejar las Fases 4, 5 y 6 ejecutadas hasta donde permitan los datos reales y preparar el proyecto para avanzar hacia la predicción del aroma a partir de las variables de producción.