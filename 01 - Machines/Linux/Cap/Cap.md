---
title: "HTB Cap"
machine: Cap
platform: "HackTheBox"
difficulty: Fácil
os: Linux
author_machine: ""
solved_by: Javier Rioseco Rodriguez
date:
entry_vector: "IDOR → PCAP → Credenciales FTP"
privesc_vector: "Linux Capabilities (cap_setuid)"
tags:
  - htb
  - ctf
  - walkthrough
  - idor
  - pcap
  - ftp
  - linux-capabilities
  - privesc
  - portfolio
status: retired
---

# HTB Cap — Write-up

> Hack The Box · Máquina **Cap** · Dificultad **Fácil** · Sistema **Linux**
> Autor: **Javier Rioseco Rodriguez**
> Vector de entrada: **IDOR → PCAP → Credenciales FTP** · Escalada: **Capabilities Linux (`cap_setuid`)**

> [!note] Aviso
> Documento personal de práctica en ciberseguridad ofensiva. Contiene el proceso de resolución de la máquina **Cap** (Hack The Box). Uso educativo / portfolio.
> Las credenciales y los valores de flag se han **redactado**, ya que corresponden a una instancia de laboratorio efímera y HTB pide no publicar flags en claro.

---

## Introducción

Hay máquinas de HTB que te reciben con una superficie de ataque enorme —diez puertos abiertos, tres dominios distintos, un Active Directory con cincuenta usuarios— y luego está Cap, que directamente te dice: "aquí tienes tres puertos, un panel de administración con capturas de red descargables, y buena suerte". A veces las máquinas más sencillas en apariencia son las que mejor enseñan un concepto muy concreto: en este caso, que un simple `id` en una URL puede filtrar información que nunca debería salir de un servidor.

Vamos a reconstruir el proceso completo, desde el escaneo inicial hasta el `root.txt`.

---

## 1. Reconocimiento inicial

Como manda la tradición, antes de tocar nada conviene saber qué hay delante. Se lanza un escaneo Nmap agresivo contra todos los puertos:

```bash
sudo nmap -Pn -p- --min-rate 5000 -T4 <TARGET_IP>
```

```text
Nmap scan report for <TARGET_IP>
Host is up (0.11s latency).
Not shown: 65532 closed tcp ports (reset)

PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  open  http
443/tcp open  https
```

Nada extraordinario a primera vista: SSH, HTTP y HTTPS. Tres puertos clásicos, lo que reduce bastante el abanico de vectores posibles y apunta claramente a que la vía de entrada va a estar en el servicio web.

> [!warning] Nota sobre la IP
> En las capturas posteriores (fichero `/etc/hosts` y el resto de la sesión) la máquina aparece registrada con una IP distinta a la del escaneo inicial. Es un detalle que llama la atención, pero es perfectamente coherente con el comportamiento habitual de HTB: las IPs se reasignan cada vez que se resetea o se vuelve a desplegar la instancia de la máquina. Lo dejo anotado por rigor, pero no afecta al resto del análisis. Las IPs concretas se han sustituido por `<TARGET_IP>` en este documento, al ser valores efímeros de laboratorio.

Con los tres puertos claros, el paso lógico es añadir el dominio de la máquina al `/etc/hosts` para poder trabajar cómodamente con el vhost en lugar de la IP pelada:

```bash
echo "<TARGET_IP> cap.htb" | sudo tee -a /etc/hosts
```

---

## 2. Enumeración web: un panel que enseña demasiado

Al visitar `http://cap.htb` nos encontramos con un dashboard de estilo "panel de seguridad de red", con una barra lateral que incluye:

- Dashboard
- Security Snapshot (5 Second PCAP + Analysis)
- IP Config
- Network Status

Interesante ya solo por el nombre: una aplicación que genera capturas de tráfico de 5 segundos y las deja disponibles para análisis. Es decir, estamos ante una herramienta cuya funcionalidad principal es exponer tráfico de red capturado en el propio servidor — un objetivo jugosísimo si se puede acceder a esos ficheros sin restricciones.

Al entrar en la sección de captura llegamos a una URL reveladora:

```text
http://cap.htb/data/0
```

