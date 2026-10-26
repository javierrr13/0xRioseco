# Convenciones del vault

Esta base de conocimiento es un vault de Obsidian versionado con Git. Para que
el conocimiento se mantenga **conectado, consistente y consultable** a medida que
crece, toda nota nueva debe seguir estas convenciones.

---

## 1. Estructura de carpetas

```
00 - Dashboard/     Panel principal (Home.md). Solo enlaza a notas que existen.
01 - Machines/      Máquinas resueltas: <OS>/<Máquina>/<Máquina>.md
02 - Challenges/    Retos por categoría (Crypto, Pwn, Web, ...)
03 - Academy/       Apuntes de HTB Academy
04 - Notes/         Teoría transversal (Enumeration, PrivEsc, AD, ...)
05 - Cheatsheets/   Referencias rápidas de comandos
06 - Writeups/      Versión pulida/porfolio de casos destacados
99 - Templates/     Plantillas de nota (Machine.md, ...)
```

- Cada máquina vive en su propia carpeta: `01 - Machines/Linux/Cap/Cap.md`.
- Las imágenes van en una subcarpeta `attachments/` junto a la nota.

---

## 2. Esquema de frontmatter (máquinas)

Toda nota de máquina **debe** empezar con este bloque YAML. Es el contrato que
permite que el plugin `bases` de Obsidian y las consultas tipo Dataview agreguen
las notas de forma fiable.

```yaml
---
title: "HTB <Máquina>"          # Título legible
machine: "<Máquina>"            # Nombre de la máquina
platform: "HackTheBox"          # HackTheBox | Business CTF 2026 | ...
difficulty: ""                  # Fácil | Media | Difícil | Insane
os: ""                          # Linux | Windows
author_machine: ""              # Creador de la máquina (opcional)
solved_by: "Javier Rioseco Rodriguez"
date:                           # YYYY-MM-DD
entry_vector: ""                # p.ej. "IDOR → PCAP → Credenciales FTP"
privesc_vector: ""              # p.ej. "Linux Capabilities (cap_setuid)"
tags:                           # usa el namespace htb/ y etiquetas de técnica
  - htb
  - walkthrough
status: in-progress             # in-progress | retired
---
```

### Reglas

- **Nombres de campo fijos.** No inventes variantes (`author`, `pwn_date`). Usa
  `solved_by` y `date`. Campos extra opcionales (p.ej. `xp`) se permiten, pero no
  sustituyen a los del esquema.
- `status` pasa a `retired` cuando la máquina se retira en HTB.
- Las etiquetas describen **técnicas** (`jwt`, `rbac`, `idor`, `linux-capabilities`)
  para poder navegar por el panel de tags.

---

## 3. Orden de secciones (máquinas)

Toda máquina arranca desde [`99 - Templates/Machine.md`](<99 - Templates/Machine.md>)
y respeta este ciclo (para que el conocimiento sea reutilizable):

```
Recon → Enumeration → Initial Access → Privilege Escalation
      → Post Exploitation → Flags → Lessons Learned
```

La sección **Lessons Learned** no es opcional: responde *por qué* funcionó el
vector, *por qué* fallaron otros enfoques y qué *indicadores* lo delataban.

---

## 4. Redacción de material sensible (obligatorio)

Este repo es **público**. Antes de commitear:

- **Flags:** nunca en claro. Usa `<REDACTED>` y el callout de aviso.
- **IPs de laboratorio:** sustituye por `<TARGET_IP>` (son efímeras).
- **Credenciales / tokens:** `<REDACTED>`.
- **Claves privadas:** nunca se incrustan; ya están en `.gitignore`.

El workflow `.github/workflows/validate.yml` revisa esto en cada push y **falla**
si detecta una flag `HTB{...}` en claro o una clave privada incrustada.

---

## 5. Enlaces

- En Obsidian usa wikilinks (`[[nota]]`).
- Antes de enlazar desde `Home.md` o el `README`, **comprueba que el destino
  existe**. Los enlaces rotos los caza el link-checker de CI (lychee).
- Para contenido aún no creado, usa una casilla `- [ ] Tema` en lugar de un
  enlace roto.
