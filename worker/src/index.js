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
      <div class="tiny">This page calls the same Worker origin endpoints: POST /jobs and GET /health.</div>
    </main>

    <script>
      const source = document.getElementById("source");
      const config = document.getElementById("config");
      const result = document.getElementById("result");

      function show(data) {
        result.textContent = JSON.stringify(data, null, 2);
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
        show(await response.json());
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

    return json({ ok: false, error: "Not Found" }, 404);
  }
  ,
  async queue(batch, env) {
    for (const message of batch.messages) {
      const payload = message.body;
      if (!env.PROCESSOR_WEBHOOK) {
        console.log("Queue message received (no PROCESSOR_WEBHOOK configured):", payload);
        message.ack();
        continue;
      }

      try {
        const response = await fetch(env.PROCESSOR_WEBHOOK, {
          method: "POST",
          headers: {
            "content-type": "application/json"
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          throw new Error(`Webhook failed with ${response.status}`);
        }

        message.ack();
      } catch (error) {
        console.error("Queue forwarding failed", error);
        message.retry();
      }
    }
  }
};
