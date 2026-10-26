/* HTB Operations Center — lógica de la portada:
   roadmap clicable + buscador + filtros de máquinas.
   Los datos de máquinas llegan en window.MACHINES (inyectado por build.py). */
(function () {
  "use strict";

  var MACHINES = window.MACHINES || [];
  var grid = document.getElementById("machine-grid");
  if (!grid) return;

  // Mapa fase -> etiquetas/palabras clave relacionadas.
  var PHASE_TAGS = {
    recon:    ["nmap", "recon", "osint", "dns", "enumeration"],
    enum:     ["enumeration", "ffuf", "gobuster", "smb", "ldap"],
    web:      ["web", "idor", "jwt", "sqli", "xss", "lfi", "langflow", "http"],
    network:  ["network", "ftp", "pcap", "smb", "pivoting", "kubernetes"],
    access:   ["rce", "foothold", "shell", "ftp", "idor", "langflow", "cve"],
    privesc:  ["privesc", "linux-capabilities", "suid", "sudo", "kernel", "rbac"],
    post:     ["post-exploitation", "pivoting", "rbac", "kubernetes", "jwt", "lateral"],
    root:     ["root", "admin", "flag"],
    lessons:  ["portfolio", "lessons", "walkthrough"]
  };

  var state = { q: "", os: "all", phase: null };

  // --- construir tarjetas ---------------------------------------------
  function osColor(os) {
    os = (os || "").toLowerCase();
    if (os.indexOf("linux") > -1) return "var(--yellow)";
    if (os.indexOf("windows") > -1) return "var(--blue)";
    if (os.indexOf("active") > -1) return "var(--purple)";
    return "var(--green)";
  }
  function osIcon(os) {
    os = (os || "").toLowerCase();
    if (os.indexOf("linux") > -1) return "🐧";
    if (os.indexOf("windows") > -1) return "🪟";
    if (os.indexOf("active") > -1) return "🏢";
    return "🖥️";
  }
  function slugClass(s) { return (s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-"); }

  function cardHTML(m) {
    var tags = (m.tags || []).slice(0, 6).map(function (t) { return "<span>" + esc(t) + "</span>"; }).join("");
    var vec = "";
    if (m.entry_vector) vec += '<div class="vec"><b>Entrada</b>' + esc(m.entry_vector) + "</div>";
    if (m.privesc_vector) vec += '<div class="vec"><b>Escalada</b>' + esc(m.privesc_vector) + "</div>";
    return '' +
      '<article class="card" style="--os-color:' + osColor(m.os) + '">' +
        '<div class="top">' +
          '<h3><a href="' + esc(m.url) + '">' + esc(m.machine || m.title) + "</a></h3>" +
          '<span class="os">' + osIcon(m.os) + " " + esc(m.os || "") + "</span>" +
        "</div>" +
        '<div class="meta-row">' +
          '<span class="badge diff-' + slugClass(m.difficulty) + '">' + esc(m.difficulty || "?") + "</span>" +
          '<span class="badge">' + esc(m.platform || "HTB") + "</span>" +
          '<span class="badge st-' + slugClass(m.status) + '">' + esc(m.status || "") + "</span>" +
        "</div>" +
        vec +
        '<div class="tags">' + tags + "</div>" +
        '<a class="go" href="' + esc(m.url) + '">Leer writeup →</a>' +
      "</article>";
  }

  function matches(m) {
    if (state.os !== "all") {
      var os = (m.os || "").toLowerCase();
      if (os.indexOf(state.os) === -1) return false;
    }
    if (state.phase) {
      var want = PHASE_TAGS[state.phase] || [];
      var hay = ((m.tags || []).join(" ") + " " + (m.entry_vector || "") + " " +
                 (m.privesc_vector || "")).toLowerCase();
      if (!want.some(function (t) { return hay.indexOf(t) > -1; })) return false;
    }
    if (state.q) {
      var blob = (m.machine + " " + m.title + " " + (m.tags || []).join(" ") + " " +
                  (m.entry_vector || "") + " " + (m.privesc_vector || "") + " " +
                  (m.os || "") + " " + (m.difficulty || "")).toLowerCase();
      if (blob.indexOf(state.q.toLowerCase()) === -1) return false;
    }
    return true;
  }

  function render() {
    var list = MACHINES.filter(matches);
    if (!list.length) {
      grid.innerHTML = '<div class="empty">Sin resultados para este filtro. ' +
        '<a href="#" id="clearf">Limpiar filtros</a></div>';
      var c = document.getElementById("clearf");
      if (c) c.onclick = function (e) { e.preventDefault(); clearAll(); };
      return;
    }
    grid.innerHTML = list.map(cardHTML).join("");
  }

  function clearAll() {
    state = { q: "", os: "all", phase: null };
    var si = document.getElementById("search-input"); if (si) si.value = "";
    document.querySelectorAll(".chip").forEach(function (c) {
      c.classList.toggle("on", c.getAttribute("data-os") === "all");
    });
    document.querySelectorAll(".phase").forEach(function (p) { p.classList.remove("active"); });
    updatePhaseLabel();
    render();
  }

  function updatePhaseLabel() {
    var el = document.getElementById("phase-label");
    if (!el) return;
    if (state.phase) {
      var name = document.querySelector('.phase[data-phase="' + state.phase + '"] .ph-name');
      el.innerHTML = 'Filtrando por fase: <b>' + (name ? name.textContent : state.phase) +
        '</b> · <a href="#" id="unfilter">ver todas</a>';
      var u = document.getElementById("unfilter");
      if (u) u.onclick = function (e) { e.preventDefault(); setPhase(null); };
    } else {
      el.innerHTML = 'Pulsa una fase del roadmap para <b>filtrar las máquinas</b> que la tocan.';
    }
  }

  function setPhase(p) {
    state.phase = (state.phase === p) ? null : p;
    document.querySelectorAll(".phase").forEach(function (el) {
      el.classList.toggle("active", el.getAttribute("data-phase") === state.phase);
    });
    updatePhaseLabel();
    render();
    if (state.phase) {
      var sec = document.getElementById("machines");
      if (sec) sec.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // --- contar máquinas por fase (badge en cada nodo) ------------------
  function phaseCounts() {
    document.querySelectorAll(".phase").forEach(function (el) {
      var p = el.getAttribute("data-phase");
      var saved = state.phase; state.phase = p;
      var n = MACHINES.filter(function (m) {
        var want = PHASE_TAGS[p] || [];
        var hay = ((m.tags || []).join(" ") + " " + (m.entry_vector || "") + " " +
                   (m.privesc_vector || "")).toLowerCase();
        return want.some(function (t) { return hay.indexOf(t) > -1; });
      }).length;
      state.phase = saved;
      var badge = el.querySelector(".ph-count");
      if (badge) badge.textContent = n;
    });
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // --- wiring ----------------------------------------------------------
  document.querySelectorAll(".phase").forEach(function (el) {
    el.addEventListener("click", function () { setPhase(el.getAttribute("data-phase")); });
  });
  document.querySelectorAll(".chip[data-os]").forEach(function (c) {
    c.addEventListener("click", function () {
      state.os = c.getAttribute("data-os");
      document.querySelectorAll(".chip[data-os]").forEach(function (x) { x.classList.remove("on"); });
      c.classList.add("on");
      render();
    });
  });
  var si = document.getElementById("search-input");
  if (si) si.addEventListener("input", function () { state.q = si.value; render(); });

  phaseCounts();
  updatePhaseLabel();
  render();
})();
