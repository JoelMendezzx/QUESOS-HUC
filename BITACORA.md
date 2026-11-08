# Bitácora del proyecto QUESOS-HUC

Registro de lo que se hizo en cada sesión. La entrada más reciente va primero.

---

## 2026-11-08 · Sesión 5 — Fases 4, 5 y 6 ejecutadas → base `v3-fases456`

Instrucción seguida: [`corrections/fases456.md`](corrections/fases456.md). Informe: [INFORME_FINAL_FASES_4_5_6.md](INFORME_FINAL_FASES_4_5_6.md).

### Qué se hizo

**Fase 4 — Control de calidad** ([FASE4](FASE4_Control_Calidad.md))
- Se descargaron y guardaron en caché PubChem y Flavornet (`data_external/`).
- Se resolvieron 42 de las 53 evidencias pendientes y 64 de los 138 pares por confirmar, con fuente o por inferencia documentada.
- CID faltantes: de 38 a 5. CAS faltantes: de 16 a 5.
- Se añadieron propiedades químicas y huellas moleculares de 199 compuestos.
- Se confirmó que Curioni 2002 es una **revisión**. Se añadió la independencia de estudios (`independent_study_keys`) y se marcaron 31 duplicados (`use_as_cheese_aroma_label_dedup`).
- Se recalcularon enlaces exactos evidencia → proceso. Las 369 listas cortadas no son reconstruibles; se documenta.

**Fase 5 — Modelo compuesto → familia** ([FASE5](FASE5_Modelo_Compuesto_Aroma.md))
- 144 compuestos y 6 familias; validación agrupada por estructura (10 × 5 pliegues).
- Random Forest: macro-AUPRC 0,57, frente a 0,46 de la clase química y 0,22 del azar. Prueba de permutación p = 0,02.
- Validación externa con 510 compuestos de Flavornet: generaliza en toasted y fruity; no en lactic ni animal.

**Fase 6 — Datos por muestra** ([FASE6](FASE6_Extraccion_Muestras.md))
- 7 estudios de acceso abierto, 64 muestras, 30 unidades de producción, 2.192 mediciones de compuestos y 425 descriptores de aroma.
- Los 10 estudios prioritarios, incluido Jo 2018, son de pago: no se extrajeron.
- Viabilidad:
  - **A:** direcciones coherentes (maduración 14 de 16 compuestos; pasteurización 8 de 8 pares).
  - **C:** no viable todavía (20 muestras, 3 métodos).

### Correcciones durante la sesión
- La normalización de términos trataba distinto «vegetables» y «vegetable». Por eso «Cooked vegetables» se asignaba a lactic; corregido a vegetal.
- «Toasted» y «Ammonia» de Torri 2021 quedaban sin familia; corregido.
- La conversión a texto del artículo de Idiazabal se había sobrescrito con una respuesta vacía de Europe PMC; se regeneró desde el HTML.

### Decisiones a revisar por la usuaria
1. **Acceso a artículos de pago** (Jo 2018, Qian 2002, Moio 1998/2000) a través de la biblioteca. Es lo que más puede mejorar el proyecto.
2. La asignación de los 197 términos de Flavornet a familias de Bérodier (`FN_FAMILY` en `scripts/phase4_quality.py`).

### Versión
Etiqueta git **`v3-fases456`**. Se conservan `v1-clean` y `v2-harmonized`.

---

## 2026-11-08 · Sesión 4 — Fases 1, 2 y 3 ejecutadas → base `v2-harmonized`

Instrucción seguida: [`corrections/fases123.md`](corrections/fases123.md).

### Qué se hizo
1. **Investigación de fuentes.**
   - Rueda de Bérodier et al. (1997) en sus tres niveles, leída en el protocolo del ITA St-Hyacinthe (pp. 2–3).
   - Léxico de Drake et al. (2001), con sus 32 términos.
   - Lista de quesos con DOP/IGP de la UE.
   - Unos 30 pliegos DOP/IGP y normas: Grana Padano, Parmigiano Reggiano, Gorgonzola, Gruyère, Emmental, Ragusano, Mozzarella di Bufala, pecorinos, Manchego, Idiazabal, Roncal, Majorero, Palmero, Flor de Guía, San Simón, Camembert, Livarot, Sainte-Maure, West Country Farmhouse Cheddar, Gouda Holland, 21 CFR, Minas Frescal…

   Todo está en [REFERENCIAS_VERIFICADAS.md](REFERENCIAS_VERIFICADAS.md).
