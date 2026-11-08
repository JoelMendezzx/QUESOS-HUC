# Auditoría de viabilidad predictiva — Base HUC

**Proyecto:** *Cheese Types, Production Variables and Sensory Descriptor Harmonization for Data-Driven Aroma Prediction*
**Datos auditados:** base limpia en `clean/` (generada desde el Excel original)
**Script reproducible:** [`scripts/audit_viability.py`](scripts/audit_viability.py) → tablas de detalle en [`clean/auditoria/`](clean/auditoria/)
**Fecha:** 2026-11-08

---

## Veredicto

| Modelo | Pregunta que responde | ¿Viable hoy? | Motivo principal |
|---|---|---|---|
| **C. Producción → aroma (directo)** | "Con esta leche, cuajo y maduración, ¿a qué olerá?" | **No** | Solo **9 combinaciones distintas** de variables de producción tienen etiquetas de aroma (5 si se exige evidencia fuerte). |
| **B. Compuesto → descriptor** | "¿A qué huele este compuesto?" | **Sí, a nivel de familia** | 488 pares, 144 compuestos y 8 familias con buen respaldo. Por descriptor individual no alcanza: solo 8 descriptores tienen ≥ 10 compuestos. |
| **A. Producción → compuestos** | "¿Cómo cambia este compuesto si cambio la maduración, la grasa…?" | **Solo exploratorio** | 144 comparaciones de 14 estudios, casi todas a nivel de familia química; con compuesto concreto solo hay 3 estudios. |

**Conclusión:** la base sirve hoy para **describir y armonizar**, y para un **modelo compuesto → familia aromática**. Para predecir el aroma a partir de la producción falta un cambio de unidad. Hay que pasar del **tipo de queso** a la **muestra de un estudio**, con sus propias variables de producción y su resultado sensorial. Ese dato está en los estudios primarios ya citados, pero no en el Excel.

---

## Definiciones usadas

- **Queso concreto:** `cheese_label_type = specific`. Se excluyen categorías genéricas ("Blue cheeses"), etiquetas con varios quesos y no-quesos.
- **Etiqueta de aroma del queso:** `use_as_cheese_descriptor_label = True`, es decir, la fuente da el descriptor para ese compuesto en ese queso.
- **Bloques de producción:** leche, tratamiento térmico, cuajo/cultivo y maduración. Un bloque está "conocido" si no figura como *not specified*.
- **Estudio primario:** fuente de tipo `primary` o fuente primaria citada en la evidencia, normalizada como "apellido año".
- **GC-O:** el texto de la evidencia menciona Charm, AEDA, FD, OAV, DF, OI u OP. Es un indicio, no una confirmación del método.

---

## 1. ¿Cuántos quesos tienen variables de producción suficientemente completas?

**Respuesta: 13 de 72 quesos concretos tienen los 4 bloques; solo 7 si se exige un valor sin ambigüedad.**

| Nivel | Quesos |
|---|---|
| Quesos distintos en la base (todos los tipos) | 129 |
| Quesos concretos | 72 |
| … con perfil de producción | 50 |
| … con especie de leche conocida | 41 |
| … con cuajo/cultivo conocido | 37 |
| … con tratamiento térmico conocido | 29 (solo 19 sin ambigüedad: no "raw *or* pasteurized") |
| … con maduración conocida | 23 |
| **… con los 4 bloques conocidos** | **13** |
| **… con los 4 bloques sin ambigüedad** (tratamiento exacto + maduración numérica) | **7** |

Distribución de la completitud (50 quesos con perfil):

| Bloques conocidos | 0/4 | 1/4 | 2/4 | 3/4 | 4/4 |
|---|---|---|---|---|---|
| Quesos | 1 | 11 | 8 | 17 | 13 |

- **4 bloques:** Beyaz peynir, Cheddar, Cheddar (aged), Cheddar (low-fat), Feta, Fresh, Gouda, Grana Padano, Majorero, Mozzarella (buffalo), Pecorino Romano, Roncal, San Simón da Costa.
- **Sin ambigüedad:** Beyaz peynir, Feta, Gouda, Grana Padano, Majorero, Mozzarella (buffalo), Roncal.

