# Fase 3 — Armonización de descriptores sensoriales

**Archivo:** [`corrections/fase3_descriptores_mapeo.xlsx`](corrections/fase3_descriptores_mapeo.xlsx) (hojas `descriptores` y `lexico`).
**Columnas en la base:** `is_aroma_target`, `aroma_family`, `berodier_subfamily`, `aroma_terms`, `berodier_term`, `drake_term`, `harmonization_status` en [`clean/soporte/dim_descriptor.csv`](clean/soporte/dim_descriptor.csv), y las mismas en la tabla plana y en `fact_compound_odor.csv`.
**Fuentes:** [`REFERENCIAS_VERIFICADAS.md`](REFERENCIAS_VERIFICADAS.md)

## Resultado

| Indicador | Valor |
|---|---|
| Descriptores de aroma revisados | **169** |
| Notas de aroma válidas como objetivo | **161** |
| Excluidos del objetivo (no son notas) | **8** |
| `verificado_con_fuente` / `inferencia_documentada` / `no_verificado` | 61 / 108 / 0 |
| Con término literal de Bérodier equivalente | 93 |
| Con término equivalente de Drake (2001) | 62 |
| Con varios términos que conviene separar | 10 |
| Subfamilias (nivel 2) usadas | 51: 39 de Bérodier, 11 añadidas por el proyecto y 1 «[general]» |

---

## 1. Léxicos consultados y elección

| Léxico | Qué se verificó | Uso |
|---|---|---|
| **Bérodier et al. (1997)**, *Guide d'évaluation olfacto-gustatif des fromages à pâte dure ou semi-dure* (Poligny), versión publicada en LWT 30(7):653–664 | Estructura completa de 3 niveles, leída en la reproducción del ITA St-Hyacinthe (pp. 2–3), que cita la obra | **Léxico principal**: familias (nivel 1) y subfamilias (nivel 2) |
| **Drake et al. (2001)**, J. Food Sci. 66(9):1422–1427 | Los 32 términos del léxico de Cheddar (cheesescience.org, «Adapted from Drake et al. 2001») | **Complementario**: columna `drake_term`, para términos que Bérodier no cubre (p. ej. «Ketone (bleu)», «Cardboard», «Waxy») |
| American Cheese Society | No se encontró un vocabulario publicado y verificable | No se usó |

**Por qué Bérodier es el principal:** es la única fuente verificada con jerarquía de tres niveles específica de queso. **Limitación:** fue desarrollado para quesos de pasta dura y semidura, así que no cubre bien notas de quesos azules (cetonas), de quesos frescos ni ciertos defectos. Esos casos se completan con Drake o con subfamilias del proyecto, marcadas como `[proyecto]`.

**Lo que no se atribuye a Bérodier:** las subfamilias marcadas `[proyecto]` y la ubicación de descriptores que no aparecen literalmente en su lista. Además, el nombre de la subfamilia que agrupa «champignon» y «humus» no es legible en la fuente; se registra como «champignon–humus (sous-famille non lisible)».

## 2. Ontología (3 niveles)

**Nivel 1 — familias de Bérodier** (`aroma_family` en inglés · `berodier_family_fr` en francés):

| Familia | Subfamilias de Bérodier (nivel 2) usadas | Subfamilias `[proyecto]` | Descriptores |
|---|---|---|---|
| lactic · lactique | lactique frais, lactique chauffé, lactique acidifié, croûte de fromage | queso madurado | 15 |
| vegetal · végétal | herbe, légumes cuits à l'eau, alliacées, champignon–humus, boisé | verdura fresca, verdura fermentada | 25 |
| floral · floral | fleurs, miel | — | 8 |
| fruity · fruité | fruits secs, agrumes, fruits exotiques, fruits à noyau ou à pépins, fruits transformés, fruits fermentés | frutos rojos, fruta verde | 32 |
| toasted · torréfié | empyreumatique très fort / fort et torréfié / moyen / léger | — | 23 |
| animal · animal | fumier, viande, sueur, cuir – poil d'animaux, vache – troupeau | — | 17 |
| spicy · épicé | épices, épicé rafraîchissant | — | 5 |
| other · autres | moisi, savon, soufré, aigre, acétique, ammoniacal, rance, butyrique, putride, piquant au nez, propionique | graso, químico, oxidado, cetona (bleu), defecto, dulce de confitería | 36 |

**Nivel 3:** los términos de la fuente en inglés (`aroma_terms`, separados por «;»). La etiqueta original se conserva en `descriptor_label`.

## 3. Reglas de correspondencia

