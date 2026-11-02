import json
import os

from flask import Flask, render_template_string, request

from main import FILE, MODELS, get_ai_suggestions

app = Flask(__name__)

# The whole UI (HTML + CSS + JavaScript) lives in this one string.
# The r before the quotes makes it a raw string, so \n reaches the browser as \n.
PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CampusFlow</title>
  <style>
    :root {
      --bg: #050f0d;
      --panel: #0a1a17;
      --panel2: #071311;
      --line: #16332e;
      --text: #e6f4f1;
      --muted: #7c9a94;
      --mint: #5eead4;
      --amber: #fbbf24;
      --coral: #fb7185;
      --mono: ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(1100px 600px at 85% -10%, #0e2b26 0%, transparent 60%), var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
    }
    .wrap { max-width: 1040px; margin: 0 auto; padding: 24px 20px 48px; }

    .top {
      display: flex;
      align-items: center;
      gap: 12px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }
    .logo {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, #5eead4, #38bdf8);
      color: #04201c;
      display: grid;
      place-items: center;
      font-family: var(--mono);
      font-weight: 800;
    }
    .brand { font-weight: 700; }
    .brand small { display: block; color: var(--muted); font-weight: 400; font-size: 0.8rem; }

    .eyebrow {
      margin: 36px 0 8px;
      font-size: 0.75rem;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--mint);
      font-weight: 700;
    }
    h1 {
      margin: 0;
      font-size: clamp(2rem, 5.5vw, 3.4rem);
      line-height: 1.08;
      letter-spacing: -0.02em;
    }
    h1 span { color: var(--amber); }
    .lead { max-width: 560px; margin: 14px 0 28px; color: var(--muted); }

    .card {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel);
      overflow: hidden;
    }
    .card-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 18px 22px;
      border-bottom: 1px solid var(--line);
    }
    .card-head h2 { margin: 0; font-size: 1.05rem; }
    .card-head p { margin: 2px 0 0; color: var(--muted); font-size: 0.82rem; }
    .badge {
      border: 1px solid var(--mint);
      color: var(--mint);
      border-radius: 8px;
      padding: 4px 10px;
      font-family: var(--mono);
      font-size: 0.7rem;
      letter-spacing: 0.08em;
      white-space: nowrap;
    }

    .term {
      margin: 20px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel2);
      overflow: hidden;
    }
    .term-bar {
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
    }
    .dot { width: 10px; height: 10px; border-radius: 50%; }
    .dot.a { background: var(--coral); }
    .dot.b { background: var(--amber); }
    .dot.c { background: var(--mint); }
    .term-title { margin-left: auto; font-family: var(--mono); font-size: 0.72rem; color: var(--muted); }

    .log {
      height: clamp(300px, 52vh, 560px);
      overflow-y: auto;
      padding: 14px 18px;
      font-family: var(--mono);
      font-size: 0.92rem;
    }
    .line { display: grid; grid-template-columns: 26px 1fr; margin: 9px 0; word-break: break-word; }
    .line.ok .sym, .line.ok .txt { color: var(--mint); }
    .line.warn .sym, .line.warn .txt { color: var(--amber); }
    .line.err .sym, .line.err .txt { color: var(--coral); }
    .line.ask .sym, .line.ask .txt { color: var(--c); }
    .line.user .sym { color: var(--muted); }
    .line.list .txt { color: var(--muted); }
    .out { grid-column: 2; }
    .out pre {
      margin: 0 0 10px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #040c0a;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: var(--mono);
      font-size: 0.88rem;
      color: var(--text);
    }

    .bar {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      border-top: 1px solid var(--line);
    }
    .bar .prompt { font-family: var(--mono); color: var(--mint); }
    .bar input {
      flex: 1;
      min-width: 0;
      background: transparent;
      border: 0;
      outline: none;
      color: var(--text);
      font-family: var(--mono);
      font-size: 0.95rem;
    }
    .btn {
      display: inline-block;
      border: 0;
      border-radius: 8px;
      padding: 9px 16px;
      background: var(--mint);
      color: #04201c;
      font: inherit;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      text-decoration: none;
    }
    .btn:disabled { opacity: 0.5; cursor: wait; }
    .btn.alt { background: var(--amber); }
    .bar.end { justify-content: flex-end; }

    .spin {
      display: inline-block;
      width: 12px;
      height: 12px;
      border: 2px solid var(--amber);
      border-right-color: transparent;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    @media (max-width: 600px) {
      .card-head { flex-direction: column; align-items: flex-start; }
      .term { margin: 12px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div class="logo">&gt;_</div>
      <div class="brand">CampusFlow<small>Helpdesk terminal</small></div>
    </div>

    <div class="eyebrow">Helpdesk / 01</div>
    <h1>Report it. Track it.<br><span>Fix it faster.</span></h1>
    <p class="lead">Answer a few quick questions in the terminal below and get AI-powered fix suggestions for your problem.</p>

    <div class="card">
      <div class="card-head">
        <div>
          <h2>Ticket terminal</h2>
          <p>Describe the problem, one step at a time</p>
        </div>
        <div class="badge">GUIDED CLI</div>
      </div>

      <div class="term">
        <div class="term-bar">
          <span class="dot a"></span><span class="dot b"></span><span class="dot c"></span>
          <span class="term-title">campusflow ~ terminal</span>
        </div>

        <div class="log" id="log">
          {% if ticket %}
            {% set colors = {'Issue': '#fb7185', 'Location': '#5eead4', 'When it happened': '#38bdf8', 'Duration': '#a78bfa', 'Extra details': '#fb923c'} %}
            <div class="line ok"><span class="sym">✓</span><span class="txt">Ticket creation started.</span></div>

            <div class="line ask" style="--c:#fbbf24"><span class="sym">›</span><span class="txt">Ticket title</span></div>
            <div class="line user"><span class="sym">$</span><span class="txt">{{ ticket.title }}</span></div>

            {% for part in ticket.description.splitlines() %}
              {% set pieces = part.split(': ', 1) %}
              {% set label = pieces[0] %}
              {% set value = pieces[1] if pieces|length > 1 else '' %}
              <div class="line ask" style="--c:{{ colors.get(label, '#e6f4f1') }}"><span class="sym">›</span><span class="txt">{{ label }}</span></div>
              <div class="line user"><span class="sym">$</span><span class="txt">{{ value }}</span></div>
            {% endfor %}

            {% set chosen = models.get(form.model) %}
            {% if chosen %}
              <div class="line ask" style="--c:#a3e635"><span class="sym">›</span><span class="txt">AI model</span></div>
              <div class="line user"><span class="sym">$</span><span class="txt">{{ chosen.model }} ({{ chosen.provider }})</span></div>
            {% endif %}

            <div class="line ok"><span class="sym">✓</span><span class="txt">Ticket {{ ticket.id }} saved: {{ ticket.title }}</span></div>
          {% endif %}
          {% if suggestions %}
            <div class="line warn"><span class="sym">!</span><span class="txt">AI suggestions</span></div>
            <div class="line">
              <span></span>
              <div class="out">
                <pre id="suggestions-text">{{ suggestions }}</pre>
                <button type="button" class="btn alt" id="copy-btn">Copy</button>
              </div>
            </div>
          {% endif %}
          {% if error %}
            <div class="line err"><span class="sym">✗</span><span class="txt">{{ error }}</span></div>
          {% endif %}
        </div>

        {% if ticket or error %}
          <div class="bar end">
            <a class="btn" href="/">New ticket</a>
          </div>
        {% else %}
          <div class="bar">
            <span class="prompt">$</span>
            <input type="text" id="cmd" autocomplete="off" autofocus>
            <button type="button" class="btn" id="send">Send</button>
          </div>
        {% endif %}
      </div>
    </div>

    <form method="post" id="ticket-form" style="display:none">
      <input type="hidden" name="title" id="f-title">
      <input type="hidden" name="description" id="f-description">
      <input type="hidden" name="model" id="f-model">
    </form>
  </div>

  <script>
    const hasResult = {{ 'true' if (ticket or error) else 'false' }};
    const models = {{ models | tojson }};

    const log = document.getElementById("log");
    const input = document.getElementById("cmd");
    const sendBtn = document.getElementById("send");
    const form = document.getElementById("ticket-form");

    const steps = [
      { key: "title", ask: "Enter the ticket title:", color: "#fbbf24", max: 100, required: true },
      { key: "issue", ask: "What is the issue?", color: "#fb7185", max: 300, required: true },
      { key: "place", ask: "Where is it? (building, room or cluster)", color: "#5eead4", max: 100, required: true },
      { key: "when", ask: "When did it happen?", color: "#38bdf8", max: 100, required: true },
      { key: "duration", ask: "How long has it been going on? (Enter to skip)", color: "#a78bfa", max: 100, required: false },
      { key: "extra", ask: "Anything else we should know? (Enter to skip)", color: "#fb923c", max: 200, required: false },
      { key: "model", ask: "Choose an AI model by number (Enter for the first one):", color: "#a3e635", max: 10, required: false, isModel: true }
    ];

    const answers = {};
    const modelKeys = Object.keys(models);
    let i = 0;

    function addLine(sym, text, cls, color) {
      const row = document.createElement("div");
      row.className = "line " + cls;
      if (color) { row.style.setProperty("--c", color); }
      const s = document.createElement("span");
      s.className = "sym";
      s.textContent = sym;
      const t = document.createElement("span");
      t.className = "txt";
      t.textContent = text;
      row.appendChild(s);
      row.appendChild(t);
      log.appendChild(row);
      log.scrollTop = log.scrollHeight;
      return row;
    }

    function modelLabel(key) {
      const m = models[key];
      if (m && typeof m === "object") {
        return key + ") " + m.model + " (" + m.provider + ")";
      }
      return key + ") " + String(m);
    }

    function askNext() {
      const step = steps[i];
      if (step.isModel) {
        modelKeys.forEach(function (k) { addLine(" ", modelLabel(k), "list"); });
      }
      addLine("›", step.ask, "ask", step.color);
      input.maxLength = step.max;
      input.focus();
    }

    function buildDescription() {
      const parts = [
        ["Issue", answers.issue],
        ["Location", answers.place],
        ["When it happened", answers.when],
        ["Duration", answers.duration],
        ["Extra details", answers.extra]
      ];
      return parts
        .filter(function (p) { return p[1] && p[1] !== ""; })
        .map(function (p) { return p[0] + ": " + p[1]; })
        .join("\n");
    }

    function finish() {
      document.getElementById("f-title").value = answers.title;
      document.getElementById("f-description").value = buildDescription();
      document.getElementById("f-model").value = answers.model;
      input.disabled = true;
      sendBtn.disabled = true;
      addLine("✓", "Got everything.", "ok");
      const row = addLine("›", " Saving ticket and asking the AI...", "warn");
      const spinner = document.createElement("span");
      spinner.className = "spin";
      row.querySelector(".sym").textContent = "";
      row.querySelector(".sym").appendChild(spinner);
      setTimeout(function () { form.submit(); }, 500);
    }

    function submitAnswer() {
      const step = steps[i];
      let val = input.value.trim();

      if (step.isModel) {
        if (val === "") { val = modelKeys[0]; }
        if (modelKeys.indexOf(val) === -1) {
          addLine("!", "Please type one of: " + modelKeys.join(", "), "warn");
          return;
        }
      }
      if (step.required && val === "") {
        addLine("!", "This one is required.", "warn");
        return;
      }

      addLine("$", val === "" ? "(skipped)" : val, "user");
      answers[step.key] = val;
      input.value = "";
      i += 1;

      if (i < steps.length) { askNext(); } else { finish(); }
    }

    if (!hasResult) {
      sendBtn.addEventListener("click", submitAnswer);
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); submitAnswer(); }
      });
      addLine("✓", "Ticket creation started.", "ok");
      askNext();
    }

    const copyBtn = document.getElementById("copy-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", async function () {
        const text = document.getElementById("suggestions-text").innerText;
        try {
          await navigator.clipboard.writeText(text);
          copyBtn.textContent = "Copied!";
        } catch (e) {
          copyBtn.textContent = "Copy failed";
        }
        setTimeout(function () { copyBtn.textContent = "Copy"; }, 1500);
      });
    }
  </script>