**Implicación:** el bloque que más falta es la **maduración** (desconocida en 27 de 50 perfiles), justo una de las variables con más efecto en el aroma. Además, 9 perfiles se deducen solo del nombre del queso en la fuente.

Detalle: [`clean/auditoria/q1_completitud_quesos.csv`](clean/auditoria/q1_completitud_quesos.csv)

---

## 2. ¿Cuántos tienen descriptores sensoriales realmente medidos?

**Respuesta: 40 quesos tienen alguna etiqueta. Si se exige evidencia fuerte, quedan 20; con confirmación en la fuente primaria, solo 7.**

| Nivel de exigencia | Filas | Quesos | Pares queso–descriptor | Descriptores | Compuestos |
|---|---|---|---|---|---|
| A. Toda etiqueta queso–descriptor | 752 | 40 | 403 | 109 | 113 |
| B. A sin alerta de doble conteo | 615 | 40 | 370 | 99 | 111 |
| **C. B + (GC-O o fuente primaria)** | **388** | **20** | **264** | **90** | **91** |
| D. Solo confirmación en la fuente primaria | 146 | 7 | 108 | 61 | 52 |

Quesos con confirmación primaria (nivel D), con su número de descriptores: Grana Padano (48), Gorgonzola (30), Cheddar (11), Gouda (10), Grana Trentino (4), Parmigiano Reggiano (4), Limburger (1).

Quesos con más pares en el nivel C: Grana Padano (53), Gorgonzola (33), Cheddar (26), Parmigiano Reggiano (24), Camembert (15), Gruyère (15), Farmhouse Cheddar (14), Mozzarella (buffalo) (13).

**Implicaciones:**
- Hay que tener en cuenta 428 filas (no incluidas arriba) en las que el descriptor es **la nota de olor del compuesto**, sin medición en ese queso. Son útiles para el modelo B, no para el C.
- La información está **muy concentrada**: 3 quesos (Grana Padano, Gorgonzola y Cheddar) acumulan el 42 % de los pares con evidencia fuerte (112 de 264).
- Ningún dato es **negativo** ("se midió y no tenía ese olor"). Para el modelo, todo lo no reportado es desconocido, no ausente.

Detalle: [`q2_etiquetas_medidas.csv`](clean/auditoria/q2_etiquetas_medidas.csv), [`q2_quesos_con_etiquetas_C.csv`](clean/auditoria/q2_quesos_con_etiquetas_C.csv)

---

## 3. ¿Cuántos estudios primarios independientes existen?

**Respuesta: 44 estudios primarios respaldan las etiquetas de aroma, pero solo 20 en el nivel de evidencia fuerte. Un solo estudio (Curioni 2002) aparece en el 30 % de las etiquetas.**

| Conjunto | Estudios primarios distintos |
|---|---|
| Toda la tabla de evidencias | 70 |
| Etiquetas queso–descriptor (nivel A) | 44 |
| Etiquetas con evidencia fuerte (nivel C) | **20** |
| Hoja de proceso (todas las comparaciones) | 86 citas distintas* |
| Hoja de proceso, comparaciones con compuesto concreto y ratio | **3** |

\* La mayoría de las comparaciones de proceso son de familias químicas ("Esters", "Total volatiles"). Con ratio calculable hay 144 comparaciones de 14 estudios.

**Concentración de la evidencia** (filas de etiqueta por estudio):

| Estudio | Filas | % de 752 |
|---|---|---|
| Curioni 2002 | 226 | 30 % |
| Moio 1998 | 77 | 10 % |
| Moio 2000 | 73 | 10 % |
| Qian 2002 | 38 | 5 % |
| Milo 1997 | 28 | 4 % |
| Boscaini 2003 | 21 | 3 % |
| 38 estudios restantes | 1–20 cada uno | — |

