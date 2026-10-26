---
title: "Nmap — Cheatsheet"
type: post
category: cheatsheet
date: 2026-10-26
status: published
summary: "Referencia rápida de Nmap: descubrimiento, escaneo de puertos, detección de servicios/versión, scripts NSE y evasión básica."
tags:
  - cheatsheet
  - nmap
  - recon
  - enumeration
---

# Nmap — Cheatsheet

> [!abstract] Resumen
> Comandos de Nmap que uso con más frecuencia en recon y enumeración, agrupados por fase.
> Sustituye `<TARGET>` por la IP o dominio objetivo.

---

## Descubrimiento de hosts

```bash
# Ping sweep de una red (sin escanear puertos)
nmap -sn 10.10.10.0/24

# Omitir descubrimiento (tratar el host como activo). Útil en HTB.
nmap -Pn <TARGET>
```

## Escaneo de puertos

```bash
# Todos los puertos TCP, rápido
sudo nmap -Pn -p- --min-rate 5000 -T4 <TARGET>

# Top 1000 (por defecto) con detección de servicio/versión y scripts por defecto
sudo nmap -Pn -sC -sV <TARGET>

# UDP (lento): limitar a los puertos de interés
sudo nmap -Pn -sU --top-ports 50 <TARGET>
```

## Detección de servicios, versión y SO

```bash
-sV            # versión de los servicios
-sC            # scripts NSE por defecto (= --script=default)
-O             # fingerprinting del sistema operativo
-A             # agresivo: -sV -sC -O --traceroute
--version-all  # máxima intensidad de detección de versión
```

## Scripts NSE

```bash
# Un script o categoría concreta
nmap --script=http-enum -p80,443 <TARGET>
nmap --script=vuln <TARGET>

# Ver ayuda/descripción de un script
nmap --script-help=smb-os-discovery
```

> [!tip] Flujo típico en una máquina
> 1. `nmap -Pn -p- --min-rate 5000 -T4 <TARGET>` → descubrir puertos abiertos.
> 2. `nmap -Pn -sC -sV -p<puertos> <TARGET>` → profundizar solo en esos puertos.

## Salida

```bash
-oN out.nmap     # formato normal
-oG out.gnmap    # formato "grepable"
-oX out.xml      # XML
-oA base         # los tres a la vez (base.nmap / .gnmap / .xml)
```

## Timing y evasión (básico)

```bash
-T0 … -T5        # de más sigiloso (0) a más agresivo (5)
--min-rate N     # mínimo de paquetes por segundo
-f               # fragmentar paquetes
--source-port 53 # fijar puerto de origen
-D RND:5         # señuelos (decoys)
```

> [!warning] Uso autorizado
> Escanea únicamente sistemas para los que tengas permiso explícito (HTB, labs propios, CTFs).

---
*— Javier Rioseco Rodríguez —*
