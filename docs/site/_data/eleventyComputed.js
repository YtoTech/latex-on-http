/**
 * Relative root prefix for the current page, so every link in the site works
 * no matter where it is served from (/docs/ route of the API, a static file
 * server, file://, a project page...).
 *
 * Page at /api/builds-sync/ -> "../..", page at / -> "".
 */
export default {
  rootPrefix: (data) => {
    const segments = String(data.page.url || "/")
      .split("/")
      .filter(Boolean);
    return "../".repeat(segments.length);
  },
};
