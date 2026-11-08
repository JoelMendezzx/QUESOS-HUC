# Referencias verificadas — Fases 1, 2 y 3

Fuentes consultadas el **2026-11-08** durante la armonización. Cada clave (`R_…`) es la que aparece en la columna `referencia` de los archivos de `corrections/` y en [`scripts/harmonization_decisions.py`](scripts/harmonization_decisions.py).

**Cómo se consultó cada fuente**, para valorar su peso:

| Marca | Significado |
|---|---|
| 📄 **Leído** | Se leyó el documento (texto extraído completo o la sección indicada). |
| 🔎 **Extracto** | Se consultó a través de un buscador web; se usó el extracto que devuelve, con su URL. El documento completo **no** se leyó. |
| ⚠️ **Secundaria** | No es una fuente oficial ni científica (enciclopedia, web comercial, prensa). Las decisiones apoyadas solo en ella son `inferencia_documentada`. |

No se citan DOI, páginas ni artículos de pliegos que no se hayan visto. Cuando no se conoce la página, se indica la sección o el documento.

---

## 1. Léxicos sensoriales (Fase 3)

| Clave | Referencia | Consulta | Qué respalda | Ubicación |
|---|---|---|---|---|
| R_BER_ITA | ITA St-Hyacinthe / CINTECH AA. *Protocole d'évaluation organoleptique des fromages*. Reproduce y cita: **Bérodier, F. et al. (1997). *Guide d'évaluation olfacto-gustatif des fromages à pâte dure ou semi-dure*. Poligny, France.** <br>https://fromageschaput.wordpress.com/wp-content/uploads/2010/05/degustation-fromage.pdf | 📄 Leído | Familias (nivel 1), subfamilias (nivel 2) y descriptores (nivel 3) de la rueda de Bérodier usados en la ontología | p. 2–3, sección «4. Descripteurs d'arômes, par familles et sous familles» (nota 1 con la cita de Bérodier). En p. 2 el nombre de la subfamilia de «Champignon / Humus» no es legible. |
| R_BER_LWT | Bérodier, F., Lavanchy, P., Zannoni, M., Casals, J., Herrero, L., Adamo, C. (1997). *A guide to the sensory evaluation of smell, aroma and taste of hard and semi-hard cheeses*. LWT – Food Science and Technology, 30(7), 653–664. <br>http://agris.fao.org/agris-search/search.do?recordID=US201301477541 | 🔎 Extracto (registro AGRIS) | Cita bibliográfica de la versión publicada del guía | Registro bibliográfico (volumen, número y páginas). El texto completo no se consultó. |
| R_DRAKE | Cheese Science Toolkit, *Cheddar Lexicon*, «Adapted from Drake, M.A. et al. 2001». <br>https://www.cheesescience.org/cheddarlexicon.html | 📄 Leído | Los 32 términos de Drake usados como equivalencias (`drake_term`) | Tabla completa de la página |
| R_DRAKE_REC | Drake, M.A., McIngvale, S.C., Gerard, P.D., Cadwallader, K.R., Civille, G.V. (2001). *Development of a descriptive language for Cheddar cheese*. Journal of Food Science, 66(9), 1422–1427. <br>https://www.scilit.net/publications/bd4b8716980ea2c1110b5c2aaa4b9248 | 🔎 Extracto | Cita del artículo original (27 términos validados en 240 Cheddar) | Resumen |

## 2. Registros de protección (Fase 1.4)

| Clave | Referencia | Consulta | Qué respalda |
|---|---|---|---|
| R_EU_LIST | *List of European cheeses with protected geographical status* (Wikipedia, tabla basada en el registro de la UE). <br>https://en.wikipedia.org/wiki/List_of_European_cheeses_with_protected_geographical_status | 📄 Leído ⚠️ Secundaria | País, régimen (PDO/PGI) y año de 44 quesos. Las filas del Reino Unido (Stilton, West Country Farmhouse Cheddar) solo se vieron en un resumen, no textualmente. Quesos **ausentes** de la lista: San Simón da Costa, Queso Castellano, Pecorino Crotonese, Ġbejna (verificados por otras fuentes o sin verificar). |
| R_TURK | Repositorio de la Univ. de Sinop, *Geographically Marked Turkish Cheeses*. <br>https://acikerisim.sinop.edu.tr/items/4be64d17-e163-42fc-b509-bdf7a666401d/full | 🔎 Extracto | Indicación geográfica de Malatya (2022) y Van otlu peyniri (n.º 405); Motal solo aparece como queso tradicional |

## 3. Pliegos de condiciones y normas (Fases 1.4 y 2)

