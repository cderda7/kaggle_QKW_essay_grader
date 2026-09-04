// Linking a judgment to its evidence, in both directions.
//
// Hovering a trait card emphasises the passages that trait cited and mutes the rest, so one line of
// reasoning can be isolated in a densely marked response. Hovering a marked passage lights up the
// card (or cards) that cited it, so a reader can work from the text back to the judgment too.
//
// Everything below is attribute work over elements the server already emitted. A segment cited by
// two traits carries both in data-criteria, so it responds to either card.

(function () {
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card[data-criterion]"));
  var marks = Array.prototype.slice.call(document.querySelectorAll("mark.hl"));
  if (!cards.length && !marks.length) return;

  function criteriaOf(mark) {
    return (mark.getAttribute("data-criteria") || "").split(/\s+/).filter(Boolean);
  }

  function clear() {
    marks.forEach(function (m) { m.classList.remove("emph", "mute"); });
    cards.forEach(function (c) { c.classList.remove("active", "dim"); });
  }

  function focusCriteria(names) {
    marks.forEach(function (m) {
      var hit = criteriaOf(m).some(function (n) { return names.indexOf(n) !== -1; });
      m.classList.toggle("emph", hit);
      m.classList.toggle("mute", !hit);
    });
    cards.forEach(function (c) {
      var hit = names.indexOf(c.getAttribute("data-criterion")) !== -1;
      c.classList.toggle("active", hit);
      c.classList.toggle("dim", !hit);
    });
  }

  cards.forEach(function (card) {
    var name = card.getAttribute("data-criterion");
    card.addEventListener("mouseenter", function () { focusCriteria([name]); });
    card.addEventListener("mouseleave", clear);
    // Keyboard parity: the same link is reachable without a pointer.
    card.addEventListener("focus", function () { focusCriteria([name]); });
    card.addEventListener("blur", clear);
  });

  marks.forEach(function (mark) {
    mark.addEventListener("mouseenter", function () { focusCriteria(criteriaOf(mark)); });
    mark.addEventListener("mouseleave", clear);
  });
})();
