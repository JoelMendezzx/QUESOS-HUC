# Registros de armonización (Fases 1–3) — completados

Estos archivos son el **registro final** de las decisiones de armonización. Se generan con `python scripts/build_clean_db.py` a partir de [`scripts/harmonization_decisions.py`](../scripts/harmonization_decisions.py) y **no se editan a mano**: para cambiar una decisión, se modifica ese archivo y se regenera la base.

| Archivo | Hojas | Registros |
|---|---|---|
| `fase1_quesos_equivalencias.xlsx` | `equivalencias` · `check_in_the_table` · `padres_variantes` | 282 · 11 · 6 |
| `fase1_quesos_familia_tecnologica.xlsx` | `familias` · `definicion_familias` | 72 · 14 |
| `fase2_produccion_valores.xlsx` | `produccion` | 160 (40 quesos × 4 bloques) |
| `fase3_descriptores_mapeo.xlsx` | `descriptores` · `lexico` | 169 · 4 |
| `fases123.md` | Instrucción de la responsable del proyecto que define estas fases | — |

Cada fila tiene:
- **`estado`:** `verificado_con_fuente`, `inferencia_documentada` o `no_verificado`.
- **`origen_evidencia`**, donde aplica: fuente externa consultada, fuente citada en el Excel, criterio textual o sin evidencia.
- **`referencia`:** URL o cita.
- **`criterio`:** justificación de la decisión.

Las fuentes se describen en [`REFERENCIAS_VERIFICADAS.md`](../REFERENCIAS_VERIFICADAS.md) y la metodología en [`INFORME_FINAL_FASES_1_2_3.md`](../INFORME_FINAL_FASES_1_2_3.md).
