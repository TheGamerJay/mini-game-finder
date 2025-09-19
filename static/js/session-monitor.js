// Session activity monitoring for authenticated users
(function () {
  // Only run for authenticated users
  if (!document.body.dataset.authenticated || document.body.dataset.authenticated !== 'true') {
    return;
  }

  const CHECK_MS = 15_000; // poll every 15s
  let warned = false;

  async function checkSession() {
    try {
      const r = await fetch("/api/session/status", { credentials: "include" });
      const data = await r.json();
      if (!data.authenticated) return; // login page handles itself

      const remain = data.remaining_seconds;
      if (remain <= 0) {
        // server will enforce logout on next request anyway; hard redirect:
        location.href = "/login";
        return;
      }

      if (!warned && remain <= data.warn_at_seconds) {
        warned = true;
        showStillThere(remain);
      }
    } catch (e) {
      // network hiccup — ignore once
    }
  }

  function showStillThere(remaining) {
    // Super-simple modal
    const el = document.createElement("div");
    el.id = "still-there";
    el.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9999;";
    el.innerHTML = `
      <div style="background:#111;color:#fff;padding:24px;border-radius:12px;max-width:420px;text-align:center">
        <h3>Still there?</h3>
        <p>For your security, you'll be logged out soon due to inactivity.</p>
        <p><strong><span id="mwf-count">${remaining}</span>s</strong> remaining</p>
        <button id="mwf-stay" style="padding:8px 16px;background:#007acc;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-top:12px;">I'm still here</button>
      </div>`;
    document.body.appendChild(el);

    const countEl = el.querySelector("#mwf-count");
    let left = remaining;
    const t = setInterval(() => {
      left -= 1;
      countEl.textContent = left;
      if (left <= 0) {
        clearInterval(t);
        location.href = "/login";
      }
    }, 1000);

    el.querySelector("#mwf-stay").addEventListener("click", async () => {
      try { await fetch("/api/session/ping", { method: "POST", credentials: "include" }); } catch(e){}
      clearInterval(t);
      el.remove();
      warned = false;
    }, { once:true });
  }

  // Reset timer on user activity (also call /api/session/ping occasionally)
  ["click","keydown","mousemove","touchstart"].forEach(evt =>
    document.addEventListener(evt, throttle(() => {
      fetch("/api/session/ping", { method:"POST", credentials:"include" }).catch(()=>{});
    }, 10_000))
  );

  function throttle(fn, wait) {
    let last = 0;
    return function(...args){
      const now = Date.now();
      if (now - last >= wait) { last = now; fn.apply(this,args); }
    }
  }

  setInterval(checkSession, CHECK_MS);
  checkSession();
})();