- Un 50 % de las etiquetas depende de solo 3 estudios: Curioni 2002, Moio 1998 y Moio 2000.
- 124 de 752 etiquetas (16 %) no tienen ningún estudio primario identificable; solo citan libros.
- Curioni 2002 figura en la base como **revisión** (`source_type = review`), aunque el Excel lo cita como fuente primaria. Si fuera una recopilación, la independencia real sería menor.

**Implicación:** para validar honestamente hay que dejar fuera **un estudio cada vez** (*leave-one-study-out*), no filas al azar. Con 20 estudios en el nivel fuerte, la validación es posible pero frágil, y el resultado dependerá mucho de Curioni 2002 y Moio.

Detalle: [`q3_estudios_primarios.csv`](clean/auditoria/q3_estudios_primarios.csv)

---

## 4. ¿Cuáles son las familias aromáticas con mayor respaldo?

**Respuesta: 8 familias tienen ≥ 10 quesos y ≥ 10 estudios primarios: Fruity, Lactic, Floral, Toasted, Vegetable, Green, Animal y Chemical.**

Familia = primera familia indicada en la fuente (`family_l1_as_in_source`), etiquetas de nivel A:

| Familia | Filas | Quesos | Descriptores | Compuestos | Estudios primarios | % confirmación primaria |
|---|---|---|---|---|---|---|
| **Fruity** | 138 | 24 | 12 | 33 | 21 | 34 % |
| **Lactic** | 41 | 15 | 7 | 14 | 18 | 17 % |
| **Floral** | 70 | 19 | 5 | 14 | 17 | 3 % |
| **Toasted** | 53 | 15 | 13 | 23 | 15 | 6 % |
| **Vegetable** | 55 | 14 | 7 | 9 | 15 | 16 % |
| **Green** | 47 | 12 | 3 | 21 | 14 | 15 % |
| **Animal** | 84 | 23 | 12 | 19 | 13 | 10 % |
| **Chemical** | 43 | 13 | 7 | 17 | 10 | 16 % |
| Off-flavor | 21 | 12 | 4 | 8 | 9 | 19 % |
| Nutty | 25 | 9 | 4 | 10 | 8 | 32 % |
| Sweet | 14 | 6 | 5 | 11 | 8 | 29 % |
| Acidic | 18 | 10 | 3 | 6 | 7 | 33 % |
| Fruit | 19 | 7 | 1 | 4 | 7 | 16 % |
| Fatty | 29 | 10 | 4 | 13 | 5 | 24 % |
| Fungal | 22 | 9 | 2 | 5 | 5 | 27 % |
| Sulfur, Earthy, Fermented, Spicy, Woody, Savory… | < 20 | ≤ 6 | — | — | ≤ 5 | — |

Con evidencia fuerte (nivel C), el orden se mantiene: Fruity (16 quesos, 13 estudios), Vegetable (14, 12), Animal (12, 10), Floral (12, 10), Toasted (10, 9), Lactic (10, 9), Green (9, 8), Chemical (8, 8).

**Implicaciones:**
- Las **8 familias** son las clases candidatas a predecir. Por debajo de ese nivel, la mayoría de los descriptores tiene muy pocos ejemplos.
- **Floral** y **Toasted** tienen muchas etiquetas pero casi ninguna confirmación primaria (3 % y 6 %): su respaldo viene sobre todo de libros.
- Hay familias que conviene **fusionar antes de modelar**: "Fruit" y "Fruity" son casi seguro la misma. Esa decisión debe tomarla una persona con criterio sensorial; no se hizo automáticamente.
- "General", "Body", "Character" y "General intensity" no son notas de aroma y deben excluirse del objetivo.

Detalle: [`q4_familias_aromaticas.csv`](clean/auditoria/q4_familias_aromaticas.csv), [`q4_familias_compuesto_olor.csv`](clean/auditoria/q4_familias_compuesto_olor.csv)

---

## 5. ¿Cuántas muestras relacionan producción y aroma?

**Respuesta: 274 filas, pero solo 11 quesos y 9 combinaciones distintas de variables de producción. Con evidencia fuerte: 6 quesos y 5 combinaciones.**