La página muestra un resumen del análisis de esa captura concreta (número de paquetes, paquetes IP, TCP, UDP...) y un botón de *Download* para bajarse el `.pcap` correspondiente a ese identificador `0`. Y aquí está la primera hipótesis que salta a la vista: si el identificador de la captura es un simple número entero en la URL, ¿qué impide pedir `/data/1`, `/data/2`, etc.? Nada indica en la interfaz que el usuario (identificado como `Nathan` en la esquina superior derecha del panel) sea el único que puede generar o consultar snapshots — lo cual sugiere un clásico **IDOR** (*Insecure Direct Object Reference*): capturas de tráfico de otros usuarios o de otras sesiones accesibles simplemente cambiando un número en la URL, sin ningún control de autorización que verifique a quién pertenece cada captura.

La captura con ID `0` es, con toda probabilidad, una de las primeras que generó el sistema —posiblemente durante el proceso de configuración inicial o un login legítimo del administrador— y por tanto una candidata perfecta para contener tráfico "interesante" que en condiciones normales no debería ser visible para un usuario cualquiera.

Se descarga el `.pcap` de esa captura número `0` a través del botón *Download*.

---

## 3. Analizando la captura de tráfico

Con el `.pcap` en local, el siguiente paso obligado es volcarlo a un formato legible y empezar a buscar algo jugoso: credenciales, tokens de sesión, cualquier protocolo en claro. Dado que la aplicación se anuncia explícitamente como una herramienta de "PCAP + Analysis", cabe esperar que el tráfico capturado corresponda a actividad real de administración de la máquina — y en un entorno con FTP, SSH y HTTP como servicios visibles, FTP es el candidato obvio para viajar en texto plano.

Tras extraer/volcar el contenido del pcap a un fichero de texto (`trafico_1.txt`), se filtra buscando cualquier mención al usuario que aparecía logueado en el dashboard, `nathan`:

```bash
grep -A 10 "nathan" trafico_1.txt
```

Y ahí aparece la mina de oro, una sesión FTP completa capturada en claro:

```text
15:12:54.084642 IP <CLIENT>.54411 > <SERVER>.ftp: Flags [P.], seq 1:14, ack 21, win 4106, length 13: FTP: USER nathan
...
15:12:54.084772 IP <SERVER>.ftp > <CLIENT>.54411: Flags [P.], seq 21:55, ack 14, win 502, length 34: FTP: 331 Please specify the password.
...
15:12:55.383140 IP <CLIENT>.54411 > <SERVER>.ftp: Flags [P.], seq 14:36, ack 55, win 4106, length 22: FTP: PASS <REDACTED>
```

FTP es un protocolo sin cifrado por diseño, así que cualquiera capaz de capturar el tráfico entre el cliente y el servidor puede leer usuario y contraseña sin ningún esfuerzo adicional. La hipótesis del IDOR se confirma de la peor manera posible para la máquina objetivo: la propia aplicación web, pensada para "analizar seguridad de red", terminó exponiendo una captura que contenía credenciales de administración FTP en texto plano.

> [!warning] Credenciales — redactadas
> - Usuario: `nathan`
> - Contraseña: `<REDACTED>` (obtenida en claro del PCAP; se omite por ser una credencial de laboratorio efímera)

**Aprendizaje de esta fase:** nunca subestimes una funcionalidad de "descarga de logs/capturas/informes" en una aplicación web. Si el control de acceso a esos recursos no verifica correctamente la pertenencia del objeto al usuario autenticado, cualquier ID predecible se convierte en una puerta abierta a datos ajenos — en este caso, literalmente, a una contraseña.

---

## 4. Acceso inicial: entrando por FTP

Con las credenciales en mano, tocaba comprobar si además de para el servicio FTP esas credenciales servían también para acceder a la máquina. Se prueba conexión FTP directa contra la IP de la máquina:

```text
ftp <TARGET_IP>
Connected to <TARGET_IP>.
220 (vsFTPd 3.0.3)
Name (<TARGET_IP>:jrioseco): nathan
331 Please specify the password.
Password: <REDACTED>
230 Login successful.
```

Login correcto. El servidor identifica el software como `vsFTPd 3.0.3`. Un `ls` muestra un único fichero disponible:

```text
ftp> ls
-r-------- 1 1001 1001 33 Aug 13 14:43 user.txt
```

Se descarga directamente sin más rodeos:

```text
ftp> get user.txt
226 Transfer complete.
33 bytes received in 00:00 (0.30 KiB/s)
```

```bash
cat user.txt
```

> [!warning] Flag — redactada
> Valor de `user.txt` omitido; HTB pide no compartir flags en claro fuera de la plataforma.

