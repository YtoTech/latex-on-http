import syntaxHighlight from "@11ty/eleventy-plugin-syntaxhighlight";

// The plugin's paired shortcode implementation, used directly as a filter so
// code samples stored in data files can be highlighted at build time.
const highlighter = syntaxHighlight.pairedShortcode;

export default function (eleventyConfig) {
  eleventyConfig.addPlugin(syntaxHighlight);

  // {{ sample.code | highlightCode("bash") | safe }} → highlighted <pre>.
  eleventyConfig.addNunjucksFilter("highlightCode", (code, language) =>
    highlighter(code, language, "", { lineSeparator: "\n" })
  );

  // Static assets (CSS/JS) are copied as-is to the build output.
  eleventyConfig.addPassthroughCopy({ assets: "assets" });

  // Watch data + assets for rebuilds during `npm run dev`.
  eleventyConfig.addWatchTarget("assets/");

  return {
    // Output outside of the input directory, at docs/_build/.
    dir: {
      input: ".",
      includes: "_includes",
      data: "_data",
      output: "../_build",
    },
    templateFormats: ["njk", "md"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
    // Pretty URLs: /guides/server/ -> guides/server/index.html
    pathPrefix: "/",
  };
}
