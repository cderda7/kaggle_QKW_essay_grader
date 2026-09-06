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

// Revealing the human rater's score.
//
// The value is not in this page — the server withheld it — so the click has to go and ask for it,
// and asking is what gets recorded. That ordering is the point: there is no local toggle that could
// show the number without the ledger entry existing (decisions_log.md ui_4). On reload the server
// renders the revealed block itself, so this path runs once per essay.

(function () {
  var block = document.querySelector(".gold[data-essay]:not([data-revealed])");
  if (!block) return;

  var button = block.querySelector(".gold-reveal");
  if (!button) return;

  button.addEventListener("click", function () {
    button.disabled = true;
    button.textContent = "Recording…";

    fetch("/api/gold/" + encodeURIComponent(block.getAttribute("data-essay")), {
      method: "POST",
      headers: { "Accept": "application/json" }
    }).then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    }).then(function (data) {
      var gap = data.gold_score - data.holistic;
      var comparison = gap === 0
        ? "same as this system’s"
        : Math.abs(gap) + (gap > 0 ? " above" : " below") + " this system’s " + data.holistic;

      block.setAttribute("data-revealed", "true");
      block.classList.add("revealed");
      button.remove();

      var value = document.createElement("p");
      value.className = "gold-value";
      value.innerHTML = '<span class="gold-number"></span><span class="of">/6</span>'
        + '<span class="gold-gap"></span>';
      value.querySelector(".gold-number").textContent = String(data.gold_score);
      value.querySelector(".gold-gap").textContent = comparison;
      block.insertBefore(value, block.querySelector(".gold-note"));

      // Same markup the server renders on reload, so one state does not have two looks.
      var note = block.querySelector(".gold-note");
      note.innerHTML = 'Revealed <span class="when"></span>. Corrections to this essay from here '
        + 'on carry <code>gold_revealed: true</code> in their record.';
      note.querySelector(".when").textContent = data.revealed_display;
    }).catch(function (error) {
      button.disabled = false;
      button.textContent = "Reveal the rater’s score";
      var failed = block.querySelector(".gold-error") || document.createElement("p");
      failed.className = "gold-error";
      failed.textContent = "Could not reveal it — nothing was recorded. (" + error.message + ")";
      block.appendChild(failed);
    });
  });
})();
