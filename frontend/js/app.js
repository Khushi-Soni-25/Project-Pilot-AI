/* ==========================================================================
   ProjectPilot AI - matcher workspace
   Form handling, API calls, result rendering and the project details drawer.
   Backend contract is unchanged: ProjectPilotAPI.{health, options, recommend, project}.
   ========================================================================== */

const state = {
  optionsLoaded: false,
  lastFocus: null,
  slowTimer: null,
};

// Used until the backend answers /options. Mirrors the values in data/projects.json.
const fallbackOptions = {
  domains: [
    "Any",
    "Artificial Intelligence",
    "Machine Learning",
    "Deep Learning",
    "Data Science",
    "Natural Language Processing",
    "Computer Vision",
    "Web Development",
  ],
  skill_levels: ["Any", "Beginner", "Intermediate", "Advanced"],
  available_times: ["Any", "1-3 Days", "4-7 Days", "8-15 Days", "16-30 Days", "1-3 Months"],
  preferred_languages: ["Any", "Python"],
};

const elements = {
  form: document.querySelector("#preferenceForm"),
  domain: document.querySelector("#domain"),
  skillLevel: document.querySelector("#skillLevel"),
  interests: document.querySelector("#interests"),
  availableTime: document.querySelector("#availableTime"),
  preferredLanguage: document.querySelector("#preferredLanguage"),
  topN: document.querySelector("#topN"),
  topNValue: document.querySelector("#topNValue"),
  formError: document.querySelector("#formError"),
  apiStatus: document.querySelector("#apiStatus"),
  loadingState: document.querySelector("#loadingState"),
  loadingNote: document.querySelector("#loadingNote"),
  emptyState: document.querySelector("#emptyState"),
  resultsGrid: document.querySelector("#resultsGrid"),
  resultsSub: document.querySelector("#resultsSub"),
  summary: document.querySelector("#summary"),
  projectDetails: document.querySelector("#projectDetails"),
  drawerBackdrop: document.querySelector("#drawerBackdrop"),
  detailTitle: document.querySelector("#detailTitle"),
  detailDescription: document.querySelector("#detailDescription"),
  detailMeta: document.querySelector("#detailMeta"),
  closeDetails: document.querySelector("#closeDetails"),
};

document.addEventListener("DOMContentLoaded", init);

function init() {
  injectScoreGradient();
  bindEvents();
  populateFallbackOptions();
  updateRangeFill();
  setApiStatus("Checking API", "");
  loadBackendOptions();
  checkBackendHealth();
}

/* Shared gradient used by every score ring */
function injectScoreGradient() {
  document.body.insertAdjacentHTML(
    "beforeend",
    `<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
       <defs>
         <linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="1">
           <stop offset="0" stop-color="#5799F5"/><stop offset="1" stop-color="#51C995"/>
         </linearGradient>
       </defs>
     </svg>`
  );
}

function bindEvents() {
  elements.topN.addEventListener("input", () => {
    elements.topNValue.textContent = elements.topN.value;
    updateRangeFill();
  });

  elements.form.addEventListener("submit", handleRecommendationSubmit);

  document.querySelectorAll("[data-interest]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const current = elements.interests.value.trim();
      const word = chip.dataset.interest;
      const already = current.toLowerCase().split(/[\s,]+/).includes(word.toLowerCase());
      if (!already) elements.interests.value = current ? `${current}, ${word}` : word;
      elements.interests.focus();
    });
  });

  elements.closeDetails.addEventListener("click", closeDrawer);
  elements.drawerBackdrop.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", handleDrawerKeys);

  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
  });
}

function updateRangeFill() {
  const min = Number(elements.topN.min);
  const max = Number(elements.topN.max);
  const pct = ((Number(elements.topN.value) - min) / (max - min)) * 100;
  elements.topN.style.setProperty("--fill", `${pct}%`);
}

/* ---------- Options & health ---------- */

function populateFallbackOptions() {
  populateSelect(elements.domain, fallbackOptions.domains);
  populateSelect(elements.skillLevel, fallbackOptions.skill_levels);
  populateSelect(elements.availableTime, fallbackOptions.available_times);
  populateSelect(elements.preferredLanguage, fallbackOptions.preferred_languages);
}

