const elements = {
  mode: document.getElementById("mode"),
  goal: document.getElementById("goal"),
  resumeText: document.getElementById("resume_text"),
  activityText: document.getElementById("activity_text"),
  jobPostingText: document.getElementById("job_posting_text"),
  sampleButton: document.getElementById("sample-button"),
  generateButton: document.getElementById("generate-button"),
  statusBadge: document.getElementById("status-badge"),
  warningBox: document.getElementById("warning-box"),
  summary: document.getElementById("tailored_summary"),
  requirementsList: document.getElementById("requirements_list"),
  gapsList: document.getElementById("gaps_list"),
  resumeBullets: document.getElementById("resume_bullets"),
  coverPoints: document.getElementById("cover_points"),
  matchesBoard: document.getElementById("matches_board"),
  checklist: document.getElementById("checklist"),
};

function setStatus(text) {
  elements.statusBadge.textContent = text;
}

function renderList(target, items) {
  target.innerHTML = "";
  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No data yet.";
    target.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

function renderMatches(matches) {
  elements.matchesBoard.innerHTML = "";
  if (!matches || matches.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No evidence mapping yet.";
    elements.matchesBoard.appendChild(empty);
    return;
  }

  matches.forEach((match, index) => {
    const card = document.createElement("article");
    card.className = "match-card";
    const colors = ["var(--green)", "var(--gold)", "var(--coral)", "var(--blue)"];
    card.style.borderLeftColor = colors[index % colors.length];

    const title = document.createElement("h4");
    title.textContent = match.requirement;
    card.appendChild(title);

    const evidence = document.createElement("p");
    evidence.textContent = `Evidence: ${match.evidence}`;
    card.appendChild(evidence);

    const note = document.createElement("p");
    note.className = "match-note";
    note.textContent = match.note;
    card.appendChild(note);

    elements.matchesBoard.appendChild(card);
  });
}

function renderWarnings(warnings) {
  if (!warnings || warnings.length === 0) {
    elements.warningBox.classList.add("hidden");
    elements.warningBox.textContent = "";
    return;
  }
  elements.warningBox.classList.remove("hidden");
  elements.warningBox.textContent = warnings.join(" ");
}

function buildPayload() {
  return {
    mode: elements.mode.value,
    goal: elements.goal.value,
    resume_text: elements.resumeText.value,
    activity_text: elements.activityText.value,
    job_posting_text: elements.jobPostingText.value,
  };
}

async function loadSample() {
  setStatus("Loading sample");
  const response = await fetch("/api/sample");
  const payload = await response.json();
  elements.goal.value = payload.goal || "internship application";
  elements.resumeText.value = payload.resume_text || "";
  elements.activityText.value = payload.activity_text || "";
  elements.jobPostingText.value = payload.job_posting_text || "";
  setStatus("Sample loaded");
}

async function generatePackage() {
  setStatus("Generating");
  renderWarnings([]);
  elements.summary.textContent = "Generating...";
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload()),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Unknown server error");
    }

    setStatus(`${payload.backend} / ${payload.language}${payload.model ? ` / ${payload.model}` : ""}`);
    elements.summary.textContent = payload.tailored_summary || "No summary generated.";
    renderList(elements.requirementsList, payload.extracted_requirements);
    renderList(elements.gapsList, payload.evidence_gaps);
    renderList(elements.resumeBullets, payload.resume_bullets);
    renderList(elements.coverPoints, payload.cover_letter_points);
    renderList(elements.checklist, payload.checklist);
    renderMatches(payload.evidence_matches);
    renderWarnings(payload.warnings || []);
  } catch (error) {
    setStatus("Error");
    elements.summary.textContent = "Generation failed.";
    renderWarnings([error.message]);
  }
}

elements.sampleButton.addEventListener("click", loadSample);
elements.generateButton.addEventListener("click", generatePackage);

