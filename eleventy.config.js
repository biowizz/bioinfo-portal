const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

function loadListings(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((file) => file.endsWith(".yaml") || file.endsWith(".yml"))
    .map((file) => {
      const raw = fs.readFileSync(path.join(dir, file), "utf8");
      const data = yaml.load(raw) || {};
      data.slug = file.replace(/\.ya?ml$/, "");
      return data;
    });
}

module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("site/style.css");
  eleventyConfig.addPassthroughCopy("site/app.js");

  eleventyConfig.addGlobalData("conferences", () =>
    loadListings(path.join(__dirname, "data/conferences"))
  );

  eleventyConfig.addGlobalData("jobs", () =>
    loadListings(path.join(__dirname, "data/jobs"))
  );

  eleventyConfig.addGlobalData("listings", () => {
    const conferences = loadListings(path.join(__dirname, "data/conferences"));
    const jobs = loadListings(path.join(__dirname, "data/jobs"));
    return [...conferences, ...jobs];
  });

  return {
    dir: {
      input: "site",
      output: "_site",
      layouts: "_layouts",
    },
  };
};