| Subconjunto | Filas | Quesos | Combinaciones de producción distintas | Pares queso–descriptor |
|---|---|---|---|---|
| Etiquetas de aroma (queso concreto) | 752 | 40 | 35 | 403 |
| … con los 4 bloques de producción conocidos | 274 | 11 | **9** | 153 |
| … y además GC-O/primaria sin doble conteo | 173 | 6 | **5** | 115 |

- **Con los 4 bloques:** Cheddar, Cheddar (aged), Cheddar (low-fat), Farmhouse Cheddar, Fresco, Gouda, Grana Padano, Majorero, Mozzarella (buffalo), Pecorino Romano, Roncal.
- **Con evidencia fuerte:** Cheddar, Farmhouse Cheddar, Gouda, Grana Padano, Mozzarella (buffalo), Roncal. Están respaldados por 10 estudios primarios.

**Por qué el número que cuenta es 9 (o 5), y no 274:** las variables de producción se asignan **por tipo de queso**, no por muestra. Todas las filas de Grana Padano llevan las mismas variables. Para un modelo producción → aroma, cada combinación distinta es **un único punto de datos**. Además, las 4 variantes de Cheddar comparten la misma combinación en la tabla de evidencias.

**Vía indirecta (proceso → compuesto → olor):** 70 mediciones de la hoja de proceso relacionan un factor con un compuesto que tiene olor conocido. Cubren 16 compuestos, 3 factores (maduración, grasa y cultivo adjunto), 3 quesos (Manchego, Cheddar, Feta) y 3 estudios. 48 de esas 70 mediciones vienen de un solo estudio sobre la maduración de Manchego.

**Implicación:** **el modelo directo no es viable.** Con 5–9 puntos y unas 40 variables de producción, cualquier modelo memorizaría en lugar de aprender.

Detalle: [`q5_produccion_aroma.csv`](clean/auditoria/q5_produccion_aroma.csv)

---

## Recomendaciones, en orden

1. **Cambiar la unidad de análisis de "tipo de queso" a "muestra de un estudio".** Cada estudio primario describe sus propias muestras: maduración exacta, leche, tratamiento y resultado de GC-O o del panel. Extraer esa información de los 20 estudios del nivel fuerte daría decenas o cientos de muestras con producción y aroma propios, en lugar de 9 combinaciones.
   *Por dónde empezar:* Moio 1998, Moio 2000, Qian 2002, Milo 1997, Boscaini 2003, Chen 2022, Suriyaphan 2001, Christensen 1995, Arora 1995 y Larrayoz 2002. Son los que ya respaldan las etiquetas fuertes.
2. **Definir el objetivo a nivel de familia:** usar las 8 familias de la §4, tras decidir fusiones como Fruit/Fruity y excluir los términos generales.
3. **Empezar por el modelo B (compuesto → familia).** Es el único con datos suficientes hoy. Conviene enriquecerlo con propiedades químicas (estructura, umbral de olor) y con bases públicas de olores, citando la fuente de cada dato.
4. **Completar la maduración y el tratamiento térmico** de los 40 quesos con etiqueta, usando los pliegos de condiciones DOP. Cada valor debe llevar su fuente. Esto sube el número de quesos con producción completa, pero no resuelve el problema de fondo del punto 1.
5. **Registrar negativos.** Al extraer los estudios primarios, anotar también los compuestos y descriptores buscados y **no** encontrados.
6. **Validar dejando fuera un estudio cada vez** (*leave-one-study-out*), e informar del resultado con y sin Curioni 2002, Moio 1998 y Moio 2000.

---

## Limitaciones de esta auditoría

- El indicio de GC-O se basa en palabras clave del texto de la evidencia, así que puede fallar en ambos sentidos.
- Las citas primarias se normalizan como "apellido año". Dos artículos del mismo autor y año se cuentan como uno; en ese caso, el número de estudios estaría subestimado.
- Las familias son las de la fuente, sin armonizar todavía. Las cifras de la §4 pueden cambiar al fusionar familias.
- Todas las cifras se regeneran con `python scripts/audit_viability.py`, después de `python scripts/build_clean_db.py`.
