(function () {
  "use strict";

  /* ---------- header scroll + mobile nav ---------- */
  var header = document.querySelector(".site-header");
  var navToggle = document.querySelector(".nav-toggle");
  var navLinks = document.querySelector(".nav-links");

  function onScroll() {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 8);
  }
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  if (navToggle && navLinks) {
    navToggle.addEventListener("click", function () {
      var open = navLinks.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    navLinks.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        navLinks.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* ---------- mark active nav link ---------- */
  var here = (location.pathname.split("/").pop() || "index.html");
  document.querySelectorAll(".nav-links a[data-page]").forEach(function (a) {
    if (a.getAttribute("data-page") === here) a.classList.add("active");
  });

  /* ---------- copy-to-clipboard for code cards ---------- */
  document.querySelectorAll("[data-copy-target]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = document.querySelector(btn.getAttribute("data-copy-target"));
      if (!target) return;
      var text = target.innerText;
      navigator.clipboard.writeText(text).then(function () {
        var label = btn.querySelector(".copy-label");
        var original = label ? label.textContent : null;
        if (label) label.textContent = "Copied!";
        setTimeout(function () {
          if (label && original !== null) label.textContent = original;
        }, 1600);
      });
    });
  });

  /* ---------- FAQ accordion ---------- */
  document.querySelectorAll(".faq-item").forEach(function (item) {
    var q = item.querySelector(".faq-question");
    if (!q) return;
    q.addEventListener("click", function () {
      var isOpen = item.classList.contains("is-open");
      item.classList.toggle("is-open", !isOpen);
      var answer = item.querySelector(".faq-answer");
      if (answer) {
        answer.style.maxHeight = !isOpen ? answer.scrollHeight + 40 + "px" : "";
      }
    });
  });

  /* ---------- recipes table: search + filter + expand ---------- */
  var recipeSearch = document.querySelector("#recipe-search");
  var recipeRows = document.querySelectorAll("tr.recipe-row");
  var filterPills = document.querySelectorAll(".filter-pill");
  var activeRegion = "all";

  function applyRecipeFilters() {
    var term = (recipeSearch && recipeSearch.value || "").trim().toLowerCase();
    recipeRows.forEach(function (row) {
      var text = row.textContent.toLowerCase();
      var region = row.getAttribute("data-region");
      var matchesTerm = !term || text.indexOf(term) !== -1;
      var matchesRegion = activeRegion === "all" || region === activeRegion;
      var show = matchesTerm && matchesRegion;
      row.classList.toggle("hidden-row", !show);
      var detail = row.nextElementSibling;
      if (detail && detail.classList.contains("recipe-detail")) {
        detail.classList.toggle("hidden-row", !show && true);
        if (!show) detail.classList.remove("is-open");
      }
    });
  }

  if (recipeSearch) recipeSearch.addEventListener("input", applyRecipeFilters);
  filterPills.forEach(function (pill) {
    pill.addEventListener("click", function () {
      filterPills.forEach(function (p) { p.classList.remove("active"); });
      pill.classList.add("active");
      activeRegion = pill.getAttribute("data-region");
      applyRecipeFilters();
    });
  });

  recipeRows.forEach(function (row) {
    row.addEventListener("click", function () {
      var detail = row.nextElementSibling;
      if (!detail || !detail.classList.contains("recipe-detail")) return;
      var willOpen = !detail.classList.contains("is-open");
      document.querySelectorAll(".recipe-detail.is-open").forEach(function (d) {
        d.classList.remove("is-open");
      });
      if (willOpen) detail.classList.add("is-open");
    });
  });

  /* ---------- docs scrollspy ---------- */
  var tocLinks = document.querySelectorAll(".docs-toc a");
  if (tocLinks.length) {
    var targets = [];
    tocLinks.forEach(function (link) {
      var id = link.getAttribute("href").replace("#", "");
      var el = document.getElementById(id);
      if (el) targets.push({ link: link, el: el });
    });

    function updateToc() {
      var pos = window.scrollY + 120;
      var current = null;
      targets.forEach(function (t) {
        if (t.el.offsetTop <= pos) current = t;
      });
      tocLinks.forEach(function (l) { l.classList.remove("active"); });
      if (current) current.link.classList.add("active");
    }
    updateToc();
    window.addEventListener("scroll", updateToc, { passive: true });
  }

  /* ---------- docs version selector ---------- */
  // Works the same on a root page (docs-site/*.html), an archived snapshot
  // (docs-site/archive/vX.Y.Z/*.html) and the archive listing page
  // (docs-site/archive/index.html) - each just declares how far "up" the
  // site root is via data-root-prefix on <body>, and an archived page also
  // declares its own version via data-archived-version. No path-sniffing.
  var versionSelect = document.getElementById("oceanval-version-select");
  if (versionSelect) {
    var page = location.pathname.split("/").pop() || "index.html";
    var rootPrefix = document.body.getAttribute("data-root-prefix") || "";
    var archivePrefix = rootPrefix + "archive/";
    var currentArchivedVersion = document.body.getAttribute("data-archived-version") || null;

    Promise.all([
      fetch("https://pypi.org/pypi/oceanval/json")
        .then(function (res) { return res.json(); })
        .catch(function () { return null; }),
      fetch(archivePrefix + "versions.json")
        .then(function (res) { return res.json(); })
        .catch(function () { return []; }),
    ]).then(function (results) {
      var pypiData = results[0];
      var archivedVersions = results[1] || [];
      var liveVersion = (pypiData && pypiData.info && pypiData.info.version)
        || currentArchivedVersion
        || archivedVersions[0];
      if (!liveVersion) return; // nothing usable came back - leave the placeholder

      versionSelect.innerHTML = "";

      var liveOpt = document.createElement("option");
      liveOpt.value = "current";
      liveOpt.textContent = "v" + liveVersion + " (current)";
      versionSelect.appendChild(liveOpt);

      var matchedArchived = false;
      archivedVersions.forEach(function (v) {
        if (v === liveVersion) return; // "current" already represents this one
        var opt = document.createElement("option");
        opt.value = v;
        opt.textContent = "v" + v;
        versionSelect.appendChild(opt);
        if (v === currentArchivedVersion) {
          opt.selected = true;
          matchedArchived = true;
        }
      });
      if (!matchedArchived) liveOpt.selected = true;

      versionSelect.disabled = false;
    });

    versionSelect.addEventListener("change", function () {
      var target = versionSelect.value;
      if (!target) return;
      location.href = target === "current"
        ? rootPrefix + page
        : archivePrefix + "v" + target + "/" + page;
    });
  }

  /* ---------- back to top ---------- */
  var backToTop = document.querySelector(".back-to-top");
  if (backToTop) {
    window.addEventListener("scroll", function () {
      backToTop.classList.toggle("is-visible", window.scrollY > 600);
    }, { passive: true });
    backToTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
})();
