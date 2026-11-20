// Sin dependencias. Todo lo que hay aquí es mejora progresiva: la página se lee igual sin JS.
(function () {
  "use strict";

  // ── Tema ────────────────────────────────────────────────────────────────
  var root = document.documentElement;
  document.getElementById("theme").addEventListener("click", function () {
    var next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("tema", next); } catch (e) {}
  });

  // ── Idioma: recuerda la elección y conserva la sección en la que estabas ──
  Array.prototype.forEach.call(document.querySelectorAll(".lang a"), function (a) {
    a.addEventListener("click", function () {
      try { localStorage.setItem("idioma", a.dataset.lang); } catch (e) {}
      var here = document.querySelector(".bar__nav a.is-here");
      if (here) { a.href = a.getAttribute("href").split("#")[0] + here.getAttribute("href"); }
    });
  });

  // ── Linaje: grafo ⇄ proyectos ───────────────────────────────────────────
  var dag = document.querySelector(".dag");
  if (dag) {
    var nodes = Array.prototype.slice.call(dag.querySelectorAll(".dag__node"));
    var edges = Array.prototype.slice.call(dag.querySelectorAll(".dag__edge"));
    var projects = Array.prototype.slice.call(document.querySelectorAll(".proj"));
    var chips = Array.prototype.slice.call(document.querySelectorAll(".path li"));
    var has = function (el, slug) { return (" " + el.dataset.p + " ").indexOf(" " + slug + " ") > -1; };

    var clear = function () {
      dag.classList.remove("is-lit");
      nodes.concat(edges, projects, chips).forEach(function (el) { el.classList.remove("is-on", "is-dim"); });
    };

    // Un proyecto enciende su recorrido completo por el grafo.
    var lightProject = function (slug) {
      clear();
      dag.classList.add("is-lit");
      nodes.concat(edges).forEach(function (el) { el.classList.toggle("is-on", has(el, slug)); });
      projects.forEach(function (el) { el.classList.toggle("is-on", el.dataset.p === slug); });
    };

    // Una herramienta enciende sus vecinas directas y los proyectos que la usan.
    var lightTool = function (id) {
      clear();
      dag.classList.add("is-lit");
      var near = {};
      near[id] = true;
      edges.forEach(function (e) {
        var on = e.dataset.a === id || e.dataset.b === id;
        e.classList.toggle("is-on", on);
        if (on) { near[e.dataset.a] = near[e.dataset.b] = true; }
      });
      nodes.forEach(function (n) { n.classList.toggle("is-on", !!near[n.dataset.tool]); });
      chips.forEach(function (c) { c.classList.toggle("is-on", c.dataset.tool === id); });
      projects.forEach(function (p) {
        var uses = !!p.querySelector('.path li[data-tool="' + id + '"]');
        p.classList.toggle("is-on", uses);
        p.classList.toggle("is-dim", !uses);
      });
    };

    nodes.forEach(function (n) {
      var go = function () { lightTool(n.dataset.tool); };
      n.addEventListener("mouseenter", go);
      n.addEventListener("focus", go);
      n.addEventListener("mouseleave", clear);
      n.addEventListener("blur", clear);
    });
    projects.forEach(function (p) {
      p.addEventListener("mouseenter", function () { lightProject(p.dataset.p); });
      p.addEventListener("mouseleave", clear);
    });
    chips.forEach(function (c) {
      c.addEventListener("mouseenter", function (ev) { ev.stopPropagation(); lightTool(c.dataset.tool); });
      c.addEventListener("mouseleave", function () { lightProject(c.closest(".proj").dataset.p); });
    });
  }

  // ── Copiar correo ───────────────────────────────────────────────────────
  // navigator.clipboard solo existe en contextos seguros (https, localhost);
  // fuera de ellos se usa el método clásico con un textarea temporal.
  var copyText = function (text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) {}
      document.body.removeChild(area);
      if (ok) { resolve(); } else { reject(new Error("copy failed")); }
    });
  };

  Array.prototype.forEach.call(document.querySelectorAll("[data-copy]"), function (btn) {
    var label = btn.textContent;  // se guarda una vez: un doble clic no debe dejar "copiado" fijo
    var timer = null;
    btn.addEventListener("click", function () {
      copyText(btn.dataset.copy).then(function () {
        btn.textContent = btn.dataset.done || "copied";
        btn.classList.add("is-done");
        clearTimeout(timer);
        timer = setTimeout(function () { btn.textContent = label; btn.classList.remove("is-done"); }, 1400);
      }, function () {
        // Último recurso: abrir el cliente de correo.
        location.href = "mailto:" + btn.dataset.copy;
      });
    });
  });

  // ── Sección actual en la barra ──────────────────────────────────────────
  var links = {};
  Array.prototype.forEach.call(document.querySelectorAll(".bar__nav a"), function (a) {
    links[a.getAttribute("href").slice(1)] = a;
  });
  if ("IntersectionObserver" in window) {
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        Object.keys(links).forEach(function (id) { links[id].classList.toggle("is-here", id === entry.target.id); });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    Object.keys(links).forEach(function (id) {
      var section = document.getElementById(id);
      if (section) { spy.observe(section); }
    });
  }
})();
