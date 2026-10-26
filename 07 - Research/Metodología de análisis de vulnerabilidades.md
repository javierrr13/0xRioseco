---
title: "Metodología de análisis de vulnerabilidades"
type: post
category: research
date: 2026-10-26
status: published
summary: "Cómo abordo el estudio de una vulnerabilidad nueva: del aviso inicial al PoC reproducible, con énfasis en entender la causa raíz."
tags:
  - research
  - methodology
  - cve
  - vulnerability-analysis
---

# Metodología de análisis de vulnerabilidades

> [!abstract] Resumen
> Esta sección recoge mi trabajo de **investigación de vulnerabilidades**: análisis de CVEs,
> estudio de parches, pruebas de concepto y, cuando sea posible, hallazgos propios.
> Antes de publicar casos concretos, dejo aquí el **método** que sigo, para que cada
> análisis futuro parta de una base consistente.

---

## 1. Triaje inicial

Ante una vulnerabilidad nueva (un CVE recién publicado, un aviso o algo que encuentro
yo mismo), lo primero es responder cuatro preguntas:

- **¿Qué componente** afecta y en qué versiones?
- **¿Qué tipo** de fallo es? (memory corruption, injection, auth bypass, deserialización…)
- **¿Cuál es el vector**? (remoto/local, autenticado/no autenticado, pre/post-auth)
- **¿Qué impacto** real tiene? (RCE, LPE, info leak, DoS)

El objetivo de esta fase no es explotar nada todavía, sino decidir si merece la pena
invertir tiempo y con qué prioridad.

## 2. Reproducir el entorno vulnerable

Sin un entorno controlado no hay análisis serio. Normalmente:

- Levanto la versión **vulnerable** del software (contenedor, VM o build desde fuente).
- Fijo la versión exacta y anoto cómo reproducirla, para que el análisis sea **repetible**.
- Preparo instrumentación (logs, debugger, proxy) según el tipo de fallo.

## 3. Entender la causa raíz

Aquí es donde está el valor real. En lugar de copiar un exploit, busco el **porqué**:

- **Patch diffing**: comparar la versión vulnerable con la parcheada revela a menudo
  el fallo exacto y la condición que lo dispara.
- Lectura del código afectado y del flujo de datos hasta el punto vulnerable.
- Identificar la **precondición** que hace explotable el fallo y qué la rompe el parche.

## 4. Prueba de concepto

Un PoC mínimo y reproducible que demuestre el impacto, documentando:

- Entrada/estado necesarios para disparar la vulnerabilidad.
- Resultado observado (y por qué constituye el impacto declarado).
- Limitaciones y condiciones (versión, configuración, mitigaciones que lo frenan).

## 5. Documentación y divulgación responsable

- Escribo el análisis orientado a **enseñar la causa**, no solo el resultado.
- Si se trata de un hallazgo propio no publicado, se sigue **divulgación responsable**:
  reportar al proveedor y respetar los plazos antes de publicar detalles.

---

> [!note] Estado de la sección
> Nota de metodología inicial. Los análisis concretos de CVEs y PoCs se irán añadiendo aquí.

---
*— Javier Rioseco Rodríguez —*
