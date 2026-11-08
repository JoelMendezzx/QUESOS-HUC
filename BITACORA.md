# Bitácora del proyecto QUESOS-HUC

Registro de lo que se hizo en cada sesión. La entrada más reciente va primero.

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
