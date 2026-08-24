(function () {
  var grid = document.querySelector("[data-card-grid]");
  if (!grid) return;

  var bar = document.querySelector("[data-filter-bar]");
  var typeSelect = bar.querySelector("[data-filter-type]");
  var tagSelect = bar.querySelector("[data-filter-tag]");
  var sortSelect = bar.querySelector("[data-sort-deadline]");
  var countEl = bar.querySelector("[data-filter-count]");
  var emptyState = document.querySelector("[data-empty-state]");

  var cards = Array.prototype.slice.call(grid.querySelectorAll(".card"));

  function populateTags() {
    var tagSet = new Set();
    cards.forEach(function (card) {
      (card.dataset.tags || "")
        .split("|")
        .filter(Boolean)
        .forEach(function (tag) {
          tagSet.add(tag);
        });
    });
    Array.from(tagSet)
      .sort()
      .forEach(function (tag) {
        var option = document.createElement("option");
        option.value = tag;
        option.textContent = tag;
        tagSelect.appendChild(option);
      });
  }

  function render() {
    var typeValue = typeSelect ? typeSelect.value : "all";
    var tagValue = tagSelect.value;
    var sortDir = sortSelect.value;

    var visible = cards.filter(function (card) {
      var matchesType = typeValue === "all" || card.dataset.type === typeValue;
      var tags = (card.dataset.tags || "").split("|");
      var matchesTag = tagValue === "all" || tags.indexOf(tagValue) !== -1;
      return matchesType && matchesTag;
    });

    visible.sort(function (a, b) {
      var deadlineA = a.dataset.deadline;
      var deadlineB = b.dataset.deadline;
      if (!deadlineA && !deadlineB) return 0;
      if (!deadlineA) return 1;
      if (!deadlineB) return -1;
      var cmp = deadlineA.localeCompare(deadlineB);
      return sortDir === "desc" ? -cmp : cmp;
    });

    cards.forEach(function (card) {
      card.hidden = true;
    });
    visible.forEach(function (card) {
      card.hidden = false;
      grid.appendChild(card);
    });

    countEl.textContent = visible.length + " of " + cards.length + " shown";
    emptyState.hidden = visible.length !== 0;
  }

  populateTags();
  if (typeSelect) typeSelect.addEventListener("change", render);
  tagSelect.addEventListener("change", render);
  sortSelect.addEventListener("change", render);
  render();
})();
