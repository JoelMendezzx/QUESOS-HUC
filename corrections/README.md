# Plantillas de revisión experta (Fases 1–3)

Generadas por [`scripts/make_correction_templates.py`](../scripts/make_correction_templates.py) a partir de la base limpia (`clean/`).

## Reglas para rellenarlas

1. **Columnas grises = datos y propuestas del script. No se editan.**
2. **Columnas amarillas = las rellena el revisor.** Varias tienen lista desplegable.
3. Todo lo que dice `propuesta_*` es una **sugerencia automática** basada solo en datos que ya están en el Excel. No es una decisión.
4. **Cada valor nuevo necesita fuente** (columna `fuente_*`): referencia y página. Sin fuente, el valor no se usará.
5. Rellenar siempre `revisado_por` y `fecha_revision`.
6. El script **no sobrescribe** una plantilla que ya existe, así que el trabajo de revisión está protegido. Para regenerarlas desde cero (perdiendo lo escrito): `python scripts/make_correction_templates.py --force`.

Las filas están ordenadas por importancia: primero lo que más pesa en el modelo.

---

## `fase1_quesos_equivalencias.xlsx` — ¿está bien unificado cada nombre de queso? (282 filas)

Cada nombre original de queso y a qué queso canónico se asignó.

| Columna amarilla | Qué poner |
|---|---|
| `decision` | `OK` si la equivalencia es correcta · `CAMBIAR` si no · `DUDA` si hay que consultarlo |
| `corregido_cheese_name_std` | Solo si `CAMBIAR`: el nombre canónico correcto |
| `corregido_label_type` | Solo si cambia el tipo: `specific`, `generic_category`, `multi_cheese`, `not_cheese`, `unresolved` |
| `fuente_correccion` | Por qué se cambia (p. ej. el PDF donde aparece) |

Prioridad: la fila `check in the table` (11 evidencias) y las etiquetas `multi_cheese`.

---

## `fase1_quesos_familia_tecnologica.xlsx` — familia tecnológica, país y DOP (72 quesos concretos)

| Estado de la propuesta | Cantidad | Significado |
|---|---|---|
| `propuesta` | 22 | El perfil tiene un indicador claro (p. ej. *P. roqueforti* → `blue`) |
| `propuesta_ambigua` | 5 | Hay varios candidatos (p. ej. Gruyère: corteza lavada y cuajada cocida) |
| `sin_propuesta` | 45 | El perfil no permite proponer nada; hay que decidirlo con una fuente |

| Columna amarilla | Qué poner |
|---|---|
| `decision` | `OK` / `CAMBIAR` / `DUDA` sobre la propuesta |
| `cheese_family_final` | Una de: `fresh_acid_lactic`, `fresh_rennet`, `pasta_filata`, `brined`, `soft_bloomy_rind`, `washed_rind_smear`, `blue`, `semi_hard`, `hard_cooked`, `grana_extra_hard`, `swiss_type_eyes`, `goat_lactic`, `other` |
| `fuente_familia` | Referencia que justifica la familia |
| `pais_iso`, `pdo_pgi`, `fuente_pais_dop` | País (código ISO, p. ej. `IT`), DOP/IGP y su fuente (pliego de condiciones) |

Si la lista de familias no encaja con la clasificación que usa el grupo, se puede cambiar: avísame y regenero la plantilla.

---

## `fase2_produccion_valores.xlsx` — completar variables de producción (40 quesos × 4 bloques = 160 filas)

Solo los 40 quesos que tienen etiquetas de aroma, ordenados por `prioridad` (1 = más etiquetas fuertes).

Estado actual de los 160 valores:

| Bloque | Conocido | Ambiguo | Desconocido |
|---|---|---|---|
| Leche | 28 | 1 | 11 |
| Cuajo / cultivo | 24 | 0 | 16 |
| Tratamiento térmico | 11 | 7 | 22 |
| Maduración | 7 | 10 | 23 |

| Columna amarilla | Qué poner |
|---|---|
| `valor_nuevo` | El valor completo (ver `unidad_o_formato`). Maduración en días: `270–365` |
| `value_scope` | `type_specification` = lo que dice el pliego/tipo de queso · `sample` = valor de una muestra concreta de un estudio |
| `fuente`, `pagina` | Obligatorias |

Filas con `completar = no (solo verificar)`: el valor ya existe; basta con confirmarlo o corregirlo.

---

## `fase3_descriptores_mapeo.xlsx` — ontología de descriptores de aroma (169 descriptores)

**Antes de empezar hay que elegir el léxico de referencia** (Fase 3.1 del plan) y escribirlo en `lexico_referencia`.

Columnas de ayuda: `terminos` (los términos unidos con "/" en la fuente), `familias_en_fuente`, `n_filas_etiqueta`, `n_compuestos` y `n_etiquetas_fuertes`.

Propuestas del script:
- `propuesta_es_aroma = no` en 6 descriptores cuya familia en la fuente es General/Character/Body.
- `propuesta_separar_terminos = revisar` en 62 descriptores que unen varios términos (p. ej. `Coconut / Peach`).
- `propuesta_level1` = primera familia indicada en la fuente (sin armonizar).

**Doble revisión, para poder calcular el acuerdo (kappa):**
1. El revisor 1 rellena solo las columnas `revisor1_*`.
2. El revisor 2 trabaja en una **copia** del archivo (`fase3_descriptores_mapeo_revisor2.xlsx`), rellena solo `revisor2_*` y **no mira** las respuestas del revisor 1.
3. Con las dos copias, el script calcula el kappa y lista los desacuerdos.
4. Se resuelven en una reunión y se rellenan las columnas `consenso_*`.

| Columna | Qué poner |
|---|---|
| `revisorN_es_aroma` | `sí` / `no` |
| `revisorN_level1` | Familia general (≈ 10–12 en total) |
| `revisorN_level2` | Subfamilia (≈ 30–40 en total) |
| `revisorN_level3` | Descriptor final; si hay que separar términos, uno por línea dentro de la celda |
| `revisorN_termino_lexico` | Término equivalente en el léxico de referencia |

`referencia_familias_actuales.csv` lista las 54 familias que aparecen hoy en la fuente, como punto de partida para definir el nivel 1.

---

## Después de rellenarlas

Cuando haya plantillas revisadas, el siguiente paso es que `build_clean_db.py` lea estas correcciones y genere la **base v2 armonizada**, dejando registro de cada cambio.
