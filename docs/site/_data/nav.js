/**
 * Sidebar navigation, shared by every page.
 *
 * `url` is the canonical Eleventy page URL (used to match the active item);
 * `href` is the site-relative link target (prefixed with the page's
 * rootPrefix in the layout), so links work wherever the site is served.
 */
export default [
  {
    title: "Getting started",
    items: [{ title: "Overview", url: "/", href: "index.html" }],
  },
  {
    title: "API reference",
    items: [
      { title: "Compilation", url: "/api/builds-sync/", href: "api/builds-sync/index.html" },
      { title: "Build environment", url: "/api/environment/", href: "api/environment/index.html" },
      { title: "Caches", url: "/api/caches/", href: "api/caches/index.html" },
    ],
  },
  {
    title: "Guides",
    items: [
      { title: "Server code", url: "/guides/server/", href: "guides/server/index.html" },
      { title: "CI pipelines", url: "/guides/ci/", href: "guides/ci/index.html" },
      { title: "Browser (JSON)", url: "/guides/browser/", href: "guides/browser/index.html" },
      {
        title: "Browser (multipart)",
        url: "/guides/browser-multipart/",
        href: "guides/browser-multipart/index.html",
      },
    ],
  },
  {
    title: "Tools",
    items: [{ title: "Live playground", url: "/playground/", href: "playground/index.html" }],
  },
];
