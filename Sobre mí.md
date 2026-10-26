---
name: "Javier Rioseco Rodríguez"
role: "Ciberseguridad ofensiva · Ciencia de Datos"
location: "Oviedo, Asturias (España)"
tagline: "Estudiante de Ciencia de Datos (UNIR) con especialización en Ciberseguridad (MEDAC). Pentesting, investigación y datos: aprender, documentar y conectar, no solo resolver la máquina."
email: ""            # opcional: añade tu correo si quieres mostrarlo públicamente
cv: ""               # opcional: ruta a un PDF público, p.ej. assets/cv/CV-Javier-Rioseco.pdf
links:
  GitHub: "https://github.com/javierrr13"
  LinkedIn: ""       # añade la URL de tu perfil
  HackTheBox: ""     # añade la URL de tu perfil HTB
highlights:
  - value: "30+"
    label: "Laboratorios resueltos en HackTheBox"
  - value: "3"
    label: "Formaciones: DAM, Ciberseguridad, Ciencia de Datos"
  - value: "2"
    label: "Proyectos propios en GitHub"
experience:
  - title: "Desarrollador web"
    org: "INDUROT"
    place: "Mieres, Asturias"
    period: "sep. 2024 – dic. 2024"
    items:
      - "Desarrollo de una herramienta para el control de ocupación de equipos."
      - "Mantenimiento, instalación y reparación de equipos en Active Directory."
      - "Atención de incidencias."
education:
  - title: "Grado en Ciencia de Datos"
    org: "UNIR"
    period: "sep. 2025 – actualidad"
  - title: "Curso de Especialización en Ciberseguridad en Entornos de las Tecnologías de la Información"
    org: "MEDAC"
    period: "oct. 2024 – jun. 2025"
  - title: "CFGS Desarrollo de Aplicaciones Multiplataforma"
    org: "IES Doctor Fleming, Oviedo"
    period: ""
projects:
  - name: "AutoRecon"
    url: "https://github.com/javierrr13/Autorecon"
    summary: "Framework de reconocimiento en Python que automatiza auditorías integrando Nmap, Subfinder y FFuF. Arquitectura modular con plugins, escaneo dual (rápido/completo) y generación automática de informes: reduce el tiempo de auditoría de horas a minutos mediante paralelización."
    tech: ["Python", "Nmap API", "Pydantic", "Click", "YAML", "Subfinder", "FFuF"]
  - name: "Geolocation Server"
    url: "https://github.com/javierrr13/GeolocationServer"
    summary: "Aplicación distribuida para gestionar dispositivos (p.ej. repartidores): permisos, ubicación en tiempo real y estado de los dispositivos. Arquitectura de microservicios orquestada con Docker."
    tech: ["Spring Boot", "MongoDB", "RabbitMQ", "WebSocket", "Docker"]
languages:
  - name: "Castellano"
    level: "Nativo"
  - name: "Inglés"
    level: "B1"
skills:
  Ofensiva / Web: ["Nmap", "Burp Suite", "ffuf", "Subfinder", "Gobuster", "WhatWeb"]
  Sistemas: ["GNU/Linux", "Active Directory", "PrivEsc Linux/Windows", "Docker", "Kubernetes"]
  Programación: ["Python", "Java", "Spring Boot", "JavaScript", "PHP", "C/C++", "HTML5/CSS3"]
  Data / ML: ["Python", "R", "pandas", "NumPy", "matplotlib"]
certs: []            # añade certificaciones cuando las tengas (p.ej. eJPT, CPTS, OSCP)
---

Soy Javier, de Oviedo. Me formé como desarrollador (DAM), me especialicé en
**ciberseguridad** y ahora estudio el **Grado en Ciencia de Datos**. Este sitio es mi
laboratorio público: documento máquinas, vulnerabilidades e investigación intentando
explicar siempre **por qué** funcionó algo, no solo que funcionó.

Me interesa el punto donde se cruzan **seguridad y datos**: automatizar el
reconocimiento (como en AutoRecon), medir el impacto real de una vulnerabilidad a
escala y entender cómo la IA está cambiando el trabajo de los equipos de defensa.

> [!tip] Para reclutadores y equipos de seguridad
> Cada entrada está pensada para demostrar **proceso de pensamiento**. Buenos puntos de
> partida: el writeup de **Fireflow** (RCE en Langflow → forja de JWT → abuso de RBAC en
> Kubernetes), el análisis de datos de **PHP2Shell** y el proyecto **AutoRecon**.