async function loadBackendOptions() {
  try {
    const options = await ProjectPilotAPI.options();
    populateSelect(elements.domain, ["Any", ...options.domains]);
    populateSelect(elements.skillLevel, ["Any", ...options.skill_levels]);
    populateSelect(elements.availableTime, ["Any", ...options.available_times]);
    populateSelect(elements.preferredLanguage, ["Any", ...options.preferred_languages]);
    state.optionsLoaded = true;
  } catch {
    state.optionsLoaded = false;
  }
}

async function checkBackendHealth() {
  try {
    const health = await ProjectPilotAPI.health();
    setApiStatus(`API online, ${health.total_projects.toLocaleString("en-US")} projects`, "online");
  } catch {
    setApiStatus("API offline", "offline");
  }
}

function populateSelect(selectElement, values) {
  selectElement.innerHTML = values
    .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
    .join("");
}

/* ---------- Recommendations ---------- */

async function handleRecommendationSubmit(event) {
  event.preventDefault();
  clearError();

  const payload = getFormPayload();
  const validationMessage = validatePayload(payload);

  if (validationMessage) {
    showError(validationMessage);
    return;
  }

  setLoading(true);

  try {
    const data = await ProjectPilotAPI.recommend(payload);
    renderRecommendations(data.recommendations);
    setApiStatus("API online", "online");
  } catch (error) {
    renderApiError(error.message);
    setApiStatus("API offline", "offline");
  } finally {
    setLoading(false);
  }
}

function getFormPayload() {
  return {
    domain: elements.domain.value,
    skill_level: elements.skillLevel.value,
    interests: elements.interests.value.trim(),
    available_time: elements.availableTime.value,
    preferred_language: elements.preferredLanguage.value,
    top_n: Number(elements.topN.value),
  };
}

function validatePayload(payload) {
  if (!payload.domain) return "Please choose a domain.";
  if (!payload.skill_level) return "Please choose your skill level.";
  if (!payload.interests || payload.interests.length < 2) {
    return "Please enter at least one clear interest.";
  }
  if (!payload.available_time) return "Please choose your available time.";
  if (!payload.preferred_language) return "Please choose a programming language.";
  return "";
}

function setLoading(isLoading) {
  elements.loadingState.classList.toggle("hidden", !isLoading);
  elements.resultsGrid.classList.toggle("hidden", isLoading);
  elements.summary.classList.toggle("hidden", isLoading || !elements.summary.innerHTML);
  elements.form.querySelector(".submit-button").disabled = isLoading;

  clearTimeout(state.slowTimer);
  elements.loadingNote.textContent = "Finding your best project matches";

  if (isLoading) {
    elements.emptyState.classList.add("hidden");
    // Free-tier hosts can take a while to wake up; tell the user instead of leaving them guessing.
    state.slowTimer = setTimeout(() => {
      elements.loadingNote.textContent =
        "The backend is waking up. This can take up to a minute on the first request.";
    }, 6000);
  }
}

