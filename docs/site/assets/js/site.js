/**
 * LaTeX-on-HTTP documentation — site behaviours:
 * theme toggle, code tabs, copy-to-clipboard, mobile navigation.
 */
(function () {
  "use strict";

  /* ------------------------------ Theme --------------------------------- */

  var THEME_KEY = "loh-docs-theme";

  function applyTheme(theme) {
    if (theme === "dark" || theme === "light") {
      document.documentElement.setAttribute("data-theme", theme);
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }

  function storedTheme() {
    try {
      return window.localStorage.getItem(THEME_KEY);
    } catch (error) {
      return null;
    }
  }

  applyTheme(storedTheme());

  function currentTheme() {
    return (
      document.documentElement.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light")
    );
  }

  var themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    function updateThemeLabel(theme) {
      themeToggle.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
      );
    }

    updateThemeLabel(currentTheme());
    themeToggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      applyTheme(next);
      updateThemeLabel(next);
      try {
        window.localStorage.setItem(THEME_KEY, next);
      } catch (error) {
        /* Storage unavailable: keep the in-memory theme. */
      }
    });
  }

  /* --------------------------- Mobile sidebar --------------------------- */

  var navToggle = document.getElementById("nav-toggle");
  var sidebar = document.getElementById("sidebar");
  if (navToggle && sidebar) {
    navToggle.addEventListener("click", function () {
      var isOpen = sidebar.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
    // Close the sidebar after navigating on mobile.
    sidebar.addEventListener("click", function (event) {
      if (
        event.target instanceof Element &&
        event.target.closest("a.nav-item")
      ) {
        sidebar.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ------------------------------ Code tabs ------------------------------ */

  document.querySelectorAll("[data-tabs]").forEach(function (tabs) {
    var buttons = Array.prototype.slice.call(
      tabs.querySelectorAll(".code-tab")
    );
    var panels = Array.prototype.slice.call(
      tabs.querySelectorAll(".code-tab-panel")
    );

    function select(index) {
      buttons.forEach(function (button, buttonIndex) {
        button.classList.toggle("is-active", buttonIndex === index);
        button.setAttribute(
          "aria-selected",
          String(buttonIndex === index)
        );
      });
      panels.forEach(function (panel, panelIndex) {
        panel.classList.toggle("is-active", panelIndex === index);
        if (panelIndex === index) {
          panel.removeAttribute("hidden");
        } else {
          panel.setAttribute("hidden", "");
        }
      });
    }

    buttons.forEach(function (button, index) {
      button.addEventListener("click", function () {
        select(index);
      });
    });
  });

  /* --------------------------- Copy buttons ----------------------------- */

  function addCopyButton(container) {
    var code = container.querySelector("code");
    if (!code) {
      return;
    }
    var button = document.createElement("button");
    button.type = "button";
    button.className = "code-copy-button";
    button.textContent = "Copy";
    button.addEventListener("click", function () {
      var text = code.textContent || "";
      function fallbackCopy() {
        // Older browsers / non-secure contexts.
        var area = document.createElement("textarea");
        area.value = text;
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        try {
          document.execCommand("copy");
        } finally {
          document.body.removeChild(area);
        }
      }
      var done = function () {
        button.textContent = "Copied!";
        button.classList.add("is-copied");
        window.setTimeout(function () {
          button.textContent = "Copy";
          button.classList.remove("is-copied");
        }, 1600);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(done, function () {
          fallbackCopy();
          done();
        });
      } else {
        fallbackCopy();
        done();
      }
    });
    container.appendChild(button);
  }

  document
    .querySelectorAll(".code-tab-panel, .prose pre[class*='language-']")
    .forEach(addCopyButton);

  /* ------------------------- Heading anchors ---------------------------- */

  document
    .querySelectorAll(".content h2[id], .content h3[id]")
    .forEach(function (heading) {
      var anchor = document.createElement("a");
      anchor.className = "heading-anchor";
      anchor.href = "#" + heading.id;
      anchor.setAttribute("aria-label", "Link to this section");
      anchor.textContent = "#";
      heading.appendChild(anchor);
    });
})();
