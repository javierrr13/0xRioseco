---
title: "PHP2Shell: análisis de impacto a escala (CVE-2026-109618 / 109619)"
type: post
category: data
date: 2026-10-26
status: published
summary: "Análisis de inteligencia de amenazas + ciencia de datos del evento PHP2Shell (oct. 2026): síntesis técnica de los dos CVE, datos cuantitativos de exposición y parcheo, especificación de 3 visualizaciones y proyección de riesgos del ecosistema PHP."
tags:
  - data-science
  - threat-intel
  - php
  - cve
  - php2shell
  - vulnerability-analysis
---

# PHP2Shell: análisis de impacto a escala

> [!abstract] Para quién es esto
> Análisis pensado para alguien **junior en pentesting y datos**: no se queda en el detalle del CVE,
> sino que intenta cuantificar el **impacto real a escala** y traducirlo a visualizaciones que un
> analista de datos usaría para comunicar riesgo. Todas las cifras están **citadas**; donde no hay
> dato fiable lo marco como `dato no encontrado` y digo qué fuente lo tendría.

> [!warning] Nota metodológica sobre las cifras
> Las fuentes públicas dan rangos muy dispares (de ~1,5 M a ~36,7 M de sistemas) porque miden
> **cosas distintas**: *hosts únicos* frente a *servicios* que anuncian versión, y distintos
> cortes temporales. Además, **las distros de Linux aplican *backports* sin cambiar el número de
> versión**, así que estimar "vulnerable" por el string de versión **sobrecuenta**. A lo largo del
> texto etiqueto cada cifra con su método y su fecha. Esta ambigüedad del *denominador* es, en sí
> misma, la primera lección de ciencia de datos de este caso.

---

## FASE 1 — Recopilación y síntesis de datos

### 1. Las dos vulnerabilidades

"PHP2Shell" es el nombre con el que se divulgó un par de fallos críticos **en el propio motor de
PHP** (no en el código de la aplicación), parcheados de urgencia el **21 de octubre de 2026**. Que
estén en el runtime implica que **un sitio puede ser vulnerable aunque su código sea seguro**.

| CVE | Tipo de fallo | Vector | Autenticación | CVSS v4.0 | Identificador |
|---|---|---|---|---|---|
| **CVE-2026-109618** | Corrupción de memoria durante el manejo de *out-of-memory* (OOM): una petición queda con datos a medio inicializar y el *shutdown* los trata como válidos | Red / petición web, **remoto** | **No** (pre-auth) | **9,2 (Crítica)** | GHSA-w8hw-w9fx-j79w |
| **CVE-2026-109619** | *Use-after-free* / estado global obsoleto: memoria liberada que una petición posterior **en el mismo worker** reutiliza. El aviso de PHP confirma también **divulgación de memoria** | Red / petición web, **remoto** | **No** (pre-auth) | **9,2 (Crítica)** | GHSA-6wmf-4rv5-p3rp |

Ambos permiten, en el peor caso, **ejecución remota de código no autenticada (RCE)** con los
privilegios del *worker* web.

**Alcance por tipo de despliegue** (Sophos, INCIBE-CERT): afecta a cualquier PHP que sirva peticiones
web — **mod_php (mayor riesgo)**, PHP-FPM, php-cgi, FrankenPHP y LiteSpeed.

**Versiones y parche:**

| Rama | Estado |
|---|---|
| 8.5 / 8.4 / 8.3 / 8.2 | ✅ Corregidas en **8.5.12, 8.4.27, 8.3.36, 8.2.35** (21-oct-2026) |
| 8.1 / 8.0 / 7.4 | ⚠️ **EOL** — solo *backports* en código fuente (GitHub), sin *release* oficial |
| 7.3 y anteriores | ⛔ **Sin corrección pública** — aislar y migrar |

> [!note] Discrepancia a vigilar
> Wikipedia lista "PHP 5.4 a 8.5" como afectadas, pero watchTowr señala que la afirmación "toda
> versión desde PHP 5" **no está confirmada por un aviso oficial del proveedor**. El *post* filtrado
> previo a la divulgación hablaba de CVSS 10.0; la nota **oficial de PHP es 9,2**. Lección: distinguir
> la cifra del *marketing/filtración* de la del *emisor autoritativo*.

