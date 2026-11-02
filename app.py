import json
import os

from flask import Flask, render_template_string, request

from main import FILE, MODELS, get_ai_suggestions

app = Flask(__name__)

# The whole UI (HTML + CSS + JavaScript) lives in this one string.
PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CampusFlow</title>
  <style>
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background: linear-gradient(160deg, #0b1020 0%, #14213d 100%);
      color: #e8ebf2;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
    }
    .page {
      min-height: 100vh;
      width: 100%;
      padding: 32px clamp(16px, 5vw, 80px);
      display: flex;
      flex-direction: column;
    }
    h1 { margin: 0; font-size: 2rem; color: #74c0fc; }
    .sub { margin: 4px 0 24px; color: #9aa5b5; }
    form { flex: 1; display: flex; flex-direction: column; }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px 24px;
    }
    .full { grid-column: 1 / -1; }
    @media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }

    .field label {
      display: block;
      margin-bottom: 6px;
      font-weight: 700;
      color: var(--c);
    }
    .field input, .field textarea, .field select {
      width: 100%;
      padding: 12px 14px;
      border: 2px solid var(--c);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.06);
      color: #e8ebf2;
      font: inherit;
    }
    .field select option { color: #111; }
    .field input:focus, .field textarea:focus, .field select:focus {
      outline: none;
      box-shadow: 0 0 0 3px var(--c);
    }
    .field textarea { min-height: 110px; resize: vertical; }
    .hint { font-size: 0.8rem; color: #9aa5b5; margin-top: 4px; }

    .counter { text-align: right; font-size: 0.85rem; color: #9aa5b5; margin-top: 12px; }

    button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 14px 20px;
      border: 0;
      border-radius: 10px;
      background: #f06595;
      color: #ffffff;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled { opacity: 0.7; cursor: wait; }
    #submit-btn { width: 100%; margin-top: 16px; font-size: 1.05rem; }
    .spinner {
      display: none;
      width: 16px;
      height: 16px;
      border: 2px solid currentColor;
      border-right-color: transparent;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    button.loading .spinner { display: inline-block; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .msg { margin-top: 20px; padding: 12px 14px; border-radius: 10px; }
    .msg.error { background: #3a1c1c; color: #ffb3b3; }
    .msg.ok { background: #16301f; color: #9be3b8; }

    .suggestions {
      margin-top: 20px;
      border: 2px solid #38d9a9;
      border-radius: 12px;
    }
    .suggestions-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border-bottom: 1px solid #38d9a9;
      font-weight: 700;
      color: #38d9a9;
    }
    .suggestions-head button { padding: 6px 12px; font-size: 0.85rem; background: #38d9a9; color: #0b1020; }
    .suggestions pre {
      margin: 0;
      padding: 14px;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: inherit;
    }
  </style>
</head>
<body>
  <div class="page">
    <h1>CampusFlow</h1>
    <p class="sub">Create a helpdesk ticket and get AI-powered fix suggestions.</p>

    <form method="post" id="ticket-form">
      <div class="grid">
        <div class="field full" style="--c:#ffd43b">
          <label for="title">Ticket title</label>
          <input type="text" id="title" name="title" value="{{ form.title }}" maxlength="100" placeholder="e.g. Laptop screen broken" required>
        </div>

        <div class="field full" style="--c:#ff8787">
          <label for="issue">What is the issue?</label>
          <textarea id="issue" maxlength="400" placeholder="e.g. The screen is cracked and shows lines" required></textarea>
        </div>

        <div class="field" style="--c:#69db7c">
          <label for="place">Where is it?</label>
          <input type="text" id="place" maxlength="100" placeholder="e.g. Computer cluster, Block B" required>
        </div>

        <div class="field" style="--c:#4dabf7">
          <label for="when">When did it happen?</label>
          <input type="text" id="when" maxlength="100" placeholder="e.g. Monday morning" required>
        </div>

        <div class="field" style="--c:#da77f2">
          <label for="duration">How long has it been going on?</label>
          <input type="text" id="duration" maxlength="100" placeholder="e.g. Over a week">
        </div>

        <div class="field" style="--c:#38d9a9">
          <label for="model">AI model</label>
          <select id="model" name="model">
            {% for key, value in models.items() %}
              <option value="{{ key }}" {% if key == form.model %}selected{% endif %}>
                {{ value.name if value is mapping and value.name else value }}
              </option>
            {% endfor %}
          </select>
        </div>

        <div class="field full" style="--c:#ffa94d">
          <label for="extra">Anything else? (optional)</label>
          <textarea id="extra" maxlength="200" placeholder="e.g. Already restarted it, did not help"></textarea>
        </div>
      </div>

      <input type="hidden" id="description" name="description">
      <div class="counter"><span id="count">0</span> / 1000</div>

      <button type="submit" id="submit-btn">
        <span class="spinner"></span>
        <span id="btn-label">Create ticket</span>
      </button>
    </form>

    {% if error %}
      <div class="msg error">{{ error }}</div>
    {% endif %}

    {% if ticket %}
      <div class="msg ok">Ticket {{ ticket.id }} saved: {{ ticket.title }}</div>
    {% endif %}

    {% if suggestions %}
      <div class="suggestions">
        <div class="suggestions-head">
          <span>AI suggestions</span>
          <button type="button" id="copy-btn">Copy</button>
        </div>
        <pre id="suggestions-text">{{ suggestions }}</pre>
      </div>
    {% endif %}
  </div>

  <script>
    const form = document.getElementById("ticket-form");
    const hidden = document.getElementById("description");
    const count = document.getElementById("count");
    const submitBtn = document.getElementById("submit-btn");
    const btnLabel = document.getElementById("btn-label");
    const copyBtn = document.getElementById("copy-btn");

    function buildDescription() {
      const parts = [
        ["Issue", document.getElementById("issue").value],
        ["Location", document.getElementById("place").value],
        ["When it happened", document.getElementById("when").value],
        ["Duration", document.getElementById("duration").value],
        ["Extra details", document.getElementById("extra").value]
      ];
      return parts
        .filter(function (p) { return p[1].trim() !== ""; })
        .map(function (p) { return p[0] + ": " + p[1].trim(); })
        .join("\n");
    }

    function updateCount() {
      count.textContent = buildDescription().length;
    }
    form.addEventListener("input", updateCount);
    updateCount();

    form.addEventListener("submit", function () {
      hidden.value = buildDescription();
      submitBtn.classList.add("loading");
      submitBtn.disabled = true;
      btnLabel.textContent = "Working...";
    });

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