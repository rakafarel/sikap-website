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

  document.querySelectorAll(".sidebar a").forEach(function (a) {
    a.addEventListener("click", function () { setOpen(false); });
  });

  window.matchMedia("(min-width: 992px)").addEventListener("change", function (e) {
    if (e.matches) setOpen(false);
  });
})();