import { Container } from "@cloudflare/containers";

export class ProcessorContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "45m";
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

function html(content, status = 200) {
  return new Response(content, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

function appUi() {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Auto Clip — DJ set to short clips</title>
    <style>
      :root {
        --bg: #0b1020;
        --panel: #121a2e;
        --panel-2: #0e1526;
        --line: #26324d;
        --text: #e7ecf5;
        --muted: #8fa0bd;
        --accent: #22c55e;
        --accent-2: #06b6d4;
        --err: #f87171;
        --warn: #fbbf24;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
        color: var(--text);
        background: radial-gradient(1200px 600px at 15% -10%, #1c2a4a 0, var(--bg) 60%);
        min-height: 100vh;
      }
      header {
        display: flex; align-items: center; justify-content: space-between;
        max-width: 960px; margin: 0 auto; padding: 22px 20px 6px;
      }
      .brand { font-size: 1.35rem; font-weight: 800; letter-spacing: .3px; }
      .brand em { color: var(--accent); font-style: normal; }
      .pill {
        font-size: 12px; padding: 4px 12px; border-radius: 999px;
        border: 1px solid var(--line); color: var(--muted); background: var(--panel-2);
      }
      .pill.ok { color: var(--accent); border-color: #14532d; }
      .pill.bad { color: var(--err); border-color: #7f1d1d; }
      main { max-width: 960px; margin: 0 auto; padding: 10px 20px 60px; display: grid; gap: 18px; }
      .card {
        background: linear-gradient(180deg, var(--panel), var(--panel-2));
        border: 1px solid var(--line); border-radius: 16px; padding: 22px;
        box-shadow: 0 12px 28px rgba(0,0,0,.35);
      }
      h2 { margin: 0 0 6px; font-size: 1.15rem; }
      h3 { margin: 18px 0 8px; font-size: .95rem; color: var(--muted); text-transform: uppercase; letter-spacing: .6px; }
      .muted { color: var(--muted); font-size: .92rem; margin: 0 0 14px; }
      label { display: block; margin: 0 0 5px; font-weight: 600; font-size: .85rem; }
      input[type=text], input[type=number], textarea {
        width: 100%; border: 1px solid var(--line); border-radius: 10px;
        padding: 11px 13px; background: #0a101f; color: var(--text); font-size: .95rem;
      }
      input:focus, textarea:focus { outline: 2px solid #155e75; border-color: transparent; }
      textarea { min-height: 90px; font-family: ui-monospace, monospace; font-size: .85rem; }
      .opts { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 14px 0 6px; }
      .check { display: flex; align-items: center; gap: 8px; margin: 12px 0; font-weight: 600; font-size: .9rem; cursor: pointer; }
      .check input { width: 17px; height: 17px; accent-color: var(--accent); }
      button {
        border: none; border-radius: 10px; padding: 12px 20px; font-weight: 700;
        cursor: pointer; font-size: .95rem;
      }
      .primary { background: linear-gradient(90deg, var(--accent), var(--accent-2)); color: #04120a; width: 100%; margin-top: 8px; }
      .primary:disabled { opacity: .5; cursor: wait; }

      .sec { background: #223050; color: var(--text); }
      .row { display: flex; gap: 10px; align-items: center; }
      .row input { flex: 1; }
      .badge {
        font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 999px;
        text-transform: uppercase; letter-spacing: .5px;
      }
      .badge.processing, .badge.pending, .badge.queued { background: #172554; color: #93c5fd; }
      .badge.done { background: #052e16; color: var(--accent); }
      .badge.error { background: #450a0a; color: var(--err); }
      .spinner {
        width: 16px; height: 16px; border: 2px solid var(--line); border-top-color: var(--accent);
        border-radius: 50%; animation: spin 0.8s linear infinite; display: inline-block; vertical-align: -3px;
      }
      @keyframes spin { to { transform: rotate(360deg); } }
      #job-progress { display: flex; gap: 10px; align-items: center; color: var(--muted); margin: 12px 0; font-size: .92rem; }
      .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-top: 14px; }
      .clip { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: #0a101f; }
      .clip video { width: 100%; display: block; background: #000; aspect-ratio: 16/9; }
      .clip .meta { display: flex; justify-content: space-between; align-items: center; padding: 9px 12px; font-size: .82rem; }
      .clip a { color: var(--accent); font-weight: 700; text-decoration: none; }
      table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: .88rem; }
      th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); }
      th { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .5px; }
      .hidden { display: none; }
      .error-box { background: #450a0a; border: 1px solid #7f1d1d; color: #fecaca; border-radius: 10px; padding: 12px 14px; font-size: .88rem; margin-top: 12px; white-space: pre-wrap; word-break: break-word; }
      .hist-row {
        display: flex; justify-content: space-between; align-items: center; gap: 10px;
        padding: 10px 6px; border-bottom: 1px solid var(--line); cursor: pointer; font-size: .9rem;
      }
      .hist-row:hover { background: #16203a; }
      .hist-row .src { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; color: var(--text); }
      .hist-row .when { color: var(--muted); font-size: .78rem; white-space: nowrap; }
      details.card > summary {
        cursor: pointer; font-weight: 700; font-size: 1.05rem; list-style: none;
      }
      details.card > summary::before { content: "▸ "; color: var(--accent); }
      details.card[open] > summary::before { content: "▾ "; }
      pre.api {
        background: #05080f; border: 1px solid var(--line); border-radius: 10px;
        padding: 14px; overflow: auto; font-size: .8rem; line-height: 1.6; color: #a5f3fc;
      }
      .msg { margin-top: 10px; font-size: .88rem; color: var(--muted); }
      .msg.err { color: var(--err); }
    </style>
  </head>
  <body>
    <header>
      <div class="brand">⚡ Auto<em>Clip</em></div>
      <div id="svc" class="pill">checking…</div>
    </header>
    <main>
      <section class="card">
        <h2>Create clips from a DJ set</h2>
        <p class="muted">Paste a video URL. AutoClip finds the drops and cuts short shareable clips automatically.</p>
        <label for="source">Video URL</label>
        <input type="text" id="source" placeholder="https://... (direct .mp4/.m4v/.mkv or YouTube URL)" />
        <div class="opts">
          <div><label>Clip length (sec)</label><input type="number" id="opt-duration" value="30" min="10" max="120"></div>
          <div><label>Max clips</label><input type="number" id="opt-max" value="6" min="1" max="50"></div>
          <div><label>Min gap between clips (sec)</label><input type="number" id="opt-spacing" value="120" min="10" max="600"></div>
          <div><label>Start before drop (sec)</label><input type="number" id="opt-pre" value="10" min="0" max="60"></div>
        </div>
        <label class="check"><input type="checkbox" id="opt-vertical"> Vertical 9:16 export (TikTok / Reels / Shorts)</label>
        <button id="submit" class="primary">Generate clips</button>
        <div id="submit-msg" class="msg"></div>
      </section>

      <section class="card hidden" id="job-panel">
        <div class="row" style="justify-content: space-between;">
          <h2 style="margin:0;">Job <span id="job-id-short" class="muted" style="font-size:.8rem;"></span></h2>
          <span id="job-state" class="badge pending">pending</span>
        </div>
        <div class="muted" id="job-meta" style="margin-top:6px;"></div>
        <div id="job-progress"><span class="spinner"></span><span id="job-hint">Queued — waiting for the processor…</span></div>
        <div id="gallery" class="gallery"></div>
        <div id="drops"></div>
        <div id="job-error" class="error-box hidden"></div>
      </section>

      <section class="card" id="history-card">
        <h2>History</h2>
        <p class="muted" style="margin-bottom:4px;">Jobs from this browser. Click to reopen.</p>
        <div id="history"><div class="msg">No jobs yet.</div></div>
      </section>

      <details class="card">
        <summary>Advanced</summary>
        <h3>Batch queue</h3>
        <p class="muted">One URL per line. Uses the options above.</p>
        <textarea id="batch" placeholder="https://...\nhttps://..."></textarea>
        <button id="batch-btn" class="sec" style="margin-top:8px;">Queue all</button>
        <div id="batch-msg" class="msg"></div>
        <h3>Look up a job</h3>
        <div class="row">
          <input type="text" id="lookup" placeholder="job id" />
          <button id="lookup-btn" class="sec">Open</button>
        </div>
        <h3>Raw config override (JSON, merged over options)</h3>
        <textarea id="rawcfg" placeholder='{"sample_rate": 22050}'></textarea>
        <h3>API reference</h3>
        <pre class="api">POST /jobs                          body: {"source": "URL", "config": { ... }}
                                    → 202 { job: { id } }
GET  /results/&lt;job-id&gt;             → { status: { state }, files: [ { name, size, url } ] }
GET  /files/jobs/&lt;job-id&gt;/&lt;name&gt;   → media file (mp4 / json)
GET  /health                        → service check

config fields: clip_duration_seconds, max_clips, min_spacing_seconds,
               pre_drop_seconds, render_vertical_9x16, sample_rate</pre>
      </details>
    </main>

    <script>
      var pollTimer = null;
      var currentJob = null;
      var startedAt = null;

      function $(id) { return document.getElementById(id); }
      function esc(s) {
        return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;");
      }
      function mb(n) { return (Math.round(n / 1024 / 1024 * 10) / 10) + " MB"; }
      function ts(sec) {
        sec = Math.floor(sec);
        var m = Math.floor(sec / 60), s = sec % 60;
        return m + ":" + (s < 10 ? "0" : "") + s;
      }

      // ---------- history ----------
      function loadHist() {
        try { return JSON.parse(localStorage.getItem("autoclip-history") || "[]"); } catch (e) { return []; }
      }
      function saveHist(items) { localStorage.setItem("autoclip-history", JSON.stringify(items.slice(0, 25))); }
      function addHist(id, source) {
        var items = loadHist().filter(function (j) { return j.id !== id; });
        items.unshift({ id: id, source: source, at: Date.now(), state: "queued" });
        saveHist(items); renderHist();
      }
      function setHistState(id, state) {
        var items = loadHist();
        items.forEach(function (j) { if (j.id === id) j.state = state; });
        saveHist(items); renderHist();
      }
      function renderHist() {
        var items = loadHist();
        if (!items.length) { $("history").innerHTML = '<div class="msg">No jobs yet.</div>'; return; }
        $("history").innerHTML = items.map(function (j) {
          return '<div class="hist-row" data-id="' + esc(j.id) + '" data-src="' + esc(j.source) + '">' +
            '<span class="src">' + esc(j.source) + '</span>' +
            '<span class="when">' + new Date(j.at).toLocaleString() + '</span>' +
            '<span class="badge ' + esc(j.state || "queued") + '">' + esc(j.state || "queued") + '</span></div>';
        }).join("");
        Array.prototype.forEach.call(document.querySelectorAll(".hist-row"), function (row) {
          row.addEventListener("click", function () { openJob(row.getAttribute("data-id"), row.getAttribute("data-src")); });
        });
      }

      // ---------- config ----------
      function buildConfig() {
        var cfg = {
          clip_duration_seconds: parseInt($("opt-duration").value, 10) || 30,
          max_clips: parseInt($("opt-max").value, 10) || 6,
          min_spacing_seconds: parseInt($("opt-spacing").value, 10) || 120,
          pre_drop_seconds: parseInt($("opt-pre").value, 10) || 10,
          render_vertical_9x16: $("opt-vertical").checked
        };
        var raw = $("rawcfg").value.trim();
        if (raw) {
          try {
            var extra = JSON.parse(raw);
            for (var k in extra) cfg[k] = extra[k];
          } catch (e) { throw new Error("Advanced config JSON is invalid: " + e.message); }
        }
        return cfg;
      }

      // ---------- job submission ----------
      async function queueJob(source) {
        var cfg = buildConfig();
        var res = await fetch("/jobs", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ source: source, config: cfg })
        });
        var data = await res.json();
        if (!data.ok || !data.job || !data.job.id) throw new Error(data.error || "Submission failed");
        addHist(data.job.id, source);
        return data.job.id;
      }

      $("submit").addEventListener("click", async function () {
        var source = $("source").value.trim();
        var msg = $("submit-msg");
        msg.className = "msg"; msg.textContent = "";
        if (!source) { msg.className = "msg err"; msg.textContent = "Please paste a video URL first."; return; }
        $("submit").disabled = true;
        try {
          var id = await queueJob(source);
          msg.textContent = "Job queued.";
          openJob(id, source);
        } catch (e) {
          msg.className = "msg err"; msg.textContent = String(e.message || e);
        } finally {
          $("submit").disabled = false;
        }
      });

      // ---------- batch ----------
      $("batch-btn").addEventListener("click", async function () {
        var lines = $("batch").value.split("\\n").map(function (l) { return l.trim(); }).filter(Boolean);
        var msg = $("batch-msg");
        msg.className = "msg"; msg.textContent = "";
        if (!lines.length) { msg.className = "msg err"; msg.textContent = "Add at least one URL."; return; }
        $("batch-btn").disabled = true;
        var ok = 0, firstId = null;
        try {
          for (var i = 0; i < lines.length; i++) {
            try {
              var id = await queueJob(lines[i]);
              if (!firstId) firstId = id;
              ok++;
            } catch (e) { /* continue batch */ }
          }
          msg.textContent = "Queued " + ok + " of " + lines.length + " jobs — track them in History.";
          if (firstId) openJob(firstId, lines[0]);
        } finally {
          $("batch-btn").disabled = false;
        }
      });

      // ---------- lookup ----------
      $("lookup-btn").addEventListener("click", function () {
        var id = $("lookup").value.trim();
        if (id) openJob(id, "(lookup)");
      });

      // ---------- job panel ----------
      function openJob(id, source) {
        currentJob = id;
        startedAt = Date.now();
        $("job-panel").classList.remove("hidden");
        $("job-id-short").textContent = id;
        $("job-meta").textContent = source || "";
        $("job-state").className = "badge pending"; $("job-state").textContent = "pending";
        $("gallery").innerHTML = ""; $("drops").innerHTML = "";
        $("job-error").classList.add("hidden");
        $("job-progress").classList.remove("hidden");
        $("job-hint").textContent = "Queued — waiting for the processor…";
        $("job-panel").scrollIntoView({ behavior: "smooth" });
        if (pollTimer) clearInterval(pollTimer);
        poll();
        pollTimer = setInterval(poll, 6000);
      }

      async function poll() {
        if (!currentJob) return;
        var res, data;
        try {
          res = await fetch("/results/" + encodeURIComponent(currentJob));
          data = await res.json();
        } catch (e) { return; }
        var state = (data.status && data.status.state) || "pending";
        $("job-state").className = "badge " + state;
        $("job-state").textContent = state;
        setHistState(currentJob, state);

        if (state === "processing" || state === "pending" || state === "queued") {
          var mins = Math.floor((Date.now() - startedAt) / 60000);
          $("job-hint").textContent = state === "processing"
            ? "Processing — downloading, analyzing and cutting clips… (" + mins + "m elapsed; long sets can take a while)"
            : "Queued — the processor may be cold-starting (~1 min)…";
          return;
        }

        clearInterval(pollTimer); pollTimer = null;
        $("job-progress").classList.add("hidden");

        if (state === "error") {
          var box = $("job-error");
          box.textContent = "Processing failed: " + ((data.status && data.status.error) || "unknown error");
          box.classList.remove("hidden");
          return;
        }

        // done → render gallery
        var clips = (data.files || []).filter(function (f) { return f.name.slice(-4) === ".mp4"; });
        $("gallery").innerHTML = clips.map(function (f) {
          return '<div class="clip">' +
            '<video controls preload="metadata" src="' + esc(f.url) + '"></video>' +
            '<div class="meta"><span>' + esc(f.name) + '</span>' +
            '<a href="' + esc(f.url) + '" download>' + mb(f.size) + ' ⬇</a></div></div>';
        }).join("") || '<div class="msg">Finished, but no clips were produced. Try lowering “Min gap”.</div>';

        // drop details from summary.json
        try {
          var sRes = await fetch("/files/jobs/" + encodeURIComponent(currentJob) + "/summary.json");
          if (sRes.ok) {
            var summary = await sRes.json();
            var rows = (summary.clips || []).map(function (c, i) {
              return "<tr><td>" + (i + 1) + "</td><td>" + ts(c.drop_timestamp_seconds) + "</td><td>" +
                (Math.round(c.score * 100) / 100) + "</td><td>" + ts(c.start_seconds) + "</td></tr>";
            }).join("");
            if (rows) {
              $("drops").innerHTML = "<h3>Detected drops</h3><table><tr><th>#</th><th>Drop at</th><th>Score</th><th>Clip starts</th></tr>" + rows + "</table>";
            }
          }
        } catch (e) { /* non-fatal */ }
      }

      // ---------- boot ----------
      renderHist();
      fetch("/health").then(function (r) { return r.json(); }).then(function (h) {
        var el = $("svc");
        el.textContent = h.ok ? "service online" : "service issue";
        el.className = "pill " + (h.ok ? "ok" : "bad");
      }).catch(function () {
        var el = $("svc"); el.textContent = "offline"; el.className = "pill bad";
      });
    </script>
  </body>
</html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return html(appUi());
    }

    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "auto-clip-worker", timestamp: new Date().toISOString() });
    }

    if (request.method === "GET" && url.pathname === "/debug/restart") {
      if (!env.PROCESSOR) return json({ ok: false, error: "No container binding" }, 500);
      const container = env.PROCESSOR.getByName("processor-v2");
      await container.destroy();
      return json({ ok: true, restarted: true });
    }

    if (request.method === "GET" && url.pathname === "/debug/container") {
      if (!env.PROCESSOR) return json({ ok: false, error: "No container binding" }, 500);
      try {
        const container = env.PROCESSOR.getByName("processor-v2");
        const response = await container.fetch("http://container/health");
        const text = await response.text();
        let body;
        try { body = JSON.parse(text); } catch { body = { raw: text }; }
        return json({ ok: true, containerStatus: response.status, containerHealth: body });
      } catch (error) {
        return json({ ok: false, error: String(error) }, 500);
      }
    }

    if (request.method === "POST" && url.pathname === "/jobs") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ ok: false, error: "Invalid JSON payload" }, 400);
      }

      if (!body || typeof body.source !== "string" || body.source.trim() === "") {
        return json({ ok: false, error: "Field 'source' is required" }, 400);
      }

      const payload = {
        source: body.source,
        config: body.config ?? null,
        id: crypto.randomUUID(),
        requestedAt: new Date().toISOString()
      };

      if (env.AUTO_CLIP_JOBS) {
        await env.AUTO_CLIP_JOBS.send(payload);
      }

      return json({
        ok: true,
        accepted: true,
        mode: env.AUTO_CLIP_JOBS ? "queued" : "stub",
        job: payload
      }, 202);
    }

    if (request.method === "GET" && url.pathname.startsWith("/results/")) {
      const jobId = url.pathname.slice("/results/".length).replace(/[^a-zA-Z0-9_-]/g, "_");
      if (!jobId) return json({ ok: false, error: "Job id required" }, 400);

      const listFiles = async () => {
        const listed = await env.OUTPUTS.list({ prefix: `jobs/${jobId}/` });
        return listed.objects.map((o) => ({
          name: o.key.split("/").pop(),
          size: o.size,
          url: `/files/${o.key}`
        }));
      };

      // Already synced to R2?
      const statusObject = await env.OUTPUTS.get(`jobs/${jobId}/status.json`);
      if (statusObject) {
        const status = await statusObject.json();
        return json({ ok: true, job: jobId, status, files: await listFiles() });
      }

      // Ask the container and sync finished results into R2.
      if (env.PROCESSOR) {
        try {
          const container = env.PROCESSOR.getByName("processor-v2");
          const response = await container.fetch(`http://container/job/${jobId}`);
          if (response.status === 200) {
            const info = await response.json();
            if (info.state === "done") {
              for (const name of info.files || []) {
                const file = await container.fetch(`http://container/job/${jobId}/file/${name}`);
                if (file.ok) {
                  await env.OUTPUTS.put(`jobs/${jobId}/${name}`, await file.arrayBuffer());
                }
              }
              if (info.summary) {
                await env.OUTPUTS.put(`jobs/${jobId}/summary.json`, JSON.stringify(info.summary, null, 2));
              }
              const status = { state: "done", clip_count: (info.files || []).length };
              await env.OUTPUTS.put(`jobs/${jobId}/status.json`, JSON.stringify(status, null, 2));
              return json({ ok: true, job: jobId, status, files: await listFiles() });
            }
            if (info.state === "error") {
              const status = { state: "error", error: info.error };
              await env.OUTPUTS.put(`jobs/${jobId}/status.json`, JSON.stringify(status, null, 2));
              return json({ ok: true, job: jobId, status, files: [] });
            }
            return json({ ok: true, job: jobId, status: { state: info.state || "processing" }, files: [] });
          }
        } catch (error) {
          console.error("Container results sync failed", error);
        }
      }

      return json({ ok: true, job: jobId, status: { state: "pending" }, files: [] });
    }

    if (request.method === "GET" && url.pathname.startsWith("/files/")) {
      const key = decodeURIComponent(url.pathname.slice("/files/".length));
      if (!key.startsWith("jobs/")) return json({ ok: false, error: "Not Found" }, 404);
      const object = await env.OUTPUTS.get(key);
      if (!object) return json({ ok: false, error: "Not Found" }, 404);
      const name = key.split("/").pop();
      return new Response(object.body, {
        headers: {
          "content-type": name.endsWith(".mp4") ? "video/mp4" : "application/json",
          "content-disposition": `inline; filename="${name}"`
        }
      });
    }

    return json({ ok: false, error: "Not Found" }, 404);
  }
  ,
  async queue(batch, env) {
    for (const message of batch.messages) {
      const payload = message.body;

      try {
        if (env.PROCESSOR) {
          const container = env.PROCESSOR.getByName("processor-v2");
          const response = await container.fetch("http://container/process", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(payload)
          });
          if (!response.ok) {
            throw new Error(`Container processing failed with ${response.status}`);
          }
        } else if (env.PROCESSOR_WEBHOOK) {
          const response = await fetch(env.PROCESSOR_WEBHOOK, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(payload)
          });
          if (!response.ok) {
            throw new Error(`Webhook failed with ${response.status}`);
          }
        } else {
          console.log("Queue message received (no processor configured):", payload);
        }

        message.ack();
      } catch (error) {
        console.error("Queue forwarding failed", error);
        message.retry();
      }
    }
  }
};
