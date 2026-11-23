const ProjectPilotAPI = (() => {
  // Deployed backend. To point at a local server instead, set
  // `window.PROJECTPILOT_API_BASE = "http://127.0.0.1:8000"` before this script loads.
  const API_BASE_URL = window.PROJECTPILOT_API_BASE || "https://pilot-ai-8hig.onrender.com";

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    if (!response.ok) {
      const message = await getErrorMessage(response);
      throw new Error(message);
    }

    return response.json();
  }

  async function getErrorMessage(response) {
    try {
      const data = await response.json();
      return data.detail || "Something went wrong. Please try again.";
    } catch {
      return "Something went wrong. Please try again.";
    }
  }

  return {
    health: () => request("/health"),
    options: () => request("/options"),
    project: (projectId) => request(`/projects/${projectId}`),
    recommend: (payload) =>
      request("/recommend", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  };
})();
