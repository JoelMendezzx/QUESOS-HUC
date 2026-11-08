# Fase 6 — Extracción de datos experimentales por muestra

**Tablas:** [`clean/muestras/`](clean/muestras/): `study.csv`, `sample.csv`, `sample_compound.csv`, `sample_descriptor.csv`, `data_dictionary_muestras.csv` y `resumen_fase6.json`.
**Código:**
- [`scripts/article_tables.py`](scripts/article_tables.py): convierte las tablas de cada artículo a CSV.
- [`scripts/phase6_extract.py`](scripts/phase6_extract.py): extracción.
- [`scripts/phase6_viability.py`](scripts/phase6_viability.py): análisis de viabilidad (resultados en [`results/fase6/`](results/fase6/)).

**Artículos descargados:** [`data_external/articles/`](data_external/articles/), con el HTML o XML original y sus tablas en CSV.

## Resultado

| Indicador | Valor real obtenido |
|---|---|
| Estudios extraídos | **7** |
| Muestras (filas de `sample.csv`) | **64** |
| Unidades de producción independientes | **30** |
| Muestras con producción documentada y compuestos medidos | **58** |
| Muestras con producción documentada y descriptores de aroma | **20** (3 estudios) |
| Mediciones de compuestos | 2.192 (1.600 enlazadas a un compuesto de la base; 341 no detecciones explícitas) |
| Registros de descriptores de aroma | 425 (419 con familia de Bérodier asignada) |

**Las 64 muestras no son 64 observaciones independientes.** La mayoría son series temporales de una misma producción. La cifra que cuenta para modelar la producción es **30 unidades de producción**, y de ellas solo 20 tienen datos de aroma.

## 1. Búsqueda bibliográfica

### Estudios prioritarios del plan

| Estudio | Acceso | Resultado |
|---|---|---|
| Moio & Addeo 1998 (*J. Dairy Res.* 65:317–333, Grana Padano) | De pago (Cambridge) | **No accesible.** Solo el resumen. |
| Moio, Piombino & Addeo 2000 (*J. Dairy Res.* 67:273–285, Gorgonzola) | De pago | **No accesible** |
| Qian & Reineccius 2002 (*J. Dairy Sci.* 85:1362–1369, DOI 10.3168/jds.S0022-0302(02)74202-1) | No está en Europe PMC ni en PMC | **No accesible**; el resumen no da datos por muestra |
| Milo & Reineccius 1997; Boscaini 2003; Suriyaphan 2001; Christensen 1995; Arora 1995 | De pago (*J. Agric. Food Chem.*, *J. Food Sci.*) | **No accesibles** |
| Larráyoz 2002 | Es *Journal of Sensory Studies* (Roncal) | **No accesible** |
| Chen 2022 | **Abierto** (PMC9532783) | **Extraído** |
| Jo et al. 2018 (*J. Dairy Sci.* 101:1967–1989, 36 Gouda de 3 meses a 5 años) | No abierto (Europe PMC: OA = N); la web de la revista devuelve 403 | **No accesible**. Sería la fuente más valiosa. |

### Ampliación a otros estudios de acceso abierto

Se buscaron en Europe PMC las fuentes primarias del Excel y estudios recientes. Se extrajeron los que tienen texto completo y tablas con datos por muestra:

| ID | Estudio | DOI | Diseño |
|---|---|---|---|
| DUE24A | Duensing, Hinrichs & Schieberle 2024, *J. Agric. Food Chem.* | 10.1021/acs.jafc.4c01814 | Gouda piloto de leche pasteurizada y cruda, 0–30 semanas |
| DUE24B | Duensing, Hinrichs & Schieberle 2024, *J. Agric. Food Chem.* | 10.1021/acs.jafc.4c01813 | Mismo Gouda a las 30 semanas, 2 lotes; GC-O (AEDA), OAV |
| IDI23 | Santamarina-García et al. 2023, *Curr. Res. Food Sci.* | 10.1016/j.crfs.2022.100425 | Idiazabal DOP de 4 productores, 1–120 días |
| DOP20 | Dopieralska et al. 2020, *Animals* 10:2103 | 10.3390/ani10112103 | Queso ahumado, 1–69 días de almacenamiento |
| NAT20 | Natrella et al. 2020, *Foods* 9:1446 | 10.3390/foods9101446 | Stracciatella con 4 conservantes, 1–16 días |
| TOR21 | Torri et al. 2021, *Foods* 10:2791 | 10.3390/foods10112791 | 6 Gorgonzola DOP (dulce/picante, 70–95 días, artesanal/industrial), RATA con consumidores |
| CHE22 | Chen et al. 2022, *Food Chem. X* | 10.1016/j.fochx.2022.100416 | 12 Gouda comerciales (jóvenes, medios, madurados), GC-O y OAV |

