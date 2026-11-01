const card = document.querySelector(".card");
const titles = { login: "Masuk - SIKAP", register: "Daftar - SIKAP" };

/* Satu tombol: ganti Masuk <-> Daftar dengan animasi lingkaran dari tengah layar */
const html = document.documentElement;
const reduced = false; // matchMedia("(prefers-reduced-motion: reduce)").matches;
let busy = false;

function applyMode(mode) {
  card.dataset.mode = mode;
  html.dataset.mode = mode;
  document.title = titles[mode];
  history.replaceState(null, "", mode === "register" ? "/register" : "/login");
  setTimeout(() => {
    const first = card.querySelector(".f-" + mode + " input:not([type=radio])");
    if (first && matchMedia("(hover: hover)").matches) first.focus({ preventScroll: true });
  }, 700);
}

/* Cadangan untuk browser tanpa View Transitions: lingkaran menutup layar, lalu halaman diganti */
function circleFallback(mode) {
  const wipe = document.createElement("div");
  wipe.className = "wipe " + mode;
  document.body.appendChild(wipe);
  wipe.animate(
    [{ clipPath: "circle(0 at 50% 50%)" }, { clipPath: "circle(150vmax at 50% 50%)" }],
    { duration: 700, easing: "cubic-bezier(.65,0,.25,1)", fill: "forwards" }
  ).finished.then(() => {
    applyMode(mode);
    wipe.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 400, fill: "forwards" })
      .finished.then(() => { wipe.remove(); busy = false; });
  });
}

function setMode(mode) {
  if (busy || card.dataset.mode === mode) return;
  busy = true;
  if (reduced) { applyMode(mode); busy = false; return; }
  if (document.startViewTransition) {
    document.startViewTransition(() => applyMode(mode)).finished.finally(() => { busy = false; });
  } else {
    circleFallback(mode);
  }
}
document.getElementById("switch").addEventListener("click", () =>
  setMode(card.dataset.mode === "login" ? "register" : "login")
);
setTimeout(() => card.classList.remove("intro"), 1800);

/* Ikon mata password */
document.querySelectorAll(".eye").forEach((btn) =>
  btn.addEventListener("click", () => {
    const input = btn.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.querySelector("i").className = show ? "fas fa-eye-slash" : "fas fa-eye";
    btn.setAttribute("aria-label", show ? "Sembunyikan password" : "Tampilkan password");
  })
);

/* Tombol kirim: tampil "Memproses..." dan cegah kirim ganda */
document.querySelectorAll("form").forEach((f) =>
  f.addEventListener("submit", (e) => {
    if (f.dataset.sent) return e.preventDefault();
    f.dataset.sent = "1";
    const btn = f.querySelector(".btn");
    btn.classList.add("loading");
    btn.firstElementChild.textContent = "Memproses";
  })
);
addEventListener("pageshow", (e) => {
  if (!e.persisted) return;
  document.querySelectorAll("form").forEach((f) => {
    delete f.dataset.sent;
    const btn = f.querySelector(".btn");
    btn.classList.remove("loading");
    btn.firstElementChild.textContent = btn.firstElementChild.dataset.label;
  });
});

/* Kalimat yang diketik di panel kiri */
const words = ["mengajukan dosen pembimbing", "mencatat logbook bimbingan", "mendaftar sidang KP", "lanjut ke pengajuan TA"];
const typed = document.getElementById("typed");
let w = 0, c = 0, del = false;
(function tick() {
  const t = words[w];
  typed.textContent = t.slice(0, c);
  if (!del && c === t.length) { del = true; return setTimeout(tick, 1600); }
  if (del && c === 0) { del = false; w = (w + 1) % words.length; }
  c += del ? -1 : 1;
  setTimeout(tick, del ? 28 : 65);
})();

/* Cahaya mengikuti kursor di panel kiri */
const brand = document.querySelector(".brand");
brand.addEventListener("pointermove", (e) => {
  const r = brand.getBoundingClientRect();
  brand.style.setProperty("--mx", e.clientX - r.left + "px");
  brand.style.setProperty("--my", e.clientY - r.top + "px");
});

/* Pesan flash (salah password, username sudah ada, dll.) hilang sendiri setelah 5 detik */
document.querySelectorAll(".alert").forEach((el) => {
  setTimeout(() => {
    el.animate(
      [
        { opacity: 1, maxHeight: el.offsetHeight + "px" },
        { opacity: 0, maxHeight: "0px", paddingTop: "0px", paddingBottom: "0px", marginBottom: "-12px" }
      ],
      { duration: 400, easing: "ease", fill: "forwards" }
    ).finished.then(() => el.remove());
  }, 5000);
});