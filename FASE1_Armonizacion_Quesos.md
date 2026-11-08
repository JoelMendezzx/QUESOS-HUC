# Fase 1 — Armonización de tipos de queso

**Archivos:** [`corrections/fase1_quesos_equivalencias.xlsx`](corrections/fase1_quesos_equivalencias.xlsx) (hojas `equivalencias`, `check_in_the_table`, `padres_variantes`) y [`corrections/fase1_quesos_familia_tecnologica.xlsx`](corrections/fase1_quesos_familia_tecnologica.xlsx) (hojas `familias`, `definicion_familias`).
**Decisiones en código:** [`scripts/harmonization_decisions.py`](scripts/harmonization_decisions.py) · **Aplicación:** [`scripts/build_clean_db.py`](scripts/build_clean_db.py) · **Fuentes:** [`REFERENCIAS_VERIFICADAS.md`](REFERENCIAS_VERIFICADAS.md)

## Resultado

| Registro | Total | `verificado_con_fuente` | `inferencia_documentada` | `no_verificado` |
|---|---|---|---|---|
| Equivalencias de nombres | 282 | 107 | 174 | 1 |
| Evidencias «check in the table» | 11 | 0 | 8 | 3 |
| Relaciones queso padre → variante | 6 | 1 | 5 | 0 |
| Familia tecnológica | 72 | 20 | 45 | 7 |
| País y DOP/IGP | 72 | 32 | 18 | 22 |

Las 282 equivalencias producen **127 entradas de queso** en la base v2 (antes 129): 67 quesos concretos, 34 categorías genéricas, 22 etiquetas con varios quesos, 3 no-quesos y 1 sin resolver («European»). Las evidencias «check in the table» no son un queso: se resuelven una por una.

---

## 1.1 Equivalencias de nombres

### Metodología

Cada nombre original (de las hojas Evidence, Process and Volatiles, Odor & Aroma y Cheese Profiles) recibe un nombre canónico, un tipo y, si procede, un calificador de muestra. Las reglas, en orden:

| Regla | Estado | Criterio |
|---|---|---|
| Mismo nombre salvo mayúsculas, acentos o espacios | `verificado_con_fuente` (criterio textual) | Identidad textual |
| No es un queso (té negro, cacao, leche) | `verificado_con_fuente` (criterio textual) | Se conserva como `not_cheese` |
| Errata o variante ortográfica (Mozzarrella, Grana Tretino, Emmentaler, Parmigiano-Reggiano, Gruyere) | `inferencia_documentada` | Corrección a la forma registrada |
| Variante con calificador ("Grana Padano (12 months)", "Mozzarella (cow)", "Low-fat Cheddar") | `inferencia_documentada` | El calificador pasa a `sample_qualifier`: es una condición de la **muestra**, no un queso distinto |
| Nombre de grupo ("Blue cheeses", "Swiss-type cheeses", "Goat cheeses (…)") | `inferencia_documentada` | Se agrupa en la categoría genérica |
| Etiqueta con varios quesos ("Parmesan, Grana Padano") | `inferencia_documentada` | Se conserva: la fuente da el dato para el grupo y separarla atribuiría datos a quesos concretos sin evidencia |
| Casos con decisión explícita | según el caso | Ver la tabla siguiente |

### Equivalencias corregidas respecto a v1 (11 nombres originales)

| Nombre original | v1 | v2 | Justificación |
|---|---|---|---|
| Pecorino, pecorino, Pecorino (6 months) | Pecorino (queso concreto) | **Pecorino (generic)** — categoría | «Pecorino» designa una familia de quesos de oveja; la lista de DOP de la UE recoge varios pecorinos distintos (R_EU_LIST) |
| Chèvre (cottage cheese model), Chèvre (fresh goat cheese), chèvre | Chèvre (queso concreto) | **Goat cheese (generic)** | «Chèvre» significa «queso de cabra» |
| Turkish white cheese | queso aparte | **Beyaz peynir** | «Beyaz peynir» es «queso blanco» en turco: mismo queso |
| Mature Cheddar | Cheddar [mature] | **Cheddar (aged)** | «Mature» = «aged»; «Aged Cheddar» ya iba a Cheddar (aged) |
| Fresco, Fresco (Sonora, Mexico) | Fresco (queso concreto) | **Fresco (queso fresco, generic)** | «Queso fresco» es una categoría |
| fresh (perfil) | Fresh (queso concreto) | **Fresh (Tunick 2023 profile)** — categoría | «fresh» no es un nombre de queso |

### Decisiones explícitas sin cambio de valor

- **Parmesan** se mantiene separado de Parmigiano Reggiano. En la UE el nombre está reservado a la DOP, pero en EE. UU. existe una norma de identidad propia (21 CFR 133.165, curado ≥ 10 meses). Las fuentes del Excel no indican el origen de las muestras.
- **European** queda `no_verificado`: la etiqueta no identifica ningún queso y la evidencia no aporta texto.

### Resolución de «check in the table» (11 evidencias)

Se resolvió **evidencia por evidencia**, con el texto del PDF que el Excel copia en la columna *evidence (PDF text)*:

| Evidencia | Queso asignado | Base |
|---|---|---|
| EV_00054-1, EV_00065-1 | Cheddar; Emmental; Gorgonzola; Grana Padano; Pecorino (generic) | El texto cita el furaneol como odorante de esos cinco quesos |
| EV_00056-4, EV_00258-1 | Mozzarella (buffalo) | Abreviatura de tabla «Mozz WB» |
| EV_00066-1, EV_00220-1 | Farmhouse Cheddar | Abreviatura «Ched BF» (Cheddar British Farmhouse) |
| EV_00069-2, EV_00269-1 | Gruyère | El texto relaciona las notas de lipólisis con Gruyère |
| EV_00153-1, EV_00202-1, EV_00214-1 | — (`no_verificado`) | El texto (p. 18) no nombra ningún queso |

### Relaciones queso padre → variante

Cheddar (aged), Cheddar (low-fat), Farmhouse Cheddar y Goat Cheddar → **Cheddar**; Mozzarella (buffalo) → **Mozzarella**; Grana Trentino → **Grana Padano**. Esta última está verificada: el Trentingrana es una tipología del Grana Padano DOP (R_GP_ONAF).

### Otra corrección

Al unificar nombres, algunas evidencias quedaban con dos etiquetas originales que apuntan al mismo queso (p. ej. «Mozzarella (bovine)» y «Mozzarella (cow)»). En v2 se fusionan, para no contar dos veces la misma evidencia: la tabla plana pasa de 2.029 a 2.023 filas.

---

## 1.4 Clasificación tecnológica, país y DOP/IGP

### Clasificación usada

Las 13 categorías aprobadas más **`hard_pressed`** (pasta prensada dura no cocida). Esta se añadió porque los pliegos describen como «pasta prensada» quesos como Idiazabal, Majorero o Manchego, y el Cheddar no encajaba en `semi_hard` ni en `hard_cooked`.

| Familia | Quesos | Familia | Quesos |
|---|---|---|---|
| hard_pressed | 17 | grana_extra_hard | 4 |
| semi_hard | 9 | washed_rind_smear | 4 |
| brined | 6 | goat_lactic | 3 |
| other | 6 | soft_bloomy_rind | 2 |
| pasta_filata | 5 | swiss_type_eyes | 1 |
| fresh_acid_lactic | 4 | hard_cooked | 1 |
| blue | 4 | sin familia (`no_verificado`) | 2 |
| fresh_rennet | 4 | | |

Cuando una sola familia no basta, `secondary_technology` conserva las demás características: `cooked_curd`, `washed_rind`, `smoked`, `natural_whey_starter`, `rennet_paste_lamb_kid`, `vegetable_rennet`, `pit_ripened`, `stretched_curd`, etc. Por ejemplo, Gruyère es `hard_cooked` con `cooked_curd; washed_rind`.

### Criterio de los estados

- **`verificado_con_fuente` (20):** un pliego o norma describe la tecnología. Por ejemplo, Cabrales «queso de pasta azul»; Idiazabal y Majorero «pasta prensada»; Emmental «fermentación propiónica»; Mozzarella di Bufala y Ragusano «pasta filata»; Sainte-Maure «moho superficial»; Livarot «lavado con achiote»; Chihuahua «semiduro» según la norma mexicana.
- **`inferencia_documentada` (45):** clasificación deducida del perfil de producción del Excel (p. ej. *P. roqueforti* → `blue`) o de la definición del tipo de queso.
- **`no_verificado` (7):** Castelo Branco, Cremoso, Ġbejna, Malatya, Polish smoked cheese, Serpa y Turkish Motal. No se encontró una descripción tecnológica verificable. Malatya y Motal quedan sin familia; los otros cinco tienen una familia provisional basada en el Excel, marcada como no verificada.

### Decisiones difíciles

| Queso | Decisión | Motivo |
|---|---|---|
| Formaella | `hard_pressed` (no `pasta_filata`) | La fuente lo describe como queso prensado no cocido. El ahumado del perfil del Excel no se pudo verificar. |
| Gruyère | `hard_cooked` + `washed_rind` | Cuajada cocida (57 °C según el Excel) con flora de frotado |
| Roncal | `hard_pressed` | El pliego confirma oveja, leche cruda y ≥ 4 meses; «cooked; smoked» viene de una fuente del Excel y no se verificó |
| Gruyère y Emmental | DOP suiza | Existen también versiones francesas con IGP (French Gruyère, Emmental de Savoie…); las fuentes del Excel no indican el origen |
| Mozzarella (buffalo) | DOP solo si es Mozzarella di Bufala Campana | El Excel no dice si las muestras son DOP |
| Camembert | DOP «unknown» | La AOP Camembert de Normandie exige leche cruda, pero muchos Camembert no son AOP |

### País y DOP/IGP

32 confirmados con fuente (lista de la UE, pliegos y fichas oficiales); 18 por inferencia (p. ej. el país por el origen del tipo de queso, o una DOP cuyo vínculo con la muestra no es seguro); 22 sin verificar (quesos genéricos o sin registro encontrado).