### 2. Datos cuantitativos de exposición y parcheo

> [!warning] Cada fila mide algo distinto — no son comparables entre sí
> Léelas con su método y fecha, no como una única "verdad".

| Fuente | Fecha | Métrica | Cifra |
|---|---|---|---|
| **Palo Alto — Cortex Xpanse** | ~oct-2026 | Instancias expuestas *potencialmente* vulnerables (telemetría) | **> 22,6 M** |
| **Censys** (host-level) | 21-oct | Hosts expuestos a Internet / con versión PHP identificable / **sin parchear** | ~2,58 M / ~1,58 M / **~1,57 M** |
| **Censys** (service-level, por versión) | 22-oct | Servicios que anuncian versión PHP afectada | **~36,7 M** |
| **Censys** (service-level) | ~22-oct | Parcheados = 8,1 M ≈ **20 %** de 41,5 M servicios que revelan versión | **~80 % sin parchear** |
| **Censys** (reporte) | 23-oct | Servicios PHP aún vulnerables / % de sitios PHP vulnerables a 24 h | **> 34 M / 77 %** |
| **OX Security** (muestra menor) | +24 h | Instancias medibles **sin** versión parcheada | **~99,3 %** |
| **VulnCheck** | oct-2026 | Hosts PHP expuestos, casi todos vulnerables | **> 2,6 M** |

> [!tip] Dato llamativo que hay que matizar
> Titulares de prensa ("afecta al **70 % de la web**") confunden *"la web que corre PHP"* (estadística
> estructural de cuota de mercado, p. ej. W3Techs) con *"la web vulnerable"*. Son **denominadores
> distintos**: correr PHP ≠ estar sin parchear ≠ ser explotable en tu combinación OS/versión/servidor.

**Fuentes de CERT / organismos oficiales (prioritarias):**
- **CERT-EU** — *Security Advisory 2026-018*.
- **Centro Canadiense de Ciberseguridad** — *AL26-026* (indica **PoC disponible; sin explotación activa identificada** en su corte).
- **INCIBE-CERT** — aviso crítico. ⚠️ El número exacto aparece citado como **INCIBE-2026-762** (21-oct) y **INCIBE-2026-778** (24-oct) en prensa; `verificar la referencia oficial en incibe.es` (puede ser aviso + actualización).
- **NCSC-NL** — página operativa; **UK NCSC** emitió aviso urgente (vía CircleID).

> [!note] `dato no encontrado`
> No localicé en estas fuentes un **desglose por país ni por sector** de la población vulnerable.
> Fuente que lo tendría: **Shadowserver Dashboard** (estadísticas diarias por país/ASN) y los
> *dashboards* por geografía de **Censys**.

---

## FASE 2 — Análisis de impacto y visualizaciones

### 3. Tres visualizaciones para comunicar el riesgo

> [!tip] Especificación, no imágenes
> Para cada gráfico: tipo, variables por eje y la *historia* que cuenta.

**Gráfico 1 — Barras horizontales apiladas: "¿el problema es que no hay parche, o que no se aplica?"**
- **Tipo:** barras horizontales apiladas (100 %).
- **Ejes:** `Y` = rama de PHP (8.5, 8.4, 8.3, 8.2, 8.1-EOL, ≤8.0-EOL); `X` = nº de servicios (o %); **segmentos** = `parcheado` vs `vulnerable`.
- **Historia:** separa dos problemas distintos. La mayor parte de lo expuesto está en ramas **que sí
  tienen parche** pero no se ha aplicado (problema de *operación*), mientras una **cola en versiones
  EOL** no tiene *release* y solo saldrá migrando (problema *estructural*).
- **Fuente de datos:** Censys service-level por versión (22–23 oct).

