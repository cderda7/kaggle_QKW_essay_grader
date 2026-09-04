// Linking a judgment to its evidence, in both directions.
//
// Focusing a trait repaints everything that trait cited in THAT trait's colour and direction, and
// fades the rest. The resting colour of a passage belongs to whichever span is outermost, which is
// the right default when reading the whole response — but the moment a reader asks "what did
// conventions look at?", a conventions citation must read as conventions even if an organization
// span wraps it. Per-criterion classes on each mark (has-*, pol-*-*) let CSS do that repaint.
//
// Hover previews a trait; click pins it, so evidence can be studied without holding the pointer
// still. Escape, or clicking the pinned card again, releases it.

(function () {
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card[data-criterion]"));
  var marks = Array.prototype.slice.call(document.querySelectorAll("mark.hl"));
  if (!cards.length) return;

  var names = cards.map(function (c) { return c.getAttribute("data-criterion"); });
  var body = document.body;
  var pinned = null;

  function criteriaOf(mark) {
    return (mark.getAttribute("data-criteria") || "").split(/\s+/).filter(Boolean);
  }

  function paint(active) {
    body.classList.toggle("focusing", active.length > 0);
    names.forEach(function (n) {
      body.classList.toggle("focus-" + n, active.indexOf(n) !== -1);
    });
    cards.forEach(function (card) {
      var name = card.getAttribute("data-criterion");
      var hit = active.indexOf(name) !== -1;
      card.classList.toggle("active", hit && active.length > 0);
      card.classList.toggle("dim", active.length > 0 && !hit);
      card.classList.toggle("pinned", pinned === name);
    });
  }

  function show(active) {
    if (pinned) return;             // a pin outranks hover
    paint(active);
  }

  function rest() {
    paint(pinned ? [pinned] : []);
  }

  cards.forEach(function (card) {
    var name = card.getAttribute("data-criterion");

    card.addEventListener("mouseenter", function () { show([name]); });
    card.addEventListener("mouseleave", rest);
    card.addEventListener("focus", function () { show([name]); });
    card.addEventListener("blur", rest);

    card.addEventListener("click", function () {
      pinned = pinned === name ? null : name;
      paint(pinned ? [pinned] : []);
    });
    card.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        pinned = pinned === name ? null : name;
        paint(pinned ? [pinned] : []);
      }
    });
  });

  marks.forEach(function (mark) {
    mark.addEventListener("mouseenter", function () { show(criteriaOf(mark)); });
    mark.addEventListener("mouseleave", rest);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && pinned) {
      pinned = null;
      paint([]);
    }
  });
})();
