# Instrucción definitiva — Finalización de las Fases 1, 2 y 3 del proyecto QUESOS-HUC

Quiero que ejecutes y completes integralmente las Fases 1, 2 y 3 del proyecto **“Cheese Types, Production Variables and Sensory Descriptor Harmonization for Data-Driven Aroma Prediction”**.

No quiero únicamente propuestas, plantillas preparadas o recomendaciones. Quiero los archivos efectivamente revisados, corregidos, documentados e integrados en la base de datos.

## REQUISITOS OBLIGATORIOS

1. **Investiga por tu cuenta.** Busca los artículos científicos, documentos oficiales DOP/IGP, normas, léxicos sensoriales y demás fuentes necesarias. Consulta los documentos originales siempre que estén disponibles.

2. **No inventes absolutamente nada.** No inventes valores, fuentes, páginas, DOI, clasificaciones, resultados experimentales ni condiciones de producción. Si un dato no puede verificarse, registra `no_verificado` y justifica por qué.

3. **Completa todos los registros.** Cada fila debe quedar revisada y recibir una decisión documentada, incluso cuando el resultado sea que no existe evidencia suficiente para asignar un valor.

4. **Todas las decisiones deben estar justificadas.** Registra la fuente utilizada, la ubicación exacta de la evidencia y el criterio científico que fundamenta la decisión. Distingue confirmación directa, inferencia documentada y ausencia de evidencia.

5. **No me delegues las revisiones.** Realiza directamente todas las búsquedas, comparaciones, comprobaciones y correcciones documentales que puedas efectuar. No dejes un caso pendiente sin intentar resolverlo mediante investigación.

6. **No marques las decisiones como “revisión IA pendiente de validación”.** Utiliza estados técnicos como `verificado_con_fuente`, `inferencia_documentada` o `no_verificado`. Documenta con transparencia el procedimiento automatizado en la metodología del proyecto.

7. **Conserva la trazabilidad.** No modifiques el Excel original. Trabaja sobre las plantillas de `corrections/` y utiliza los scripts reproducibles del proyecto.

---

## FASE 1 — Armonización completa de tipos de queso

Completa los siguientes archivos:

### `fase1_quesos_equivalencias.xlsx` — 282 filas

- Verifica individualmente las 282 equivalencias.
- Corrige errores de nomenclatura, ortografía y normalización.
- Distingue sinónimos auténticos de variantes tecnológicas.
- Comprueba las relaciones entre quesos padres y variantes.
- Resuelve los casos `check in the table`, `multi_cheese` y `unresolved` consultando las fuentes originales.
- Registra la justificación y la referencia correspondiente para cada corrección.

### `fase1_quesos_familia_tecnologica.xlsx` — 72 filas

- Investiga y clasifica los 72 quesos.
- Utiliza una clasificación tecnológica consistente y científicamente fundamentada.
- Verifica los países de origen y las denominaciones DOP/IGP.
- Conserva las características tecnológicas secundarias cuando una sola familia no represente adecuadamente el queso.
- Justifica las clasificaciones utilizando literatura científica o documentación oficial.

**Resultado exigido:** 282 equivalencias revisadas y 72 clasificaciones evaluadas, con decisiones registradas y todas las asignaciones respaldadas por fuentes verificables.

---

## FASE 2 — Armonización completa de variables de producción

Completa `fase2_produccion_valores.xlsx`, que contiene 160 registros correspondientes a 40 quesos y cuatro bloques de producción.

Investiga y documenta:

- Especie de leche y mezclas.
- Tratamiento térmico.
- Cuajo, coagulantes y cultivos.
- Tiempo y condiciones de maduración.

Para cada valor:

- Verifica lo existente o busca la información faltante.
- Registra la fuente científica u oficial.
- Indica la página, tabla o sección.
- Conserva las unidades originales y estandarizadas.
- Distingue valores exactos, intervalos, alternativas e información desconocida.
- Separa claramente `type_specification` de `sample`.
- Nunca atribuyas a una muestra experimental un valor que solo describe las características generales del queso.

**Resultado exigido:** los 160 registros revisados, con todos los valores verificables completados y cada imposibilidad de verificación explicada.

---

## FASE 3 — Armonización completa de descriptores sensoriales

Completa `fase3_descriptores_mapeo.xlsx`, con sus 169 descriptores de aroma.

