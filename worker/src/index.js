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
    <title>Auto Clip Job Launcher</title>
    <style>
      :root {
        --bg: #0f172a;
        --panel: #111827;
        --panel-2: #1f2937;
        --text: #e5e7eb;
        --muted: #94a3b8;
        --accent: #22c55e;
        --accent-2: #06b6d4;
      }
      body {
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
        color: var(--text);
        background: radial-gradient(circle at 10% 10%, #1e293b 0, var(--bg) 55%);
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 20px;
      }
      .card {
        width: min(760px, 100%);
        background: linear-gradient(180deg, var(--panel), var(--panel-2));
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 14px 30px rgba(0, 0, 0, 0.35);
      }
      h1 {
        margin: 0 0 8px;
        font-size: 1.7rem;
      }
      p {
        margin: 0 0 18px;
        color: var(--muted);
      }
      label {
        display: block;
        margin: 10px 0 6px;
        font-weight: 600;
      }
      input, textarea {
        width: 100%;
        box-sizing: border-box;
        border: 1px solid #475569;
        border-radius: 10px;
        padding: 10px 12px;
        background: #0b1220;
        color: var(--text);
      }
      textarea {
        min-height: 120px;
      }
      .actions {
        display: flex;
        gap: 12px;
        margin-top: 14px;
      }
      button {
        border: none;
        border-radius: 10px;
        padding: 10px 16px;
        font-weight: 700;
        cursor: pointer;
      }
      .primary {
        background: linear-gradient(90deg, var(--accent), var(--accent-2));
        color: #041013;
      }
      .secondary {
        background: #334155;
        color: var(--text);
      }
      pre {
        margin-top: 14px;
        background: #020617;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px;
        overflow: auto;
        white-space: pre-wrap;
      }
      .tiny {
        margin-top: 10px;
        font-size: 12px;
        color: var(--muted);
      }
    </style>
  </head>
  <body>
    <main class="card">
      <h1>Auto Clip Job Launcher</h1>
      <p>Submit YouTube or media URLs to the Worker queue for downstream clip processing.</p>
      <label for="source">Source URL</label>
      <input id="source" placeholder="https://www.youtube.com/watch?v=..." />

      <label for="config">Optional Config JSON</label>
      <textarea id="config" placeholder='{"max_clips": 8, "render_vertical_9x16": true}'></textarea>

      <div class="actions">
        <button id="submit" class="primary">Queue Job</button>
        <button id="health" class="secondary">Check Health</button>
      </div>

      <pre id="result">Ready.</pre>
      <div id="clips"></div>
      <div class="tiny">This page calls the same Worker origin endpoints: POST /jobs, GET /results/&lt;id&gt;, GET /health.</div>
    </main>

    <script>
      const source = document.getElementById("source");
      const config = document.getElementById("config");
      const result = document.getElementById("result");
      const clipsBox = document.getElementById("clips");
      let pollTimer = null;

      function show(data) {
        result.textContent = JSON.stringify(data, null, 2);
      }

      function renderClips(files) {
        const clips = files.filter((f) => f.name.endsWith(".mp4"));
        if (!clips.length) { clipsBox.innerHTML = ""; return; }
        clipsBox.innerHTML = "<h3>Clips</h3>" + clips.map((f) =>
          '<p><a style="color:#22c55e" href="' + f.url + '" target="_blank">' + f.name + '</a> (' + Math.round(f.size / 1024 / 1024 * 10) / 10 + ' MB)</p>'
        ).join("");
      }

      async function poll(jobId) {
        const response = await fetch("/results/" + jobId);
        const data = await response.json();
        show(data);
        renderClips(data.files || []);
        const state = data.status && data.status.state;
        if (state === "done" || state === "error") {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      }

      document.getElementById("submit").addEventListener("click", async () => {
        const payload = { source: source.value.trim() };
        if (!payload.source) {
          show({ ok: false, error: "Source URL is required" });
          return;
        }

        if (config.value.trim()) {
          try {
            payload.config = JSON.parse(config.value);
          } catch (err) {
            show({ ok: false, error: "Config must be valid JSON", details: String(err) });
            return;
          }
        }

        const response = await fetch("/jobs", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        show(data);

        if (data.ok && data.job && data.job.id) {
          if (pollTimer) clearInterval(pollTimer);
          pollTimer = setInterval(() => poll(data.job.id), 8000);
        }
      });

      document.getElementById("health").addEventListener("click", async () => {
        const response = await fetch("/health");
        show(await response.json());
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