function renderRecommendations(recommendations) {
  closeDrawer({ restoreFocus: false });

  if (!recommendations.length) {
    elements.resultsGrid.innerHTML = "";
    elements.summary.innerHTML = "";
    elements.summary.classList.add("hidden");
    elements.resultsSub.textContent = "No matches for these preferences.";
    elements.emptyState.classList.remove("hidden");
    elements.emptyState.innerHTML = `
      <span class="empty-icon">${icon("search")}</span>
      <strong>No matching projects found</strong>
      <p>Try broader interests, or choose "Any" in the dropdowns.</p>
    `;
    return;
  }

  elements.emptyState.classList.add("hidden");
  elements.resultsGrid.classList.remove("hidden");
  elements.resultsSub.textContent = `${recommendations.length} projects ranked by match score.`;
  renderSummary(recommendations);
  elements.resultsGrid.innerHTML = recommendations.map(createProjectCard).join("");

  elements.resultsGrid.querySelectorAll("[data-project-id]").forEach((button) => {
    button.addEventListener("click", () => loadProjectDetails(button.dataset.projectId));
  });

  if (window.matchMedia("(max-width: 1020px)").matches) {
    document.querySelector("#results").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderSummary(recommendations) {
  const scores = recommendations.map((project) => Number(project.match_percentage));
  const best = Math.max(...scores);
  const average = scores.reduce((sum, value) => sum + value, 0) / scores.length;

  elements.summary.innerHTML = `
    <div class="stat"><span>Projects ranked</span><b>${recommendations.length}</b></div>
    <div class="stat"><span>Best match</span><b class="grad">${best.toFixed(1)}<small>%</small></b></div>
    <div class="stat"><span>Average match</span><b>${average.toFixed(1)}<small>%</small></b></div>
  `;
  elements.summary.classList.remove("hidden");
}

function createProjectCard(project, index) {
  const score = Number(project.match_percentage);
  return `
    <article class="project-card glass spot" style="--i: ${index}">
      <span class="rank-badge" aria-label="Rank ${index + 1}">${index + 1}</span>
      <div class="card-main">
        <div class="badge-row">
          <span class="badge level ${levelClass(project.skill_level)}">${escapeHtml(project.skill_level)}</span>
          <span class="badge">${escapeHtml(project.domain)}</span>
        </div>
        <h3>${escapeHtml(project.title)}</h3>
        <p>${escapeHtml(project.description)}</p>
        <div class="card-meta">
          <span>${icon("clock")}${escapeHtml(project.available_time)}</span>
          <span>${icon("code")}${escapeHtml(project.preferred_language)}</span>
          <button class="text-button" type="button" data-project-id="${escapeHtml(project.project_id)}">
            View plan ${icon("arrow")}
          </button>
        </div>
      </div>
      <div class="score" role="img" aria-label="${score.toFixed(1)} percent match">
        <svg viewBox="0 0 52 52" aria-hidden="true">
          <circle class="track" cx="26" cy="26" r="22"></circle>
          <circle class="arc" cx="26" cy="26" r="22" style="--p: ${Math.min(100, score)}"></circle>
        </svg>
        <b>${Math.round(score)}%</b>
      </div>
    </article>
  `;
}

/* ---------- Project details drawer ---------- */

async function loadProjectDetails(projectId) {
  openDrawer();
  elements.detailTitle.textContent = "Loading project plan";
  elements.detailDescription.textContent = "";
  elements.detailMeta.innerHTML = "";
  clearTabs();

  try {
    const project = await ProjectPilotAPI.project(projectId);
    renderProjectDetails(project);
  } catch (error) {
    elements.detailTitle.textContent = "Could not load the project plan";
    elements.detailDescription.textContent = `${error.message} Close this panel and try again.`;
  }
}

function openDrawer() {
  state.lastFocus = document.activeElement;
  elements.projectDetails.classList.remove("hidden");
  // next frame so the slide-in transition runs
  requestAnimationFrame(() => {
    elements.projectDetails.classList.add("open");
    elements.drawerBackdrop.classList.add("open");
    document.body.classList.add("drawer-open");
    elements.closeDetails.focus();
  });
}

function closeDrawer({ restoreFocus = true } = {}) {
  if (!elements.projectDetails.classList.contains("open")) {
    elements.projectDetails.classList.add("hidden");
    return;
  }
  elements.projectDetails.classList.remove("open");
  elements.drawerBackdrop.classList.remove("open");
  document.body.classList.remove("drawer-open");
  setTimeout(() => {
    if (!elements.projectDetails.classList.contains("open")) {
      elements.projectDetails.classList.add("hidden");
    }
  }, 380);
  if (restoreFocus && state.lastFocus && state.lastFocus.focus) state.lastFocus.focus();
}

function handleDrawerKeys(event) {
  if (!elements.projectDetails.classList.contains("open")) return;

  if (event.key === "Escape") {
    closeDrawer();
    return;
  }

  if (event.key === "Tab") {
    // keep keyboard focus inside the dialog
    const focusable = elements.projectDetails.querySelectorAll("button, a[href]");
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
}

function renderProjectDetails(project) {
  elements.detailTitle.textContent = project.title;
  elements.detailDescription.textContent = project.description;
  elements.detailMeta.innerHTML = `
    <span class="badge level ${levelClass(project.skill_level)}">${escapeHtml(project.skill_level)}</span>
    <span class="badge">${icon("clock")}${escapeHtml(project.available_time)}</span>
    <span class="badge">${escapeHtml(project.domain)}</span>
    <span class="badge">${icon("code")}${escapeHtml(project.preferred_language)}</span>
  `;

  renderInfoBlocks("tab-roadmap", [["Learning roadmap", project.learning_roadmap, "route", "steps"]]);
  renderInfoBlocks("tab-skills", [
    ["Skills required", project.required_skills, "wrench", "tags"],
    ["Required libraries", project.required_libraries, "layers", "tags"],
  ]);
  renderInfoBlocks("tab-resources", [
    ["Free dataset links", project.free_datasets, "database", "list"],
    ["Free API information", project.free_apis, "globe", "list"],
    ["Learning resources", project.learning_resources, "book", "list"],
  ]);
  renderInfoBlocks("tab-future", [["Future scope", project.future_scope, "rocket", "list"]]);

  activateTab("roadmap");
}

function clearTabs() {
  document.querySelectorAll(".tab-content").forEach((tab) => {
    tab.innerHTML = "";
  });
}

function renderInfoBlocks(containerId, sections) {
  const container = document.querySelector(`#${containerId}`);
  container.innerHTML = sections
    .map(([title, items, iconName, kind]) => {
      let body;

      if (kind === "steps" && items.length) {
        body = `<ol class="steps-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>`;
      } else if (kind === "tags" && items.length) {
        body = `<div class="tag-list">${items.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")}</div>`;
      } else {
        const listItems = items.length
          ? items.map(renderListItem).join("")
          : `<li class="muted">Not required</li>`;
        body = `<ul class="bullet-list">${listItems}</ul>`;
      }

      return `
        <article class="info-block">
          <h3>${icon(iconName)}${escapeHtml(title)}</h3>
          ${body}
        </article>
      `;
    })
    .join("");
}

function renderListItem(item) {
  // "Not applicable - Not applicable" means the project needs nothing here.
  const parts = String(item).split(" - ").map((part) => part.trim().toLowerCase());
  if (parts.every((part) => part === "not applicable")) {
    return `<li class="muted">Not required</li>`;
  }
  return `<li>${linkify(escapeHtml(item))}</li>`;
}

function activateTab(tabName) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    const active = button.dataset.tab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });

  document.querySelectorAll(".tab-content").forEach((content) => {
    content.classList.toggle("active", content.id === `tab-${tabName}`);
  });
}