| Clave | Documento | Consulta | Qué respalda (ubicación) |
|---|---|---|---|
| R_GP_SPEC | Consorzio Grana Padano, *Specifications* (oct. 2022). https://www.granapadano.it/public/file/SpecificationsGBOct2022-50252.pdf | 🔎 Extracto | Leche de vaca cruda parcialmente desnatada por afloramiento; suero-cultivo natural; cuajo de ternero |
| R_GP_ONAF | ONAF, ficha *Grana Padano*. https://www.onaf.it/uploads/public/13739_grana-padano.pdf | 🔎 Extracto | Maduración mínima de 9 meses; leche cruda; el Trentingrana es una tipología del Grana Padano (sin lisozima) |
| R_GP_DAIRY | Dairy Science, *Grana Padano*. https://dairyscience.info/cheese-dairy/italian-cheeses/82-grana-padano.html | 🔎 Extracto ⚠️ | Maduración ≥ 270 días (confirmación adicional) |
| R_PR_SPEC | Consorzio Parmigiano Reggiano, *Disciplinare* (texto consolidado EN, 02/07/2025). https://backend.parmigianoreggiano.com/uploads/disciplinare_PR_EN_clean_02072025_55f8b10686.pdf | 🔎 Extracto | Maduración ≥ 12 meses desde el moldeado; leche cruda; suero-cultivo natural; solo cuajo de ternero; prohibidos los fermentos comerciales |
| R_GOR | Consorzio Gorgonzola, *Gorgonzola PDO: secrets of production and storage*. https://en.gorgonzola.com/news/gorgonzola-pdo-secrets-of-production-and-storage/ | 🔎 Extracto | Leche de vaca entera pasteurizada; dulce 50–150 días, picante 80–270 días |
| R_GRU | Interprofession du Gruyère, *Cahier des charges*. https://gruyere.com/fr/cahier-des-charges | 🔎 Extracto | Art. 4: mínimo 5 meses a la salida de las cavas; leche cruda (AOP suiza) |
| R_RAG_1995 | ONAF, *Disciplinare iniziale DOP Ragusano*. https://www.onaf.it/uploads/public/formaggi/2020_1-dop-ragusano-disciplinare-iniziale.pdf | 🔎 Extracto | Leche de vaca entera cruda; cuajo en pasta de cordero o cabrito; pasta filata |
| R_RAG_PRESS | Quotidiano di Ragusa, 15/10/2026. https://www.quotidianodiragusa.it/2026/10/15/cucina/ragusano-dop-disciplinare-stagionatura/ | 🔎 Extracto ⚠️ | Maduración mínima de 3 meses desde el moldeado |
| R_EMM_SITE | Emmentaler Switzerland, *Maturing cheese*. https://emmentaler.ch/en/maturing-cheese-the-secret-of-affinage | 🔎 Extracto | Emmentaler AOP: al menos 120 días |
| R_EMM_BLW | OFAG/BLW, modificación del pliego Emmentaler AOP (2025), anexo. https://www.blw.admin.ch/dam/fr/sd-web/QyDkjJEegx7D/Emmentaler%20%C3%84nderung%20PH%202025%20f_Anhang.pdf | 🔎 Extracto | Pasta dura de leche cruda con fermentación propiónica; leche no calentada por encima de 40 °C |
| R_MOZB | ARSIAL, *Mozzarella di Bufala Campana DOP*. https://www.arsial.it/wp-content/uploads/2025/06/MozzarellaBufalaCampanaDOP.pdf | 🔎 Extracto | Leche de búfala cruda o, opcionalmente, termizada o pasteurizada; suero-cultivo natural; cuajo de ternero; queso fresco |
| R_PROM | ONAF, ficha *Pecorino Romano*. https://www.onaf.it/uploads/public/11795_pecorino-romano.pdf | 🔎 Extracto | Leche de oveja cruda o termizada; cuajo de cordero en pasta; mínimo 5 meses (mesa) y 8 (rallar); salado en seco o en salmuera |
| R_PSIC | ONAF, *Disciplinare iniziale DOP Pecorino Siciliano*. https://www.onaf.it/uploads/public/formaggi/1872_1-dop-pecorino-siciliano-disciplinare-iniziale.pdf | 🔎 Extracto | Leche de oveja entera cruda; cuajo de cordero en pasta; ≥ 4 meses (tipo curado) |
| R_PCRO | ONAF / DOUE C 2014, *Pecorino Crotonese DOP* (CELEX 52014XC0702(02)). https://onaf.it/uploads/public/formaggi/19423_3-rich-dop-pecorino-crotonese-discipl-e-celex-52014xc0702-02-it-txt.pdf | 🔎 Extracto | DOP; semiduro 60–90 días; curado > 6 meses |
| R_CASTM | ONAF, ficha *Castelmagno*. https://www.onaf.it/uploads/public/20088_castelmagno.pdf | 🔎 Extracto | Leche de vaca con 5–20 % de oveja y/o cabra; maduración mínima de 60 días |
| R_FOSSA | Regione Marche, *Disciplinare Formaggio di Fossa di Sogliano DOP*. https://WWW.REGIONE.MARCHE.IT/Portals/0/Agricoltura/qualita/Formaggio_Fossa_Sogliano%20dop.pdf | 🔎 Extracto | Tipos ovino, vacuno o mixto (vaca ≤ 80 %, oveja ≥ 20 %); maduración mínima de 60 días; infossatura |
| R_MANCH | Junta de Castilla-La Mancha, *Pliego de condiciones DOP Queso Manchego* (2025). https://apliagri.castillalamancha.es/sites/default/files/2026-07/Pliego_Condiciones_DOP_Queso_Manchego_2025_0.pdf | 🔎 Extracto | Leche de oveja manchega cruda o pasteurizada; cuajo natural u otras enzimas autorizadas; maduración 30 días (≤ 1,5 kg) / 60 días (resto); máximo 2 años |
| R_MAJ | Foods & Wines from Spain, *Queso Majorero PDO* (información del Consejo Regulador). https://www.foodswinesfromspain.com/en/food/products/cheese/queso-majorero-pdo | 🔎 Extracto | Pasta prensada de cabra majorera (≤ 15 % de oveja); tierno 8–20 días, semicurado 20–60, curado > 60 |
| R_PALM | MAPA, *Pliego Queso Palmero* (2002). https://www.mapa.gob.es/images/es/queso-palmero_2002_07_11_tcm30-211309.pdf | 🔎 Extracto | Leche cruda exclusivamente de cabra palmera; cuajo artesanal de cabrito |
| R_FLOR | BOE 22/09/2006, *Pliego DOP Queso de Flor de Guía…*. https://boe.gob.es/boe/dias/2006/09/22/pdfs/B10284-10285.pdf | 🔎 Extracto | Leche: ≥ 60 % oveja, ≤ 10 % cabra, ≤ 40 % vaca; cuajo vegetal (*Cynara*). El dato de maduración aparece cortado en el extracto. |
| R_RONC | eAmbrosia, documento de la DOP Roncal. https://ec.europa.eu/geographical-indications-register/eambrosia-public-api/api/v1/attachments/59790 | 🔎 Extracto | Leche cruda de oveja; maduración mínima de 4 meses desde el salado; cuajo natural |
| R_IDIA | MAPA, *Pliego DOP Idiazabal*. https://www.mapa.gob.es/gl/alimentacion/temas/calidad-diferenciada/pliego_incluidas_modif_idi_v6-5-14_tcm7-326642_tcm37-78957.pdf | 🔎 Extracto | Leche cruda de oveja latxa y carranzana; pasta prensada; maduración ≥ 60 días |
| R_CABR | Principado de Asturias, *DOP Cabrales*. https://www.asturias.es/documents/4911212/4919355/DOP-cabrales.pdf/15d23072-1548-fd72-12c2-a7561f929c18 | 🔎 Extracto | Queso de pasta azul de leche cruda de vaca, oveja o cabra (o mezcla) |
| R_SSIM | Xunta de Galicia (AGACAL), *Ficha técnica DOP San Simón da Costa* (2023). https://agacal.xunta.gal/sites/default/files/calidade-alimentaria/queixos/Ficha-tecnica-DOP-S-Simon-da-Costa-2023.pdf | 🔎 Extracto | Leche de vaca cruda o pasteurizada; ahumado con abedul; 45 días (formato grande) / 30 días (bufón) |
| R_CAST | MAPA, *Pliego IGP Queso Castellano* (2020). https://mapa.gob.es/images/es/queso_castellano_2020_02_25_tcm30-535837.pdf | 🔎 Extracto | IGP; leche de oveja cruda o pasteurizada de Castilla y León; ≥ 30 días |
| R_CAM | INAO, *Cahier des charges AOP Camembert de Normandie*. https://extranet.inao.gouv.fr/fichier/CDCCamembertNormandieSansModification.pdf | 🔎 Extracto | La AOP designa un queso de leche cruda. No se encontró la maduración mínima. |
| R_LIV | INAO, *Cahier des charges AOP Livarot*. https://extranet.inao.gouv.fr/fichier/PNOCDCLivarot.pdf | 🔎 Extracto | Mínimo 3 semanas de maduración; lavado con agua y achiote |
| R_SMAU | INAO, *Document unique AOP Sainte-Maure de Touraine*. https://extranet.inao.gouv.fr/fichier/DUPNOSainteMauredeTouraine.pdf | 🔎 Extracto | Leche de cabra entera y cruda; moho superficial visible |
| R_WCFC | DEFRA, *Protected food name: West Country Farmhouse Cheddar*. https://assets.publishing.service.gov.uk/media/5fd3693f8fa8f54d59e8b750/pfn-west-country-farmhouse-cheddar.pdf | 🔎 Extracto | Leche pasteurizada o no; venta tras ≥ 9 meses. No especifica el cuajo. |
| R_GOUDA | Documento único IGP *Gouda Holland*. https://www.gob.mx/cms/uploads/attachment/file/245731/NL_Gouda_Holland.pdf | 🔎 Extracto | Leche pasteurizada ≥ 72 °C durante 15 s; queso semiduro madurado de forma natural |
| R_FORM | GOV.UK, *Formaella Arachovas Parnassou* (registro). https://www.gov.uk/protected-food-drink-names/phormaella-araxobas-parnassou-slash-formaella-arachovas-parnassou | 🔎 Extracto | Leche de oveja, de cabra o mezcla; queso prensado no cocido. El pliego no está publicado en ese registro. |
| R_CFR_PARM | 21 CFR Parte 133, Subparte B (§ 133.165 *Parmesan and reggiano cheese*). https://www.law.cornell.edu/cfr/text/21/part-133/subpart-B | 🔎 Extracto | Curado ≥ 10 meses (norma de identidad de EE. UU.) |
| R_CFR_CHED | 21 CFR § 133.113 *Cheddar cheese*. https://www.law.cornell.edu/cfr/text/21/133.113 | 🔎 Extracto | Leche cruda (curado ≥ 60 días a ≥ 35 °F) o pasteurizada |
| R_MINAS | SciELO, artículo sobre el queso Minas Frescal. https://www.scielo.br/j/rca/a/MZDt5CDnv66x63ThkT54twn/abstract/?lang=en | 🔎 Extracto | Definición legal: queso fresco de coagulación enzimática; obligación de leche pasteurizada (Res. GMC 145/96) |

