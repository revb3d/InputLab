const RELEASE_API = "https://api.github.com/repos/revb3d/InputLab/releases/latest";
const RELEASE_FALLBACK_PAGE = "https://github.com/revb3d/InputLab/releases/latest";
const FALLBACK_INSTALLER = "https://github.com/revb3d/InputLab/releases/latest/download/InputLabSetup.exe";

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "Unknown";
  }
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(dateString) {
  if (!dateString) {
    return "Unknown";
  }
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function assignHref(selector, href) {
  document.querySelectorAll(selector).forEach((node) => {
    node.href = href;
  });
}

function assignText(selector, value) {
  document.querySelectorAll(selector).forEach((node) => {
    node.textContent = value;
  });
}

function updateReleaseNotes(value) {
  const fallback = "Latest public build for InputLab. Open the release page if the GitHub API rate limit is reached.";
  document.querySelectorAll("[data-release-notes]").forEach((node) => {
    node.textContent = value && value.trim() ? value.trim() : fallback;
  });
}

async function hydrateReleaseData() {
  assignHref("[data-release-link]", RELEASE_FALLBACK_PAGE);
  assignHref("[data-download-latest]", FALLBACK_INSTALLER);

  try {
    const response = await fetch(RELEASE_API, {
      headers: {
        Accept: "application/vnd.github+json",
      },
    });
    if (!response.ok) {
      throw new Error(`GitHub release request failed: ${response.status}`);
    }

    const release = await response.json();
    const installer = release.assets?.find((asset) => /\.exe$/i.test(asset.name)) || release.assets?.[0];
    const version = release.tag_name || release.name || "Latest build";
    const downloadUrl = installer?.browser_download_url || FALLBACK_INSTALLER;
    const releaseUrl = release.html_url || RELEASE_FALLBACK_PAGE;

    assignText("[data-latest-version]", version);
    assignText("[data-published-at]", formatDate(release.published_at));
    assignText("[data-asset-size]", formatBytes(installer?.size));
    assignHref("[data-download-latest]", downloadUrl);
    assignHref("[data-release-link]", releaseUrl);
    updateReleaseNotes(release.body);
  } catch (_error) {
    assignText("[data-latest-version]", "Latest public build");
    assignText("[data-published-at]", "GitHub release feed");
    assignText("[data-asset-size]", "Latest installer");
    updateReleaseNotes("");
  }
}

function setupReveals() {
  const nodes = document.querySelectorAll(".reveal");
  if (!nodes.length) {
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.16,
  });

  nodes.forEach((node) => observer.observe(node));
}

document.addEventListener("DOMContentLoaded", () => {
  setupReveals();
  hydrateReleaseData();
});
