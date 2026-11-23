/* ==========================================================================
   Landing page: hydrate live numbers from the real backend.
   Static values in the HTML are the fallback if the API is unreachable.
   ========================================================================== */

(async () => {
  const status = document.querySelector("#heroStatus");

  const setStatus = (text, state) => {
    if (!status) return;
    status.textContent = text;
    status.classList.remove("online", "offline");
    if (state) status.classList.add(state);
  };

  try {
    const health = await ProjectPilotAPI.health();
    setStatus(`${health.total_projects.toLocaleString("en-US")} projects indexed, API online`, "online");
    window.countUp(document.querySelector("#statProjects"), health.total_projects);
  } catch {
    setStatus("Backend is waking up or offline", "offline");
  }

  try {
    const options = await ProjectPilotAPI.options();
    window.countUp(document.querySelector("#statDomains"), options.domains.length);
    window.countUp(document.querySelector("#statLanguages"), options.preferred_languages.length);
    window.countUp(document.querySelector("#statTimes"), options.available_times.length);

    const cloud = document.querySelector("#domainCloud");
    if (cloud && options.domains.length) {
      cloud.innerHTML = options.domains
        .map((domain) => `<span class="chip">${escapeText(domain)}</span>`)
        .join("");
    }
  } catch {
    /* keep static fallback values */
  }

  function escapeText(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }
})();