Revisados y **no extraídos**: Tintrop 2025 (PMC11951147), porque estudia la distribución espacial dentro de una rueda de queso, no variables de producción; y Andriot 2024 y Capozzi 2020, porque son quesos modelo o mascarpone sin diseño de producción comparable.

## 2. Criterios aplicados

- **Identificador único** por muestra (`sample_id` = estudio + código), con el código original del artículo.
- **Solo condiciones dadas por el artículo para sus muestras.** Ejemplos:
  - En DUE24 no se indica la especie de leche, así que queda vacía, aunque el Gouda sea normalmente de vaca.
  - En TOR21 no se dan el tratamiento ni la especie de cada muestra, aunque el pliego de Gorgonzola los fije. Esos valores del tipo de queso siguen en `dim_cheese` (`spec_*`) y **no se copian a la muestra**.
- **Métodos de aroma separados** (`evaluation_method`):
  - panel de consumidores RATA (TOR21);
  - GC-O con dilución (AEDA, factor FD) (DUE24B);
  - GC-O con frecuencia modificada (CHE22).

  Las «notas de olor» bibliográficas de los compuestos (IDI23, NAT20) **no** se registran como descriptores de la muestra: son propiedades de compuestos aislados.
- **No detecciones:** solo cuando la tabla dice «ND»/«Nd» (IDI23, DOP20) o «–» en GC-O y GC-MS a la vez (CHE22). Los «–» de tablas que solo listan valores por encima de un umbral (NAT20: OAV > 1 o > 1 μg/kg) **no** se cuentan como negativos y se anotan.
- **Unidades originales conservadas** (`unit_original`): μg/kg de materia seca, μg/kg, abundancia relativa respecto al patrón interno, % de área, OAV/OIR, factor FD, MF %. **No se convirtieron unidades** entre estudios porque no son comparables.
- **Fuente:** cada dato lleva la tabla o sección (`source_location`).
- **Réplicas** (`replicate_type`, `production_unit`, `independence_note`): por ejemplo, IDI23 da medias de 4 productores × duplicado; DUE24B tiene dos lotes independientes; DUE24A es una serie temporal de una misma producción.
- **Posible solapamiento:** las muestras de 30 semanas de DUE24A pueden ser el mismo queso que el lote 1 de DUE24B. Se marca en `possible_same_material_as`.

## 3. Variables de producción documentadas

| Estudio | Variable que cambia entre muestras | Fijas y documentadas |
|---|---|---|
| DUE24A | tratamiento térmico (crudo / 72–74 °C 30 s), maduración 0–210 días | 15 °C y 80–85 % HR; cuajo de laboratorio; cultivos definidos; salmuera 28 h |
| DUE24B | tratamiento térmico; lote | ídem, 210 días |
| IDI23 | maduración 1–120 días | leche cruda de oveja latxa; cultivo mesófilo Choozit MM 100; cuajo artesanal o comercial; 8–14 °C |
| DOP20 | almacenamiento 1–69 días | leche de vaca de razas autóctonas, pasteurizada 75 °C 15 s; *S. thermophilus*; ahumado; vacío |
| NAT20 | conservante, almacenamiento 1–16 días | nata UHT + mozzarella |
| TOR21 | estilo (dulce/picante), maduración 70–95 días, artesanal/industrial | Gorgonzola DOP |
| CHE22 | categoría de maduración (joven/medio/madurado) | — (la edad exacta está en una tabla suplementaria no consultada) |