Primera flag conseguida. Y de paso, un detalle interesante: los permisos del fichero (`-r--------`, propietario `1001:1001`) confirman que estas credenciales FTP corresponden efectivamente al usuario del sistema `nathan`, y que ese usuario tiene una cuenta real en la máquina, no solo un acceso FTP anónimo o enjaulado sin más.

---

## 5. Enumeración post-explotación y escalada de privilegios

Una vez dentro (tras acceder vía SSH/shell interactiva con las mismas credenciales), tocaba la fase de rigor en cualquier máquina Linux: buscar binarios con *capabilities* o permisos especiales que permitan escalar privilegios.

Las *capabilities* de Linux son un mecanismo que permite otorgar a un binario permisos específicos normalmente reservados a root (como poder cambiar de UID, abrir puertos *privileged*, etc.) sin necesidad de marcarlo como SUID completo. El problema es que, si se asignan capabilities demasiado potentes a binarios que a su vez pueden ejecutar código arbitrario —como un intérprete de Python—, el resultado es prácticamente equivalente a tener SUID root.

Se revisa el binario de Python del sistema:

```bash
getcap /usr/bin/python3.8
```

```text
/usr/bin/python3.8 = cap_setuid,cap_net_bind_service+eip
```

Ahí está el fallo de configuración: `python3.8` tiene asignada la capability `cap_setuid`, que le permite cambiar el UID del proceso en ejecución — exactamente lo necesario para saltar de un usuario normal a root, ya que Python puede invocar directamente `os.setuid(0)` sin ninguna restricción del kernel de por medio.

La explotación es tan directa como cabría esperar (técnica estándar y ampliamente documentada, ver [GTFOBins — python `cap_setuid`](https://gtfobins.github.io/gtfobins/python/#capabilities)):

```bash
/usr/bin/python3.8 -c 'import os; os.setuid(0); os.system("/bin/bash")'
```

```text
root@cap:~# ls
user.txt
root@cap:~# cd /root/
root@cap:/root# ls
root.txt snap
root@cap:/root# cat root.txt
```

> [!warning] Flag — redactada
> Valor de `root.txt` omitido por la misma razón que la flag de usuario.

Root conseguido. Shell interactiva como `root`, y la segunda flag en el bolsillo.

**Aprendizaje de esta fase:** las capabilities de Linux son una herramienta legítima para aplicar el principio de mínimo privilegio, pero cuando se asignan a intérpretes de propósito general (Python, Perl, Node...) el riesgo es máximo, porque cualquier función del lenguaje que toque el UID del proceso (`os.setuid`, `os.setgid`, etc.) queda disponible sin restricciones. Revisar `getcap -r /` debería ser un paso rutinario en cualquier enumeración de post-explotación.

---

## 6. Flags obtenidas

| Flag       | Estado                       |
| ---------- | ---------------------------- |
| `user.txt` | ✅ Obtenida (valor redactado) |
| `root.txt` | ✅ Obtenida (valor redactado) |

---

## Conclusiones

Cap es una máquina corta pero muy didáctica porque encadena dos fallos de naturaleza completamente distinta, ambos extremadamente comunes en entornos reales:

1. **Un control de acceso roto a nivel de aplicación (IDOR).** El panel web permitía acceder a capturas de tráfico ajenas simplemente iterando un identificador numérico en la URL, sin verificar que el recurso solicitado perteneciera al usuario autenticado. La consecuencia fue la exposición de credenciales que viajaban en claro por un protocolo inseguro (FTP).
2. **Una mala configuración de privilegios a nivel de sistema operativo (Linux capabilities).** Otorgar `cap_setuid` a un intérprete como `python3.8` anula por completo la separación de privilegios: cualquier usuario capaz de ejecutar ese binario puede convertirse en root con una sola línea de código.

Ninguna de las dos vulnerabilidades requiere herramientas sofisticadas ni exploits complejos — solo observación cuidadosa (¿por qué la URL tiene un ID numérico? ¿por qué este binario tiene capabilities?) y conocimiento de los mecanismos que hay detrás. Es, quizás, la mejor lección que deja esta máquina: muchas veces el camino más corto hacia root no pasa por un CVE con nombre propio, sino por preguntarse "¿y si cambio este número?" y "¿qué permisos tiene realmente este binario?".

---
*— Javier Rioseco Rodriguez —*
