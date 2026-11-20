/* Menu sidebar geser untuk layar kecil (role selain mahasiswa) */
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
    var kpLulus = null;
    fetch("/api/status-kp", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) kpLulus = d.lulus; })
      .catch(function () {});

    taLinks.forEach(function (a) {
      a.addEventListener("click", function (e) {
        if (kpLulus !== false) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        window.showToast("Modul Tugas Akhir baru bisa diakses setelah Anda lulus Sidang Kerja Praktek (KP).", "danger");
      });
    });
  }
})();

/* ===== Animasi Matrix Hero Banner ===== */
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('matrixCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const characters = '011001010{}<>/=+$#@;*INF';
    const fontSize = 13;
    let columns = 0;
    let drops = [];

    function resizeCanvas() {
        canvas.width = canvas.parentElement.offsetWidth;
        canvas.height = canvas.parentElement.offsetHeight;
        columns = Math.floor(canvas.width / fontSize);
        drops = Array(columns).fill(1);
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    function drawMatrix() {
          ctx.fillStyle = 'rgba(15, 27, 61, 0.2)';
          ctx.fillRect(0, 0, canvas.width, canvas.height);

          // Warna teks kode Biru Utama (#0284C7)
          ctx.fillStyle = '#0284C7'; 
          ctx.font = `${fontSize}px monospace`;

          for (let i = 0; i < drops.length; i++) {
              const text = characters.charAt(Math.floor(Math.random() * characters.length));
              ctx.fillText(text, i * fontSize, drops[i] * fontSize);

              if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                  drops[i] = 0;
              }
              drops[i]++;
          }
        }})