**Variables que faltan** (de 64 muestras): especie de leche en 54, tratamiento térmico en 38, coagulante y cultivo en 38, días de maduración en 36. En CHE22, los días de maduración se sustituyen por una categoría.

## 4. Viabilidad actualizada

Archivos en [`results/fase6/`](results/fase6/).

### Modelo A — producción → compuestos

- **Maduración:** hay 3 series con suficientes tiempos (DUE24A pasteurizado, DUE24A crudo, IDI23).
  - **16 compuestos** se midieron en al menos 2 series, y **14 cambian en la misma dirección** con la maduración (correlación de Spearman). Por ejemplo, aumentan el ácido butanoico, el hexanoico y el acético, el butanoato y el hexanoato de etilo, y los ácidos ramificados; disminuye el butano-2,3-diona (diacetilo).
  - Las dos excepciones son el 3-metilbutanal y el 3-metil-1-butanol, que no tienen la misma tendencia en Gouda y en Idiazabal.
  - Ver `A1_tendencias_maduracion.csv`, `A2_coherencia_entre_series.csv` y `tendencias_maduracion.png`.
- **Pasteurización:** 8 pares emparejados crudo/pasteurizado (DUE24A y DUE24B).
  - La leche cruda da sistemáticamente más ácidos butanoico, pentanoico y hexanoico y más butanoato y hexanoato de etilo (8 de 8 pares; log2 medio de 0,8 a 3,4).
  - La pasteurizada da más butano-2,3-diona, 3-metilbutanal, ácido 2-metilbutanoico y 3-metil-1-butanol (0 de 8 pares a favor de la cruda).
  - Ver `A3_efecto_pasteurizacion.csv`.
- **Conclusión:** hay efectos **direccionales coherentes y reproducibles** de la maduración y la pasteurización sobre compuestos concretos, con los que se puede trabajar. Un modelo cuantitativo entre estudios sigue sin ser posible: cada estudio mide en una unidad distinta y solo 3 estudios tienen series de producción con compuestos.

### Modelo C — producción → aroma

- **Datos:** 20 muestras de 3 estudios, con 3 métodos de aroma distintos (RATA con consumidores, GC-O AEDA y GC-O MF). No se pueden reunir en un único conjunto de entrenamiento.
- **Resultados dentro de cada estudio** (exploratorios, n pequeño):
  - **CHE22:** la suma de frecuencias de GC-O de la familia **animal** (Kruskal-Wallis p = 0,007) y de la **fruity** (p = 0,023) aumenta de los Gouda jóvenes a los madurados; la **lactic** tiende a disminuir (p = 0,08). n = 4 por grupo.
  - **TOR21:** «Moldy» y «Ammonia» aumentan con los días de maduración (ρ = 0,90; p = 0,015; n = 6). Los Gorgonzola picantes tienen el doble de intensidad «moldy» que los dulces.
- **Conclusión:** sigue **sin ser viable un modelo supervisado** producción → aroma. Los efectos dentro de cada estudio son coherentes con la bioquímica (maduración → más notas animales, afrutadas y de moho), pero 20 muestras con tres métodos distintos no permiten generalizar.

## 5. Limitaciones

- La mayoría de los estudios prioritarios son de pago y no se pudieron consultar; **no se extrajo nada de ellos**. El estudio más útil para el objetivo, Jo et al. 2018 (36 Gouda con edad y panel descriptivo), no estaba accesible.
- Las tablas suplementarias (p. ej. la edad exacta de CHE22 o los compuestos volátiles de TOR21) no se consultaron.
- 25 nombres de compuestos (156 mediciones) no se pudieron identificar en PubChem. Son nombres con formato de índice CAS, con erratas («Phenilethyl alcohol») o con notas al pie pegadas. Se conservan con su nombre original y `compound_match = no_resuelto`.
- En DUE24B, la tabla de GC-O no indica el lote; se vinculó al lote 1 (análisis principal) con `sample_link_status = inferencia_documentada`.