/* ---------- Errors, status & helpers ---------- */

function renderApiError(message) {
  elements.resultsGrid.innerHTML = "";
  elements.summary.innerHTML = "";
  elements.summary.classList.add("hidden");
  elements.resultsSub.textContent = "The request did not complete.";
  elements.emptyState.classList.remove("hidden");
  elements.emptyState.innerHTML = `
    <span class="empty-icon error">${icon("alert")}</span>
    <strong>Unable to reach the backend</strong>
    <p>${escapeHtml(message)} Check that the API is running, then try again.</p>
    <button class="button button-ghost" type="button" id="retryButton">${icon("refresh")}Try again</button>
  `;
  document.querySelector("#retryButton").addEventListener("click", () => elements.form.requestSubmit());
}

function setApiStatus(message, status) {
  elements.apiStatus.textContent = message;
  elements.apiStatus.classList.remove("online", "offline");
  if (status) elements.apiStatus.classList.add(status);
}

function showError(message) {
  elements.formError.textContent = message;
}

function clearError() {
  elements.formError.textContent = "";
}

function levelClass(level) {
  const normalized = String(level).toLowerCase();
  return ["beginner", "intermediate", "advanced"].includes(normalized) ? normalized : "";
}

function linkify(text) {
  // `text` is already HTML-escaped. Turn any URL inside it into a safe link.
  return text.replace(/https?:\/\/[^\s<]+/g, (url) => {
    return `<a href="${url}" target="_blank" rel="noreferrer noopener">${url}</a>`;
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
