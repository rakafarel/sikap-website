/* Menu sidebar geser untuk layar kecil */
(function () {
  var body = document.body;
  var toggle = document.getElementById("menuToggle");
  var backdrop = document.getElementById("sidebarBackdrop");
  if (!toggle || !backdrop) return;

  function setOpen(open) {
    body.classList.toggle("sidebar-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  toggle.addEventListener("click", function () { setOpen(true); });
  backdrop.addEventListener("click", function () { setOpen(false); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") setOpen(false); });

  // Tutup menu setelah salah satu tautan diklik
  document.querySelectorAll(".sidebar a").forEach(function (a) {
    a.addEventListener("click", function () { setOpen(false); });
  });

  // Kalau layar dilebarkan (misal HP diputar), pastikan menu tertutup
  window.matchMedia("(min-width: 992px)").addEventListener("change", function (e) {
    if (e.matches) setOpen(false);
  });
})();

/* ===== Toast / pop up notifikasi ===== */
(function () {
  var ICONS = {
    success: "bi-check-circle-fill", danger: "bi-x-circle-fill",
    warning: "bi-exclamation-triangle-fill", info: "bi-info-circle-fill"
  };
  var stack;

  function getStack() {
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      stack.setAttribute("aria-live", "polite");
      document.body.appendChild(stack);
    }
    return stack;
  }

  function dismiss(el) {
    if (!el.parentNode) return;
    el.classList.add("out");
    setTimeout(function () { el.remove(); }, 300);
  }

  window.showToast = function (message, category, ms) {
    category = ICONS[category] ? category : "info";
    var box = getStack();

    // pesan yang sama tidak ditumpuk
    box.querySelectorAll(".toast-item").forEach(function (t) {
      if (t.dataset.msg === message) t.remove();
    });
    // maksimal 3 pesan tampil bersamaan
    while (box.children.length >= 3) box.firstElementChild.remove();

    var el = document.createElement("div");
    el.className = "toast-item toast-" + category;
    el.dataset.msg = message;
    el.setAttribute("role", "alert");
    el.innerHTML = '<i class="bi ' + ICONS[category] + '"></i><span class="toast-text"></span>' +
                   '<button type="button" aria-label="Tutup">&times;</button>';
    el.querySelector(".toast-text").textContent = message;
    el.querySelector("button").addEventListener("click", function () { dismiss(el); });
    box.appendChild(el);
    setTimeout(function () { dismiss(el); }, ms || 5000);
  };

  // Pesan flash dari server (lihat _flash.html)
  document.querySelectorAll("#flash-data span").forEach(function (s) {
    window.showToast(s.textContent.trim(), s.dataset.category);
  });

  // Menu TA: kalau belum lulus KP, langsung pop up tanpa pindah halaman
  var taLinks = document.querySelectorAll('.sidebar a[href^="/mahasiswa/ta/"]');
  if (taLinks.length) {
    var kpLulus = null; // null = belum diketahui, server tetap yang memutuskan
    fetch("/api/status-kp", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) kpLulus = d.lulus; })
      .catch(function () {});

    taLinks.forEach(function (a) {
      a.addEventListener("click", function (e) {
        if (kpLulus !== false) return;
        e.preventDefault();
        window.showToast("Modul Tugas Akhir baru bisa diakses setelah Anda lulus Sidang Kerja Praktek (KP).", "danger");
      });
    });
  }
})();
