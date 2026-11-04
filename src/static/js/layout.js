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

  window.showToast = function (message, type = "info") {
      let container = document.querySelector(".toast-stack");
      if (!container) {
          container = document.createElement("div");
          container.className = "toast-stack";
          document.body.appendChild(container);
      }

      const icons = {
          success: "bi-check-circle-fill",
          danger: "bi-x-circle-fill",
          warning: "bi-exclamation-triangle-fill",
          info: "bi-info-circle-fill"
      };

      const toast = document.createElement("div");
      toast.className = `toast-item toast-${type}`;
      
      toast.innerHTML = `
          <i class="bi ${icons[type] || icons.info}"></i>
          <div class="toast-text">${message}</div>
          <button type="button" onclick="this.parentElement.remove()">&times;</button>
      `;

      container.appendChild(toast);

      setTimeout(() => {
          toast.classList.add("out");
          setTimeout(() => toast.remove(), 300);
      }, 2000);
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

document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('matrixCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Penyesuaian ukuran canvas dengan kontainer induknya
    function resizeCanvas() {
        canvas.width = canvas.parentElement.offsetWidth;
        canvas.height = canvas.parentElement.offsetHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Karakter yang ditampilkan (Biner & Simbol Kode)
    const characters = '011001010{}<>/=+$#@;*INF';
    const fontSize = 13;
    let columns = Math.floor(canvas.width / fontSize);

    // Posisi Y awal untuk tiap baris kolom
    let drops = Array(columns).fill(1);

    function drawMatrix() {
        // Efek trail/bayangan saat karakter meluncur turun (sesuai warna background #070e1b)
        ctx.fillStyle = 'rgba(7, 14, 27, 0.15)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Warna teks kode (Biru Cyan Neon)
        ctx.fillStyle = '#60a5fa'; 
        ctx.font = `${fontSize}px monospace`;

        for (let i = 0; i < drops.length; i++) {
            const text = characters.charAt(Math.floor(Math.random() * characters.length));
            ctx.fillText(text, i * fontSize, drops[i] * fontSize);

            if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }
            drops[i]++;
        }
    }

    // Interval pembaharuan animasi (50ms)
    setInterval(drawMatrix, 50);
});