</body>
</html>
"""


def save_ticket(title, description):
    tickets = []
    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                tickets = json.load(f)
        except json.JSONDecodeError:
            tickets = []

    ticket = {
        "id": f"A{len(tickets) + 1:03d}",
        "title": title,
        "description": description,
    }
    tickets.append(ticket)

    with open(FILE, "w") as f:
        json.dump(tickets, f, indent=4)
    return ticket


@app.route("/", methods=["GET", "POST"])
def index():
    ticket = suggestions = error = None
    form = {"title": "", "description": "", "model": "1"}

    if request.method == "POST":
        form["title"] = request.form.get("title", "").strip()
        form["description"] = request.form.get("description", "").strip()
        form["model"] = request.form.get("model", "1")

        if not form["title"] or not form["description"]:
            error = "Title and description cannot be empty."
        else:
            ticket = save_ticket(form["title"], form["description"])
            choice = MODELS.get(form["model"])
            if choice:
                suggestions, error = get_ai_suggestions(ticket, choice)
            # Clear the text boxes after a successful submission
            form["title"] = ""
            form["description"] = ""

    return render_template_string(
        PAGE,
        models=MODELS,
        ticket=ticket,
        suggestions=suggestions,
        error=error,
        form=form,
    )


if __name__ == "__main__":
    app.run(debug=True)