1. **`verificado_con_fuente`:** el descriptor coincide literalmente con un término o subfamilia de Bérodier («Rose» → rose; «Hay» → foin; «Vanilla» → vanillé), o es su traducción directa.
2. **`inferencia_documentada`:** no hay término literal; se ubica por analogía con un término de Bérodier («Peach» → fruits à noyau, como «abricot»), por la definición de Drake («Cooked» = leche cocida) o por la química del compuesto. El criterio se escribe en `harmonization_criterion`.
3. **Un descriptor = una familia de nivel 1.** Si el descriptor original mezcla notas de familias distintas, se marca `split_terms = True` y se lista cada término en el nivel 3.
4. No se fusionan descriptores con sensaciones distintas: «Coconut» y «Peach» comparten fila en la fuente, pero se marcan para separar.

### Correcciones respecto a la fuente y a supuestos previos

Ubicaciones que la rueda de Bérodier confirma y que corrigen la intuición o la familia original del Excel:

| Descriptor | Familia en el Excel | Ubicación en Bérodier |
|---|---|---|
| Honey | Sweet | **floral** (miel) |
| Vanilla | Sweet | **torréfié** (empyreumatique moyen) |
| Mint | Green/Herbal/Spicy | **épicé** (épicé rafraîchissant) |
| Nut, Almond, Walnut | Nutty | **fruité** (fruits secs) |
| Roasted nuts, Peanut | Nutty | **torréfié** (noisette / arachide grillée) |
| Musty/Moldy | Earthy/Fungal | **autres** (moisi) |
| Sour / Sour aromatic | Acidic | **autres** (aigre) |
| Butyric / Dirty sock | Body / Stable | **autres** (butyrique); la fuente la había marcado como no aroma |
| Swiss cheese | Character | **autres** (propionique) |

### Armonización de familias

- **«Fruit» y «Fruity»:** las dos familias del Excel quedan unificadas en **fruité**.
- Las 54 familias de la fuente («Toasted», «Malta», «Fatty Acid», «Caprine», etc.) se reducen a las **8 de Bérodier**. El token original se conserva en `family_l1_as_in_source`.

### Descriptores con varios términos (`split_terms = True`, 10)

Goat/Sheepy · Fruit/Pineapple/Banana · Coconut/Peach · Fecal/Putrid/**Rotten egg** · Cinnamon/Clove · Baked/Baked potato · Alliaceous/**meaty** · Earthy/**Musty** · Dusty/**Papery** · Potato/**Potato chips**.

Los otros 52 descriptores con «/» resultaron ser **sinónimos reales** (p. ej. «Butter / Butter-like / Buttery», «Rose / Rose flower / Rosy») y no se separan.

### Excluidos del objetivo predictivo (8)

| Descriptor | Motivo |
|---|---|
| Aromatic, Strong cheese, Overall dairy | Intensidad general |
| Fragrant, Sickening | Términos hedónicos |
| Ripe flavor, Seasoned flavor | Términos generales de maduración o condimento |
| Fresh | Categoría de maduración o humedad, no una nota |

En la tabla plana, `use_as_cheese_aroma_label` y `use_as_compound_aroma_label` ya excluyen estos términos.

## 4. Validación y consistencia

| Comprobación | Resultado |
|---|---|
| Los 169 descriptores tienen decisión y estado | OK |
| Toda familia de nivel 1 pertenece a Bérodier | OK |
| Todo término de Drake pertenece a los 32 verificados | OK |
| Ningún descriptor queda sin familia salvo los 8 excluidos | OK |

**Sin validación interjueces:** no hubo dos revisores humanos independientes, así que **no se calculó ni se presenta un kappa de Cohen**. La revisión documental la hizo un procedimiento automatizado (ver la metodología en el [informe final](INFORME_FINAL_FASES_1_2_3.md)). Para publicar se recomienda que un segundo experto revise de forma independiente una muestra (p. ej. las 108 inferencias) y se calcule entonces el acuerdo.

## 5. Familias candidatas para Machine Learning

Soporte con etiquetas queso–aroma (auditoría v2, nivel A):

| Familia | Quesos | Estudios primarios | Compuestos (modelo compuesto→familia) | ¿Candidata? |
|---|---|---|---|---|
| **fruity** | 26 | 26 | 69 | **Sí** |
| **vegetal** | 18 | 21 | 56 | **Sí** |
| **lactic** | 16 | 18 | 20 | **Sí** |
| **floral** | 18 | 17 | 26 | **Sí** (solo 4 % de confirmación primaria) |
| **toasted** | 15 | 16 | 29 | **Sí** (solo 6 % de confirmación primaria) |
| **animal** | 20 | 13 | 20 | **Sí** |
| other | 21 | 16 | 61 | **No como clase única**: agrupa notas químicamente distintas (graso, azufrado, rancio, químico…) y ninguna subfamilia llega a 10 quesos |
| spicy | 5 | 3 | 3 | **No**: soporte insuficiente |

**Lista definitiva: 6 familias** — fruity, vegetal, lactic, floral, toasted y animal.

**Candidata secundaria a evaluar:** el grupo lipolítico de «autres» (graso + rancio + butírico + jabonoso), si se demuestra que reúne soporte suficiente al combinarlo.
