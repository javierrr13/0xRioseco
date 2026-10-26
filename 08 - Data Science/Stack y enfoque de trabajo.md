---
title: "Stack y enfoque de trabajo en Data Science"
type: post
category: data
date: 2026-10-26
status: published
summary: "El stack, el flujo de trabajo y el tipo de proyectos de datos que iré documentando en esta sección."
tags:
  - data-science
  - python
  - methodology
---

# Stack y enfoque de trabajo en Data Science

> [!abstract] Resumen
> Esta sección documenta mis proyectos de **datos y machine learning**: análisis
> exploratorio, visualización, modelos y, cuando toque, cruce con seguridad
> (detección de anomalías, análisis de logs, threat intel). Antes de los casos
> concretos, dejo aquí el stack y el flujo que sigo.

---

## Stack

| Capa | Herramientas |
|------|--------------|
| Lenguaje | Python |
| Análisis | pandas, NumPy |
| Visualización | matplotlib, seaborn, plotly |
| Modelado | scikit-learn (y según el caso, frameworks de deep learning) |
| Entorno | Jupyter / notebooks + control de versiones en Git |

## Flujo de un proyecto

1. **Pregunta** — qué quiero responder o predecir, y cómo se mide el éxito.
2. **Datos** — obtención, limpieza y comprensión (valores nulos, sesgos, fugas).
3. **EDA** — análisis exploratorio y visualización para formar hipótesis.
4. **Modelado** — baseline sencillo primero, luego iterar; validación honesta.
5. **Comunicación** — conclusiones claras y reproducibles, no solo métricas.

## Cruce con seguridad

Donde más me interesa unir ambos mundos:

- Análisis de **logs** y tráfico para detección de anomalías.
- Procesado de datos de **threat intelligence**.
- Clasificación de muestras / features de artefactos.

---

> [!note] Estado de la sección
> Nota inicial de enfoque. Los proyectos y notebooks concretos se irán añadiendo aquí.

---
*— Javier Rioseco Rodríguez —*