## 4. Otras fuentes secundarias

| Clave | Referencia | Consulta | Qué respalda |
|---|---|---|---|
| R_CHIH | Revista Tecnociencia Chihuahua (UACH), artículo sobre el queso Chihuahua. https://revistascientificas.uach.mx/index.php/tecnociencia/article/download/654/691/2757 | 🔎 Extracto | Norma mexicana: queso semiduro de leche de vaca pasteurizada (origen menonita) |
| R_RUSHAN | FoodGuessr, *Rushan cheese*. https://www.foodguessr.com/food/rushan-cheese | 🔎 Extracto ⚠️ | Leche de vaca; coagulación ácida; cuajada estirada y secada en láminas |
| R_LIMB | Wikipedia, *Limburger*. https://en.wikipedia.org/wiki/Limburger | 🔎 Extracto ⚠️ | Queso de corteza lavada de leche de vaca (región de Herve) |
| R_PROOS | Epicure Foods, presentación comercial (Issuu, 2023). https://issuu.com/epicurefoods/docs/private_label_exclusive_presentation_2023/s/27379755 | 🔎 Extracto ⚠️ | Proosdij: tipo Gouda, cuajada lavada, cultivos de cepas mixtas |
| R_BOUTON | TasteAtlas, *Bouton de Culotte*. https://tasteatlas.com/bouton-de-culotte | 🔎 Extracto ⚠️ | Leche cruda de cabra del Mâconnais; ≥ 10 días antes del consumo |
| R_STILT | Wikipedia, *Stilton cheese*. https://EN.wikipedia.com/wiki/Blue_Stilton | 🔎 Extracto ⚠️ | DOP Blue Stilton de leche de vaca pasteurizada |
| R_MIHAL | Sultan of Bazaar, *Cheeses in Turkey*. https://sultanofbazaar.com/cheeses-in-turkey/ | 🔎 Extracto ⚠️ | Mihaliç: queso duro de oveja que se ralla |

## 5. Fuentes del Excel original

Cuando el valor procede del Excel (`origen_evidencia = fuente_citada_en_excel`), la referencia es la cita que ya figuraba en la hoja *Cheese Profiles* (p. ej. «Papademas 2018 (p. 213)», «McSweeney 2017 (ch. 15)»). Esas obras **no** se volvieron a consultar en esta armonización.

## Limitaciones de las fuentes

- La mayoría de los pliegos se consultaron mediante extractos de búsqueda, no leyendo el documento completo. Las cifras clave (maduración mínima, tratamiento de la leche) se tomaron solo cuando el extracto las citaba de forma explícita.
- La rueda de Bérodier se tomó de una reproducción (ITA St-Hyacinthe) que cita la obra original de 1997. La guía original (Poligny, 1997) no se consultó directamente.
- Algunos pliegos tienen versiones posteriores (p. ej. Pecorino Romano 2024, Formaggio di Fossa 2025) cuyo texto vigente no se pudo confirmar. Se indica en el criterio de cada decisión.
