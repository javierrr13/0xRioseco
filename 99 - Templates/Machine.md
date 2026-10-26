---
title: ""
machine: ""
platform: "HackTheBox"
difficulty: ""
os: ""
author_machine: ""
solved_by: "Javier Rioseco Rodriguez"
date:
entry_vector: ""
privesc_vector: ""
tags:
  - htb
  - machine
  - walkthrough
status: in-progress
---

# 🖥️ {{title}}

> [!abstract] Machine Information
> **Platform:**  
> **Difficulty:**  
> **OS:**  
> **IP:** `<TARGET_IP>`  
> **Status:** 🟡 In Progress

> [!note] Aviso
> Documento personal de práctica en ciberseguridad ofensiva. Uso educativo / portfolio.
> IPs, credenciales, tokens y flags se **redactan** (`<TARGET_IP>`, `<REDACTED>`), al corresponder a instancias de laboratorio efímeras.

---

## 🎯 Objectives

- [ ] Initial Access
- [ ] User
- [ ] Root / Administrator

---

# 🔎 01 — Reconnaissance

## Nmap

```bash
sudo nmap -Pn -p- --min-rate 5000 -T4 <TARGET_IP>
```

```text
# Pega aquí la salida relevante del escaneo
```

> **Superficie de ataque:** ¿qué servicios/puertos destacan y por qué?

---

# 🧩 02 — Enumeration

> Enumeración por servicio (web, SMB, DNS, etc.). Anota qué indicadores apuntan a cada vector.

```bash

```

---

# 🚪 03 — Initial Access

> Vector de entrada, prueba de concepto y shell obtenida.

```bash

```

> [!warning] Credenciales — redactadas
> - Usuario: ``
> - Contraseña: `<REDACTED>`

---

# 📈 04 — Privilege Escalation

> Enumeración post-explotación y escalada. ¿Qué permitió el salto de privilegios?

```bash

```

---

# 🔀 05 — Post Exploitation

> Persistencia, pivoting o acceso adicional (si aplica).

---

# 🏁 06 — Flags

| Flag       | Estado                            |
| ---------- | --------------------------------- |
| `user.txt` | ⬜ Pendiente                       |
| `root.txt` | ⬜ Pendiente                       |

> [!warning] Flags redactadas
> HTB pide no publicar flags en claro fuera de la plataforma.

---

# 📝 07 — Lessons Learned

- 🤔 **Por qué** funcionó el vector:
- ❌ **Por qué fallaron** otros enfoques:
- 🔍 **Indicadores** que apuntaban a la vulnerabilidad:
- 🛠️ **Herramientas** realmente útiles:
- 🚀 Qué haría **diferente** la próxima vez:

---
*— Javier Rioseco Rodriguez —*
