import json
import os

from flask import Flask, render_template_string, request

from main import FILE, MODELS, get_ai_suggestions

app = Flask(__name__)

# The whole UI (HTML + CSS + JavaScript) lives in this one string.
PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CampusFlow Ticket Creator</title>
  <style>
    :root {
      --bg: #f4f6fb;
      --card: #ffffff;
      --text: #1c2333;
      --muted: #6b7385;
      --border: #dde1ea;
      --accent: #3b5bdb;
      --accent-hover: #2f49b3;
      --success-bg: #e6f6ec;
      --success-text: #1a7f37;
      --error-bg: #fdeaea;
      --error-text: #b00020;
      --box-border: #e0a800;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #12151f;
        --card: #1b2030;
        --text: #e8ebf3;
        --muted: #9aa3b8;
        --border: #2d3550;
        --accent: #6f8cff;
        --accent-hover: #5877f0;
        --success-bg: #14301f;
        --success-text: #6fd58d;
        --error-bg: #3a1a1f;
        --error-text: #ff8a98;
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
    }
    .container { max-width: 640px; margin: 0 auto; padding: 2rem 1rem 4rem; }
    .header { text-align: center; margin-bottom: 1.5rem; }
    .header h1 { margin: 0; font-size: 2rem; color: var(--accent); }
    .subtitle { margin: 0.25rem 0 0; color: var(--muted); }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.25rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    .field { margin-bottom: 1.1rem; }
    label { display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.95rem; }
    input, textarea, select {
      width: 100%;
      padding: 0.7rem 0.8rem;
      font: inherit;
      color: var(--text);
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    input:focus, textarea:focus, select:focus {
      outline: 2px solid var(--accent);
      outline-offset: 1px;
    }
    textarea { resize: vertical; }
    .hint { display: block; margin-top: 0.25rem; text-align: right; font-size: 0.8rem; color: var(--muted); }
    .btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.6rem;
      width: 100%;
      padding: 0.8rem;
      font: inherit;
      font-weight: 600;
      color: #fff;
      background: var(--accent);
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.15s;
    }
    .btn:hover { background: var(--accent-hover); }
    .btn:disabled { opacity: 0.7; cursor: not-allowed; }
    .spinner {
      display: none;
      width: 1rem;
      height: 1rem;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    .btn.loading .spinner { display: inline-block; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .alert { padding: 0.85rem 1rem; border-radius: 8px; margin-bottom: 1.25rem; }
    .alert.success { background: var(--success-bg); color: var(--success-text); }
    .alert.error { background: var(--error-bg); color: var(--error-text); }
    .results { border: 2px solid var(--box-border); }
    .results-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
    .results-header h2 { margin: 0; font-size: 1.15rem; }
    .btn-small {
      padding: 0.35rem 0.8rem;
      font: inherit;
      font-size: 0.85rem;
      color: var(--text);
      background: transparent;
      border: 1px solid var(--border);
      border-radius: 6px;
      cursor: pointer;
    }
    .btn-small:hover { border-color: var(--accent); color: var(--accent); }
    .suggestions { margin: 0; white-space: pre-wrap; word-wrap: break-word; font-family: inherit; }
  </style>
</head>
<body>
  <main class="container">
    <header class="header">
      <h1>CampusFlow</h1>
      <p class="subtitle">Create a helpdesk ticket and get AI-powered fix suggestions.</p>
    </header>

    <form id="ticket-form" class="card" method="post">
      <div class="field">
        <label for="title">Ticket title</label>
        <input id="title" name="title" type="text" maxlength="100"
               placeholder="e.g. Wi-Fi keeps disconnecting"
               value="{{ form.title or '' }}" required>
      </div>

      <div class="field">
        <label for="description">Description</label>
        <textarea id="description" name="description" rows="5" maxlength="1000"
                  placeholder="Describe what is happening, where, and since when..."
                  required>{{ form.description or '' }}</textarea>
        <span id="char-count" class="hint">0 / 1000</span>
      </div>

      <div class="field">
        <label for="model">AI model</label>
        <select id="model" name="model">
          {% for key, m in models.items() %}
            <option value="{{ key }}" {% if form.model == key %}selected{% endif %}>
              {{ m.model }} ({{ m.provider }})
            </option>
          {% endfor %}
          <option value="0" {% if form.model == '0' %}selected{% endif %}>Skip AI suggestions</option>
        </select>
      </div>

      <button id="submit-btn" type="submit" class="btn">
        <span class="btn-text">Create ticket</span>
        <span class="spinner" aria-hidden="true"></span>
      </button>
    </form>

    {% if ticket %}
      <div class="alert success" role="status">
        Ticket <strong>{{ ticket.id }}</strong> created successfully.
      </div>
    {% endif %}

    {% if error %}
      <div class="alert error" role="alert">{{ error }}</div>
    {% endif %}

    {% if suggestions %}
      <section id="results" class="card results">
        <div class="results-header">
          <h2>AI suggestions</h2>
          <button id="copy-btn" type="button" class="btn-small">Copy</button>
        </div>
        <pre id="suggestions-text" class="suggestions">{{ suggestions }}</pre>
      </section>
    {% endif %}
  </main>

  <script>
    // Character counter for the description box
    const description = document.getElementById("description");
    const charCount = document.getElementById("char-count");

    function updateCount() {
      charCount.textContent = description.value.length + " / " + description.maxLength;
    }
    if (description && charCount) {
      description.addEventListener("input", updateCount);
      updateCount();
    }

    // Loading state while the AI request is running
    const form = document.getElementById("ticket-form");
    const submitBtn = document.getElementById("submit-btn");

    if (form && submitBtn) {
      form.addEventListener("submit", function () {
        const btnText = submitBtn.querySelector(".btn-text");
        submitBtn.disabled = true;
        submitBtn.classList.add("loading");
        btnText.textContent = "Creating ticket and fetching suggestions...";
      });
    }

    // Copy button for the suggestions
    const copyBtn = document.getElementById("copy-btn");
    const suggestionsText = document.getElementById("suggestions-text");

    if (copyBtn && suggestionsText) {
      copyBtn.addEventListener("click", async function () {
        try {
          await navigator.clipboard.writeText(suggestionsText.textContent);
          copyBtn.textContent = "Copied!";
        } catch (err) {
          copyBtn.textContent = "Copy failed";
        }
        setTimeout(function () {
          copyBtn.textContent = "Copy";
        }, 1500);
      });
    }

    // Scroll to the results when they appear
    const results = document.getElementById("results");
    if (results) {
      results.scrollIntoView({ behavior: "smooth", block: "start" });
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