**Gráfico 2 — Serie temporal: "la ventana de exposición de las primeras 72 h"**
- **Tipo:** líneas (multi-serie).
- **Ejes:** `X` = horas/fecha desde el parche (0 h = 21-oct … 72 h); `Y` = **% de servicios aún vulnerables**.
- **Series:** (a) población general de Internet; (b) **hosting gestionado** (p. ej. Loopia >90 % al día 1).
- **Historia:** la curva general es **casi plana** (a 24 h seguía ~77–99 % sin parchear según la
  métrica), mientras el hosting gestionado cae en picado → **quien gestiona parchea; quien no, queda expuesto**.
- **Fuente:** Censys/OX (general) + reportes de *hosters* (Loopia, otros).

**Gráfico 3 — Mapa coroplético (o treemap): "dónde se concentra el riesgo"**
- **Tipo:** mapa coroplético por país (alternativa sin geo: *treemap* por tipo de despliegue mod_php / PHP-FPM / FrankenPHP / LiteSpeed).
- **Ejes/encoding:** color = nº (o densidad) de servicios vulnerables; unidad = país **o** tipo de despliegue.
- **Historia:** el riesgo no es uniforme: se concentra en **mod_php** y en **hosting compartido / CMS**,
  y geográficamente donde más PHP heredado hay.
- **Fuente:** `dato por país no encontrado` → **Shadowserver Dashboard**; el desglose por despliegue sí
  es derivable de Sophos/Censys.

### 4. Tendencia de parcheo en las primeras 72 h

Con los *snapshots* disponibles (métricas **no homogéneas**, cada una etiquetada):

| Hora aprox. | Observación | Fuente |
|---|---|---|
| 0 h (21-oct) | ~1,57 M de ~1,58 M con versión identificable **sin parchear** (host-level) | Censys |
| +24 h | **~99,3 %** de instancias medibles aún sin versión parcheada (muestra menor) | OX Security |
| ~24–48 h (22-oct) | Parcheados ≈ **20 %** de 41,5 M servicios que revelan versión | Censys |
| ~72 h (23-oct) | **> 34 M** servicios aún vulnerables; **77 %** de sitios PHP vulnerables | Censys |

**Lectura:** la adopción del *fix* fue **lenta** en la población general durante las primeras 72 h
(del orden de un dígito a ~20 % parcheado según la métrica), con **enorme varianza por metodología**.
El contraste con *hosters* gestionados (>90 % en el día 1) sugiere que la velocidad depende sobre todo
de **quién opera el servidor**, no de la disponibilidad del parche.

> [!note] `dato no encontrado`
> No hay una **serie temporal limpia y homogénea** (mismo denominador, mismo método, por hora) en
> fuentes públicas a fecha de redacción. Fuente que lo tendría: **Shadowserver** (series diarias) o un
> *scan* longitudinal propio (ver recuadro siguiente).

> [!tip] Cómo obtendrías TUS propios datos (encaja con lo que ya sabes)
> Con tu stack actual: fingerprintear versión con **WhatWeb** / cabeceras `Server`/`X-Powered-By` y
> **Nmap** (`--script=http-php-version`), o consultar **Censys/Shodan** por `services.software` y
> versión. Guardar un *snapshot* diario → construyes tú mismo la **serie temporal de parcheo**
> (recordando el sesgo de *backports* que no cambian el string de versión).

---

## FASE 3 — Proyección de problemas futuros

### 5. Riesgos estructurales que revela el evento

- **Dependencia de versiones EOL.** La cola en 8.1/8.0/7.4 (sin *release*) y ≤7.3 (sin fix) no se
  resuelve con "actualizar": requiere **migrar**, que es caro y lento. El EOL deja de ser una fecha
  en un calendario y pasa a ser **deuda de seguridad medible**.
- **Fallo en el runtime, no en la app.** Rompe la intuición del dev de que "mi código es seguro".
  Amplía la superficie a **todo** lo que embebe PHP.
- **Entornos embebidos y de terceros.** INCIBE-CERT ya ligó el impacto a **QNAP, Synology, Mitel y
  Palo Alto Networks**: NAS, paneles de hosting, CMS y *appliances* donde el usuario **no controla**
  el ciclo de parcheo y depende del fabricante → ventana de exposición larga.
- **Velocidad de respuesta desigual.** La comunidad PHP sacó parche rápido, pero la **adopción** fue
  lenta salvo en hosting gestionado. El cuello de botella es **operativo**, no de disponibilidad.
