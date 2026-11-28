/* ============================================================
   WALLOW BABY: SITE SETTINGS
   This is the only part you need to edit when links change.
   ============================================================ */
const CONFIG = {
  // Kit form IDs (the number in your Kit embed code)
  forms: {
    starter: "10253796"    // Weaning Recipe Starter Guide (Kit form 1bd24e3db5)
  },
  // Amazon listing. "attribution" = the query string from your Amazon Attribution
  // tag (e.g. "maas=maas_adg_XXXX&ref_=aa_maas"). Leave "" to link the plain listing.
  amazon: {
    url: "https://www.amazon.com/dp/B0DXXF4HF5",
    attribution: ""
  },
  email: "hello@wallowbaby.com"
};

document.addEventListener("DOMContentLoaded", () => {
  /* ---------- mobile menu ---------- */
  const btn = document.querySelector(".menu-btn");
  const links = document.querySelector(".nav-links");
  if (btn && links) {
    btn.addEventListener("click", () => {
      const open = links.classList.toggle("open");
      btn.setAttribute("aria-expanded", open);
      btn.textContent = open ? "Close" : "Menu";
    });
  }

  /* ---------- Amazon buttons ---------- */
  const amazonHref = CONFIG.amazon.url + (CONFIG.amazon.attribution ? "?" + CONFIG.amazon.attribution : "");
  document.querySelectorAll("[data-amazon]").forEach(a => {
    a.href = amazonHref;
    a.target = "_blank";
    a.rel = "noopener";
  });

  /* ---------- email links ---------- */
  document.querySelectorAll("[data-email]").forEach(a => {
    a.href = "mailto:" + CONFIG.email;
    if (!a.textContent.trim()) a.textContent = CONFIG.email;
  });

  /* ---------- Kit signup forms ---------- */
  document.querySelectorAll("form[data-kit]").forEach(form => {
    const id = CONFIG.forms[form.dataset.kit];
    const msg = form.querySelector(".msg");
    if (!id) {
      // No Kit form yet: don't lose the visitor, tell them it's coming
      form.addEventListener("submit", e => {
        e.preventDefault();
        msg.textContent = "The Starter Guide is almost ready. Check back very soon!";
      });
      return;
    }
    form.action = `https://app.kit.com/forms/${id}/subscriptions`;
    form.method = "post";
    form.addEventListener("submit", async e => {
      e.preventDefault();
      if (form.querySelector(".hp input")?.value) return; // bot trap
      const button = form.querySelector("button");
      const data = new FormData(form);
      button.disabled = true; msg.className = "msg"; msg.textContent = "Sending…";
      try {
        const res = await fetch(form.action, { method: "POST", body: data, headers: { Accept: "application/json" } });
        const json = await res.json().catch(() => ({}));
        if (res.ok && json.status !== "failed") {
          if (form.dataset.redirect) { location.href = form.dataset.redirect; return; }
          form.classList.add("done");
          msg.textContent = "You're in! Check your email and tap the confirm button. 💛";
        } else { throw new Error("rejected"); }
      } catch (err) {
        // Network/CORS problem: fall back to a normal form post to Kit
        if (err instanceof TypeError) { HTMLFormElement.prototype.submit.call(form); return; }
        msg.className = "msg err";
        msg.textContent = "Hmm, that didn't go through. Check your email address and try again.";
        button.disabled = false;
      }
    });
  });

  /* ---------- print recipe ---------- */
  document.querySelectorAll("[data-print]").forEach(b => b.addEventListener("click", () => window.print()));

  /* ---------- footer year ---------- */
  document.querySelectorAll("[data-year]").forEach(el => el.textContent = new Date().getFullYear());
});