### Investigación del léxico

- Investiga Bérodier et al. (1997), Drake et al. (2001) y otros léxicos científicos pertinentes.
- Verifica sus clasificaciones originales en las fuentes disponibles.
- Selecciona y justifica el léxico principal y los complementarios.
- No atribuyas a un autor categorías que no aparezcan en su publicación.

### Construcción de la ontología

- Revisa individualmente los 169 descriptores.
- Organízalos en tres niveles: familia, subfamilia y descriptor.
- Distingue sinónimos reales de términos sensoriales diferentes.
- Resuelve los 62 descriptores que contienen múltiples términos.
- Armoniza familias como `Fruit` y `Fruity` cuando exista justificación.
- Identifica y excluye del objetivo predictivo los términos que no representan notas aromáticas.
- Conserva la terminología original y registra cada correspondencia con el vocabulario elegido.
- Evita fusionar descriptores que representen sensaciones distintas.

### Validación

- Comprueba la coherencia y consistencia de toda la ontología.
- Registra conflictos y decisiones de armonización.
- No simules dos revisores humanos independientes.
- Si no existen dos revisiones humanas independientes, no presentes un kappa de Cohen como validación realizada.
- Deja documentada esa limitación sin impedir que se complete la revisión documental y la ontología.

**Resultado exigido:** los 169 descriptores revisados, una ontología de tres niveles documentada, un mapeo trazable y una lista definitiva de familias aromáticas candidatas para Machine Learning.

---

## DOCUMENTACIÓN OBLIGATORIA EN MARKDOWN

Además de completar los Excel, crea o actualiza estos documentos:

### `FASE1_Armonizacion_Quesos.md`

Explica la metodología de identificación, las equivalencias corregidas, las variantes conservadas, la clasificación tecnológica, las fuentes utilizadas y las decisiones difíciles.

### `FASE2_Armonizacion_Produccion.md`

Documenta las variables, las reglas de normalización, las fuentes científicas, las condiciones de fabricación y los valores desconocidos.

### `FASE3_Armonizacion_Descriptores.md`

Documenta los léxicos consultados, la ontología propuesta, las reglas de correspondencia, los sinónimos, las fusiones, los descriptores excluidos y la justificación científica de cada decisión.

### `REFERENCIAS_VERIFICADAS.md`

Incluye todas las referencias utilizadas, DOI o URL verificables, y la localización exacta de la información que respalda las decisiones.

### `INFORME_FINAL_FASES_1_2_3.md`

Presenta:

- Resumen de las tres fases.
- Número de registros revisados y corregidos.
- Número de registros confirmados directamente.
- Número de inferencias documentadas.
- Número de casos que permanecen sin verificar.
- Principales decisiones metodológicas.
- Limitaciones científicas.
- Resultados de las comprobaciones de consistencia.
- Estado real de preparación para las siguientes fases.

---

## INTEGRACIÓN Y CONTROL DE CALIDAD

Una vez completadas las revisiones:

1. Incorpora las correcciones a los scripts de generación de la base.
2. Regenera los archivos CSV sin modificar el Excel original.
3. Comprueba que las claves y relaciones entre tablas sean consistentes.
4. Verifica que no se hayan perdido registros ni introducido duplicados incorrectos.
5. Ejecuta nuevamente la auditoría de viabilidad predictiva.
6. Actualiza el diccionario de datos.
7. Conserva la versión anterior `v1-clean`.
8. Genera la versión `v2-harmonized` únicamente cuando se hayan superado las comprobaciones de calidad.
9. Actualiza la bitácora con los cambios realizados.

## CRITERIO DE FINALIZACIÓN

No consideres completada ninguna fase simplemente porque sus plantillas tengan todas las celdas rellenadas.

Una fase estará terminada cuando todos sus registros hayan sido evaluados, las decisiones verificables estén sustentadas, las incertidumbres estén documentadas y los archivos sean consistentes y reproducibles.

No sustituyas la falta de evidencia por suposiciones para alcanzar un porcentaje artificial de completitud.

**Quiero recibir las Fases 1, 2 y 3 efectivamente ejecutadas, con archivos actualizados, documentación científica, referencias verificadas y una base armonizada reproducible. Prioriza la exactitud y trazabilidad sobre la apariencia de que todo está completo.**