- **Exploración previa a la divulgación.** Intentos observados el **17-oct** (Amazon TI), 4 días antes
  del parche → los *leaks* comprimen la ventana defensiva.

### 6. Dos predicciones y qué señales monitorizar

> [!warning] Predicciones (12–24 meses) — hipótesis, no certezas
> Formuladas para ser **falsables** y acompañadas de la señal de datos que las confirmaría o refutaría.

**Predicción 1 — Explotación masiva *tardía* contra la cola EOL y *appliances*.**
Cuando maduren PoCs fiables por combinación OS/versión/servidor, el grueso del daño no caerá sobre
servidores modernos (ya parcheados), sino sobre **NAS/CMS/paneles con PHP EOL** que nadie migró.
- *Señales a monitorizar:* entrada de CVE-2026-109618/109619 en la **KEV de CISA**; avisos de
  fabricantes (QNAP/Synology/Mitel…); *pulls* de exploits en GitHub/ExploitDB; honeypots y la
  **serie de Shadowserver** mostrando que el % vulnerable se estanca en una **meseta** (los fáciles
  ya parchearon; queda el núcleo duro EOL).

**Predicción 2 — Aparición de *variantes* de la misma clase de fallo (memory-safety en el runtime).**
El patrón (OOM mal gestionado, estado global reutilizado entre peticiones del mismo *worker*) sugiere
**más bugs de la misma familia**, posiblemente hallados con *fuzzing* asistido por IA como en este caso.
- *Señales a monitorizar:* nuevos **GHSA** sobre el motor de PHP (no sobre librerías); *commits* en
  `php-src` que toquen *request shutdown*, OOM o ciclo de vida de memoria; menciones en listas de PHP
  internals; tendencia de CVE por componente (motor vs extensiones) a lo largo del tiempo.

---

> [!abstract] Conclusión en una línea
> El dato clave de PHP2Shell no es el CVSS 9,2: es que **el parche estaba disponible el día 0 y aun así
> la mayoría seguía expuesta a las 72 h**. El riesgo, a escala, fue **operativo y estructural (EOL +
> embebidos)**, no de falta de solución.

## Fuentes

Prioridad a CERT y organismos oficiales:

- [CERT-EU — Security Advisory 2026-018](https://cert.europa.eu/publications/security-advisories/2026-018/)
- [Centro Canadiense de Ciberseguridad — AL26-026](https://www.cyber.gc.ca/en/alerts-advisories/al26-026-critical-vulnerabilities-impacting-php-cve-2026-109618-cve-2026-109619)
- [INCIBE-CERT (resumen en prensa, verificar referencia oficial en incibe.es)](https://www.moncloa.com/2026/10/24/incibe-cert-vulnerabilidades-php-criticas-3454627/)
- [Censys — Advisory y dashboards de exposición (live)](https://censys.com/advisory/cve-2026-109618-cve-2026-109619/)
- [Unit 42 (Palo Alto) — Threat Brief (telemetría Cortex Xpanse)](https://unit42.paloaltonetworks.com/cve-2026-109618-cve-2026-109619/)
- [OX Security — 24 h: 99,3 % sin parchear](https://www.ox.security/blog/php2shell-24-hours-in-99-3-of-measurable-php-instances-are-still-unpatched/)
- [Help Net Security — cronología y explotación previa](https://www.helpnetsecurity.com/2026/10/21/php2shell-php-vulnerabilities-patched-cve-2026-109618-cve-2026-109619/)
- [Sophos — Advisory (alcance por despliegue)](https://www.sophos.com/en-us/security-advisories/sophos-sa-20261021-php2shell)
- [watchTowr — FAQ (matices y discrepancias)](https://watchtowr.com/intelligence/php-cve-2026-109618-faq/)

> [!note] Verificación
> Este análisis se redactó el 2026-10-26 con información en evolución. Contrasta siempre las cifras
> con el *dashboard* vivo de Censys/Shadowserver y con el aviso oficial de INCIBE-CERT/CERT-EU antes de
> usarlas en un informe.

---
*— Javier Rioseco Rodríguez —*