2. **Decisiones registradas** en [`scripts/harmonization_decisions.py`](scripts/harmonization_decisions.py), con estado (`verificado_con_fuente` / `inferencia_documentada` / `no_verificado`), fuente y criterio para cada registro.
3. **Integración en la base:** [`scripts/build_clean_db.py`](scripts/build_clean_db.py) aplica las decisiones, escribe los 4 registros completados en `corrections/`, el registro de cambios y las comprobaciones de calidad.
4. **Base regenerada** y **auditoría** repetida.
5. **Documentación nueva:** [FASE1](FASE1_Armonizacion_Quesos.md), [FASE2](FASE2_Armonizacion_Produccion.md), [FASE3](FASE3_Armonizacion_Descriptores.md), [REFERENCIAS_VERIFICADAS](REFERENCIAS_VERIFICADAS.md) e [INFORME_FINAL](INFORME_FINAL_FASES_1_2_3.md).
6. **Eliminado:** el generador de plantillas y los archivos de "revisión IA pendiente de validación" (a pedido de la usuaria).

### Cifras clave
| Registro | Revisados | Verificados | Inferidos | Sin verificar |
|---|---|---|---|---|
| Equivalencias de queso | 282 | 107 | 174 | 1 |
| «Check in the table» | 11 | 0 | 8 | 3 |
| Familia tecnológica / país-DOP | 72 / 72 | 20 / 32 | 45 / 18 | 7 / 22 |
| Valores de producción | 160 | 96 | 20 | 44 |
| Descriptores de aroma | 169 | 61 | 108 | 0 |

- **Quesos con producción completa:** de 12 a **20**.
- **Combinaciones de producción con aroma (fuertes):** de 5 a **11**.
- **Clases para ML:** 6 familias de Bérodier (fruity, vegetal, lactic, floral, toasted, animal).
- **Control de calidad:** 30/30 OK. Sin pérdida de registros y sin referencias rotas.

### Correcciones durante la sesión
- Al unificar nombres aparecían 14 duplicados evidencia × queso; se fusionaron (la tabla plana pasa de 2.029 a 2.023 filas).
- Ubicaciones de descriptores corregidas con la rueda de Bérodier: miel → floral, vainilla → torréfié, menta → épicé, frutos secos → fruité.
- Formaella no es pasta hilada según la fuente: pasa a `hard_pressed`.

### Decisiones a revisar por la usuaria
1. La categoría añadida `hard_pressed` (pasta prensada no cocida).
2. La exclusión de «other/autres» como clase de ML.
3. Si consigue un segundo experto: revisar una muestra de las 378 inferencias para poder publicar un índice de acuerdo.

### Versión
Etiqueta git **`v2-harmonized`**. La anterior sigue disponible como `v1-clean`.

---

## 2026-11-08 · Sesión 3 — Control de versiones y plantillas de revisión (Fases 1–3)

### Qué se hizo
1. **Control de versiones (git).** Se inicializó un repositorio en la carpeta y se guardó la versión actual con la etiqueta **`v1-clean`**. Es la base limpia antes de cualquier revisión experta, y se puede volver a ella en cualquier momento.
2. **Plantillas de revisión experta** en la carpeta [`corrections/`](corrections/), generadas por [`scripts/make_correction_templates.py`](scripts/make_correction_templates.py):

| Archivo | Fase | Filas | Para qué |
|---|---|---|---|
| [`fase1_quesos_equivalencias.xlsx`](corrections/fase1_quesos_equivalencias.xlsx) | 1.1–1.3 | 282 | Validar cómo se unificó cada nombre de queso |
| [`fase1_quesos_familia_tecnologica.xlsx`](corrections/fase1_quesos_familia_tecnologica.xlsx) | 1.4–1.5 | 72 | Asignar familia tecnológica, país y DOP |
| [`fase2_produccion_valores.xlsx`](corrections/fase2_produccion_valores.xlsx) | 2 | 160 | Completar leche, tratamiento, cuajo y maduración de los 40 quesos con aroma |
| [`fase3_descriptores_mapeo.xlsx`](corrections/fase3_descriptores_mapeo.xlsx) | 3 | 169 | Clasificar los descriptores de aroma en 3 niveles, con doble revisión |
| [`referencia_familias_actuales.csv`](corrections/referencia_familias_actuales.csv) | 3 | 54 | Familias de descriptor que aparecen hoy en la fuente |

