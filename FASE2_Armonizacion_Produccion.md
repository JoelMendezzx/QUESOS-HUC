# Fase 2 — Armonización de variables de producción

**Archivo:** [`corrections/fase2_produccion_valores.xlsx`](corrections/fase2_produccion_valores.xlsx) (160 registros = 40 quesos × 4 bloques).
**Columnas en la base:** `spec_*` de [`clean/soporte/dim_cheese.csv`](clean/soporte/dim_cheese.csv) y `cheese_spec_*` de [`clean/modelo/ml_evidence_flat.csv`](clean/modelo/ml_evidence_flat.csv).
**Fuentes:** [`REFERENCIAS_VERIFICADAS.md`](REFERENCIAS_VERIFICADAS.md)

## Resultado

| Bloque | `verificado_con_fuente` | `inferencia_documentada` | `no_verificado` |
|---|---|---|---|
| Leche | 31 | 3 | 6 |
| Tratamiento térmico | 18 | 6 | 16 |
| Cuajo / cultivo | 25 | 3 | 12 |
| Maduración | 22 | 8 | 10 |
| **Total (160)** | **96** | **20** | **44** |

Origen de la evidencia de los 116 valores asignados:
- **50** salen de fuentes consultadas en esta fase: 34 verificados y 16 inferidos.
- **65** se conservan del Excel con la fuente que ya citaba: 62 verificados y 3 inferidos.
- **1** se deduce por criterio textual («queso fresco» = sin maduración).

**53** valores cambian o se completan respecto al Excel.

## Reglas de normalización

| Bloque | Formato | Ejemplos |
|---|---|---|
| Leche | Especie(s) en texto + indicadores `spec_milk_cow/sheep/goat/buffalo` | `cow`, `sheep_or_goat`, `cow (+5–20% sheep/goat)` |
| Tratamiento térmico | Valor controlado; las **alternativas** se conservan como tales | `raw`, `pasteurized`, `raw_or_pasteurized`, `raw_or_thermized` |
| Cuajo / cultivo | Texto con coagulante y cultivos | `calf rennet; natural whey culture` |
| Maduración | Días, `mín–máx`; máximo vacío = abierto | `270–` (≥ 9 meses), `50–270`, `0–0` (fresco) |

Conversión: 1 mes = 30 días; 1 semana = 7 días. Las unidades originales se conservan en `valor_excel`.

### Separación entre tipo de queso y muestra

- Todos los valores de esta fase son **`type_specification`**: describen el **tipo** de queso (pliego, norma o perfil general) y se guardan en columnas `spec_*`.
- Las variables de la **muestra** que da cada evidencia (`ctx_*` en `fact_evidence` y en la tabla plana) **no se modifican**.
- Ejemplos de por qué importa:
  - Grana Padano: el Excel daba «≥ 15 months» como contexto de las evidencias; el pliego dice ≥ 9 meses. Se guardan los dos, cada uno en su columna.
  - Roncal: el Excel da «7 weeks» (Tunick 2014); el pliego exige ≥ 4 meses. El primero describe otra muestra o etapa y no se sobrescribe.

## Valores obtenidos de pliegos y normas (principales)

| Queso | Bloque | Valor | Fuente |
|---|---|---|---|
| Grana Padano | maduración | ≥ 270 d | Ficha ONAF; pliego 2022 (leche cruda, suero-cultivo, cuajo de ternero) |
| Parmigiano Reggiano | maduración / cuajo | ≥ 360 d; cuajo de ternero + suero-cultivo natural | Pliego 2025 |
| Gorgonzola | tratamiento / maduración | pasteurizada; 50–270 d | Consorcio |
| Gruyère | maduración | ≥ 150 d | Pliego AOP (CH), art. 4 |
| Emmental | maduración | ≥ 120 d | Emmentaler AOP |
| Ragusano | maduración | ≥ 90 d | Resumen del pliego |
| Mozzarella (buffalo) | tratamiento / cuajo / maduración | cruda o termizada/pasteurizada; ternero + suero-cultivo; fresco | Pliego DOP |
| Manchego | tratamiento / maduración | cruda o pasteurizada; 30–730 d | Pliego 2025 |
| Pecorino Romano | tratamiento / maduración | cruda o termizada; ≥ 150 d | Ficha del pliego |
| Pecorino Siciliano | tratamiento | cruda | Pliego |
| Roncal | maduración | ≥ 120 d | Pliego (eAmbrosia) |
| Castelmagno | leche / maduración | vaca + 5–20 % oveja/cabra; ≥ 60 d | Ficha ONAF |
| Formaggio di Fossa | leche / maduración | oveja / vaca / mixto; ≥ 60 d | Pliego |
| Majorero | maduración | ≥ 8 d | Consejo Regulador |
| Livarot | maduración | ≥ 21 d | Pliego AOP |
| Sainte-Maure | tratamiento | cruda | Documento único AOP |
| Gouda | tratamiento | pasteurizada | IGP Gouda Holland |
| Minas Frescal | tratamiento / maduración | pasteurizada; fresco | Legislación brasileña |
| Cheddar (y variantes) | tratamiento | cruda o pasteurizada | 21 CFR 133.113 |

## Inferencias documentadas (20) — las más relevantes

- **Farmhouse Cheddar:** se asume que corresponde a la DOP West Country Farmhouse Cheddar (cruda o pasteurizada; ≥ 9 meses). El Excel no lo confirma.
- **Camembert:** `raw_or_pasteurized`. La AOP exige leche cruda, pero el Excel no dice si las muestras son AOP.
- **Grana Trentino:** se aplica el pliego del Grana Padano, del que es tipología.
- **Bouton de Culotte, Limburger, Milk fan, Proosdij:** solo hay fuentes secundarias (webs, enciclopedia).
- **Pecorino Crotonese:** ≥ 60 días (mínimo común entre el tipo semiduro y el curado).

## Valores desconocidos (44) y por qué

| Motivo | Quesos |
|---|---|
| **Categoría genérica:** no existe una especificación única | Pecorino (generic), Chèvre, Fresco, Cottage, Mozzarella (vaca) |
| **Queso de un estudio sin especificación de tipo** | Polish smoked cheese, Goat Cheddar |
| **Fuentes contradictorias** | Formaella (maduración), Majorero (tratamiento térmico), Limburger (maduración), Parmesan (identidad ambigua) |
| **Dato ausente en los extractos de pliego consultados** | Camembert (maduración), Flor de Guía (tratamiento y maduración: el extracto se corta), Palmero (maduración), Livarot (leche, tratamiento), Castelmagno (cuajo), Formaggio di Fossa (tratamiento, cuajo), Pecorino Crotonese (tratamiento, cuajo), Formaella (tratamiento, cuajo), Farmhouse Cheddar (cuajo) |
| **Sin ninguna fuente** | Proosdij (leche, tratamiento, maduración), Milk fan (tratamiento, maduración), Minas Frescal (especie de leche), Bouton de Culotte (coagulación) |

## Efecto en la base

| Indicador (quesos concretos) | v1 | v2 |
|---|---|---|
| Con los 4 bloques de producción conocidos | 12 | **20** |
| … con tratamiento sin ambigüedad | 7 | **13** |
| Con maduración conocida | 21 | **33** |
| Con tratamiento térmico conocido | 28 | **34** |

Ver la auditoría actualizada: [`Auditoria_viabilidad_predictiva.md`](Auditoria_viabilidad_predictiva.md) y [`clean/auditoria/q1_completitud_quesos_v2.csv`](clean/auditoria/q1_completitud_quesos_v2.csv).