/* ===== Sliding Sideline (Desktop) & Sliding Underline (Mobile) ===== */
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const sidebarInner = sidebar ? sidebar.querySelector('.sidebar-inner') : null;
    const sidebarMenu = sidebar ? sidebar.querySelector('.sidebar-menu') : null;
    if (!sidebarInner || !sidebarMenu) return;

    const collapseStateKey = 'sikap_open_collapses';
    let isNavigating = false;

    // 1. Elemen garis Mobile (Underline) & Desktop (Sideline)
    const mobileUnderline = document.createElement('div');
    mobileUnderline.className = 'sliding-underline d-md-none';
    sidebarInner.appendChild(mobileUnderline);

    const desktopSideline = document.createElement('div');
    desktopSideline.className = 'sidebar-sliding-sideline d-none d-md-block';
    sidebarMenu.appendChild(desktopSideline);

    const mobileTabItems = [
        sidebar.querySelector('.sidebar-menu > a[href*="dashboard"]'),
        sidebar.querySelector('a[href="#menuKerjaPraktek"]'),
        sidebar.querySelector('a[href="#menuTugasAkhir"]'),
        sidebar.querySelector('.user-profile-link'),
        document.getElementById('themeToggle'),
        sidebar.querySelector('a[href="/logout"]')
    ].filter(Boolean);

    // 2. Simpan status buka/tutup setiap dropdown agar tetap bertahan saat pindah halaman
    function saveCollapseStates() {
        if (window.innerWidth < 768) return;
        const openIds = Array.from(sidebarMenu.querySelectorAll('.collapse.show'))
            .map(el => el.id)
            .filter(Boolean);
        sessionStorage.setItem(collapseStateKey, JSON.stringify(openIds));
    }

    // 3. Hitung & gerakkan Mobile Underline
    function moveMobileUnderline(targetEl, instant = false) {
        if (!targetEl || window.innerWidth >= 768) return;
        const containerRect = sidebarInner.getBoundingClientRect();
        const itemRect = targetEl.getBoundingClientRect();
        const barWidth = Math.min(30, itemRect.width * 0.58);
        const leftPos = (itemRect.left - containerRect.left) + (itemRect.width - barWidth) / 2;

        if (instant) mobileUnderline.style.transition = 'none';
        mobileUnderline.style.width = `${barWidth}px`;
        mobileUnderline.style.transform = `translateX(${leftPos}px)`;

        if (instant) {
            mobileUnderline.offsetHeight;
            mobileUnderline.style.transition = '';
        }
        sessionStorage.setItem('sikap_mobile_underline', JSON.stringify({ w: barWidth, x: leftPos }));
    }

    // 4. Hitung & gerakkan Desktop Sideline
    function moveDesktopSideline(targetEl, instant = false) {
        if (!targetEl || window.innerWidth < 768) return;

        const parentCollapse = targetEl.closest('.collapse');
        if (parentCollapse && !parentCollapse.classList.contains('show') && !parentCollapse.classList.contains('collapsing')) {
            const toggleBtn = sidebarMenu.querySelector(`[href="#${parentCollapse.id}"]`);
            if (toggleBtn) targetEl = toggleBtn;
        }

        const menuRect = sidebarMenu.getBoundingClientRect();
        const itemRect = targetEl.getBoundingClientRect();
        if (itemRect.height === 0) return;

        const barHeight = Math.max(24, itemRect.height * 0.65);
        const topPos = (itemRect.top - menuRect.top) + (itemRect.height - barHeight) / 2;
        const leftPos = targetEl.classList.contains('sub-menu-link') ? 22 : 4;

        if (instant) desktopSideline.style.transition = 'none';
        desktopSideline.style.height = `${barHeight}px`;
        desktopSideline.style.transform = `translate(${leftPos}px, ${topPos}px)`;

        if (instant) {
            desktopSideline.offsetHeight;
            desktopSideline.style.transition = '';
        }
        sessionStorage.setItem('sikap_desktop_sideline', JSON.stringify({ h: barHeight, x: leftPos, y: topPos }));
    }

    // 5. Deteksi elemen aktif & pulihkan dropdown yang sebelumnya terbuka
    function getActiveElements() {
        const path = window.location.pathname;
        const exactLink = Array.from(sidebar.querySelectorAll('a[href]')).find(a => {
            const href = a.getAttribute('href');
            return href && href !== '/' && !href.startsWith('#') && path === href;
        });

        let desktopTarget = exactLink || sidebarMenu.querySelector('.nav-link-custom.active');
        let mobileTarget = exactLink;

        if (window.innerWidth >= 768) {
            const savedOpenIds = JSON.parse(sessionStorage.getItem(collapseStateKey) || '[]');
            savedOpenIds.forEach(id => {
                const colEl = document.getElementById(id);
                const togEl = sidebar.querySelector(`a[href="#${id}"]`);
                if (colEl) colEl.classList.add('show');
                if (togEl) togEl.setAttribute('aria-expanded', 'true');
            });
        }

        if (path.includes('/mahasiswa/ta')) {
            mobileTarget = sidebar.querySelector('a[href="#menuTugasAkhir"]');
            const taCollapse = document.getElementById('menuTugasAkhir');
            const taToggle = sidebar.querySelector('a[href="#menuTugasAkhir"]');
            if (taCollapse && window.innerWidth >= 768) {
                taCollapse.classList.add('show');
                if (taToggle) taToggle.setAttribute('aria-expanded', 'true');
            }
        } else if (path.includes('/mahasiswa/')) {
            mobileTarget = sidebar.querySelector('a[href="#menuKerjaPraktek"]');
            const kpCollapse = document.getElementById('menuKerjaPraktek');
            const kpToggle = sidebar.querySelector('a[href="#menuKerjaPraktek"]');
            if (kpCollapse && window.innerWidth >= 768) {
                kpCollapse.classList.add('show');
                if (kpToggle) kpToggle.setAttribute('aria-expanded', 'true');
            }
        } else if (path.includes('/profil')) {
            mobileTarget = sidebar.querySelector('.user-profile-link');
        }

        saveCollapseStates();

        return {
            desktop: desktopTarget || sidebarMenu.querySelector('a[href*="dashboard"]'),
            mobile: mobileTarget || sidebarMenu.querySelector('a[href*="dashboard"]')
        };
    }

    // 6. Event klik menu & tahan reload sejenak agar animasi meluncur selesai dulu
    const allSidebarLinks = sidebarMenu.querySelectorAll('.nav-link-custom');
    const navLinksToDelay = sidebar.querySelectorAll('a[href^="/mahasiswa"], a[href^="/dashboard"], a[href="/profil"]');

    navLinksToDelay.forEach(link => {
        link.addEventListener('click', (e) => {
            if (e.defaultPrevented) return;
            const targetUrl = link.getAttribute('href');

            if (e.ctrlKey || e.metaKey || e.shiftKey || targetUrl === window.location.pathname) {
                return;
            }

            e.preventDefault();
            e.stopPropagation();
            isNavigating = true;
            saveCollapseStates();

            allSidebarLinks.forEach(el => el.classList.remove('active'));
            if (link.classList.contains('nav-link-custom')) {
                link.classList.add('active');
            }

            if (window.innerWidth >= 768) {
                moveDesktopSideline(link, false);
            } else {
                const mobileTarget = targetUrl.includes('/mahasiswa/ta')
                    ? sidebar.querySelector('a[href="#menuTugasAkhir"]')
                    : targetUrl.includes('/mahasiswa/')
                    ? sidebar.querySelector('a[href="#menuKerjaPraktek"]')
                    : link;

                mobileTabItems.forEach(el => el.classList.remove('active'));
                if (mobileTarget) {
                    mobileTarget.classList.add('active');
                    moveMobileUnderline(mobileTarget, false);
                }
            }

            setTimeout(() => {
                window.location.href = targetUrl;
            }, 380);
        });
    });

    // Klik dropdown accordion tanpa pindah halaman
    allSidebarLinks.forEach(link => {
        if (link.hasAttribute('data-bs-toggle')) {
            link.addEventListener('click', (e) => {
                if (isNavigating) {
                    e.preventDefault();
                    return;
                }
                const targetId = link.getAttribute('href');
                const targetCollapse = targetId ? document.querySelector(targetId) : null;
                const hasActiveChild = targetCollapse && targetCollapse.querySelector('.nav-link-custom.active');

                if (!hasActiveChild) {
                    moveDesktopSideline(link, false);
                }
            });
        }

    });

    mobileTabItems.forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth < 768 && !item.getAttribute('href')?.startsWith('/')) {
                mobileTabItems.forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                moveMobileUnderline(item, false);
            }
        });
    });

    // 7. Ikuti pergerakan dropdown per frame agar sideline tidak patah-patah
    sidebarMenu.querySelectorAll('.collapse').forEach(collapseEl => {
        let rafId = null;
        const trackCollapse = () => {
            if (!isNavigating) {
                const activeItem = sidebarMenu.querySelector('.nav-link-custom.active') || getActiveElements().desktop;
                moveDesktopSideline(activeItem, true);
            }
            rafId = requestAnimationFrame(trackCollapse);
        };

        collapseEl.addEventListener('show.bs.collapse', (e) => {
            if (isNavigating) { e.preventDefault(); return; }
            rafId = requestAnimationFrame(trackCollapse);
        });
        collapseEl.addEventListener('hide.bs.collapse', (e) => {
            if (isNavigating) { e.preventDefault(); return; }
            rafId = requestAnimationFrame(trackCollapse);
        });
        collapseEl.addEventListener('shown.bs.collapse', () => {
            cancelAnimationFrame(rafId);
            saveCollapseStates();
            if (!isNavigating) {
                const activeItem = sidebarMenu.querySelector('.nav-link-custom.active') || getActiveElements().desktop;
                moveDesktopSideline(activeItem, false);
            }
        });
        collapseEl.addEventListener('hidden.bs.collapse', () => {
            cancelAnimationFrame(rafId);
            saveCollapseStates();
            if (!isNavigating) {
                const activeItem = sidebarMenu.querySelector('.nav-link-custom.active') || getActiveElements().desktop;
                moveDesktopSideline(activeItem, false);
            }
        });
    });

    // 8. Singkatkan label tema di HP
    const themeText = document.getElementById('themeText');
    const syncThemeLabel = () => {
        if (!themeText) return;
        if (window.innerWidth < 768) {
            themeText.textContent = 'Tema';
        } else {
            const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
            themeText.textContent = isDark ? 'Light Mode' : 'Dark Mode';
        }
    };

    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => setTimeout(syncThemeLabel, 10));
    }

    // 9. Inisialisasi posisi awal langsung terkunci rapi di halaman baru
    const initial = getActiveElements();
    if (initial.desktop) {
        allSidebarLinks.forEach(el => el.classList.remove('active'));
        initial.desktop.classList.add('active');
        moveDesktopSideline(initial.desktop, true);
    }
    if (initial.mobile) {
        mobileTabItems.forEach(el => el.classList.remove('active'));
        initial.mobile.classList.add('active');
        moveMobileUnderline(initial.mobile, true);
    }
    syncThemeLabel();

    window.addEventListener('resize', () => {
        const current = getActiveElements();
        moveDesktopSideline(sidebarMenu.querySelector('.nav-link-custom.active') || current.desktop, true);
        moveMobileUnderline(current.mobile, true);
        syncThemeLabel();
    });

    // Tutup popup submenu KP/TA di mobile saat tap di luar area sidebar
    document.addEventListener('click', (e) => {
        if (window.innerWidth < 768 && !sidebar.contains(e.target)) {
            sidebarMenu.querySelectorAll('.collapse.show').forEach(openCol => {
                const bsCol = bootstrap.Collapse.getInstance(openCol);
                if (bsCol) bsCol.hide();
                else openCol.classList.remove('show');
            });
        }
    });
});