3. **Instrucciones de uso** en [`corrections/README.md`](corrections/README.md).

### Cómo están hechas las plantillas
- **Gris = datos y propuestas del script (no editar). Amarillo = lo rellena el revisor.** Hay listas desplegables donde aplica.
- Las propuestas automáticas se basan **solo en datos que ya están en el Excel** y están marcadas como `propuesta`. Ejemplo: si el perfil dice *P. roqueforti*, se propone `blue`. No se inventó ningún valor.
- Cada valor nuevo exige **fuente y página**.
- El script **no sobrescribe** una plantilla que ya existe, para no perder trabajo de revisión.
- Se usa Excel (`.xlsx`) en vez del CSV previsto en el plan: es más fácil de editar y evita problemas con el separador `;` del Excel en español.

### Cifras clave
- **Familia tecnológica:** 22 quesos con propuesta clara, 5 ambiguos (p. ej. Gruyère) y 45 sin propuesta (hay que decidirlos con fuente).
- **Producción (160 valores):** la **maduración** es lo más incompleto (23 desconocidos y 10 ambiguos de 40), seguida del **tratamiento térmico** (22 desconocidos y 7 ambiguos).
- **Descriptores:** 6 marcados como "no es aroma" y 62 con varios términos unidos que hay que revisar si se separan.

### Correcciones durante la sesión
- La propuesta de familia "fresco" se asignaba a quesos como Pecorino Siciliano ("fresh to 4 months"). Ahora solo se propone si la maduración es realmente de queso fresco.

### Pendiente — decisiones que necesitan a la usuaria o al grupo
1. **Elegir el léxico de referencia de descriptores** (p. ej. Bérodier et al. 1997 o Drake et al. 2001). Es lo que más condiciona la Fase 3.
2. **Confirmar la lista de familias tecnológicas** de quesos o cambiarla por la que use el grupo.
3. **Asignar revisores:** quién revisa quesos y producción, y quiénes serán los dos revisores independientes de descriptores.
4. Cuando haya plantillas rellenas: conectar las correcciones al script para generar la **base v2 armonizada**.

---

## 2026-11-08 · Sesión 2 — Auditoría de viabilidad y plan de trabajo

### Qué se hizo
- **Auditoría de viabilidad predictiva** → [`Auditoria_viabilidad_predictiva.md`](Auditoria_viabilidad_predictiva.md) y script [`scripts/audit_viability.py`](scripts/audit_viability.py). Las tablas de detalle están en [`clean/auditoria/`](clean/auditoria/).
- **Plan de trabajo en 9 fases** → [`Plan_de_trabajo_HUC.md`](Plan_de_trabajo_HUC.md).
- Carpeta `clean/` reorganizada en **`modelo/`** (lo que se usa para entrenar) y **`soporte/`** (respaldo).
- Corregido un fallo en `profile_completeness`, que contaba los valores vacíos como conocidos. Ahora mide 4 bloques: leche, tratamiento, cuajo/cultivo y maduración.

### Resultados clave
- Producción → aroma directo: **no viable** (solo 9 combinaciones de producción distintas).
- Compuesto → familia aromática: **viable** (488 pares, 144 compuestos).
- 8 familias de aroma con buen respaldo: Fruity, Lactic, Floral, Toasted, Vegetable, Green, Animal y Chemical.
- El 50 % de las etiquetas depende de 3 estudios (Curioni 2002, Moio 1998 y Moio 2000).

---

## 2026-11-08 · Sesión 1 — Análisis y limpieza de la base

### Qué se hizo
- **Análisis** del Excel con propuestas de mejora → [`Analisis_y_mejoras_HUC-Database.md`](Analisis_y_mejoras_HUC-Database.md).
- **Base limpia en CSV** generada por [`scripts/build_clean_db.py`](scripts/build_clean_db.py), con 27 tablas, diccionario de datos y lista de problemas (`qa_issues.csv`). El Excel original no se modificó.
- Principales arreglos:
  - 118+ nombres de queso unificados en 72 quesos concretos;
  - compuestos fusionados por CAS;
  - variables de producción convertidas a columnas;
  - columna `claim_scope` para separar "olor del compuesto" de "aroma medido en el queso".
- Hallazgo: los CID de PubChem de la hoja *Odor & Aroma* estaban desalineados en 26 filas. Se usan los de *Synonyms*.
