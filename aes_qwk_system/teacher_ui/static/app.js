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

// Recording a correction.
//
// Nothing here computes a score. The selects gather what the teacher wants the traits to be, the
// server runs the frozen aggregator and writes the record, and the page reloads to show whatever
// the build produced — including a correction that changed nothing, which is the common case
// (decisions_log.md ui_9). A local preview of the new holistic would be a second implementation of
// a fitted map, and the one place its disagreement would surface is the panel built to be checked.

(function () {
  var form = document.querySelector(".override[data-essay]");
  if (!form) return;

  var essay = form.getAttribute("data-essay");
  var status = form.querySelector(".override-status");
  var selects = Array.prototype.slice.call(document.querySelectorAll(".card-score-select"));

  // A click on the score control must not also pin the trait it sits inside.
  selects.forEach(function (select) {
    ["click", "keydown", "mousedown"].forEach(function (type) {
      select.addEventListener(type, function (event) { event.stopPropagation(); });
    });
    select.addEventListener("change", function () {
      var card = select.closest(".card");
      if (card) card.classList.toggle("dirty", select.value !== select.getAttribute("data-score"));
      var dirty = selects.some(function (s) { return s.value !== s.getAttribute("data-score"); });
      form.classList.toggle("dirty", dirty);
      say(dirty ? "Unsaved change — save it to recompute the score." : "");
    });
  });

  function say(text, bad) {
    status.textContent = text;
    status.classList.toggle("bad", !!bad);
  }

  function post(body, working) {
    var buttons = Array.prototype.slice.call(form.querySelectorAll("button"));
    buttons.forEach(function (b) { b.disabled = true; });
    say(working);

    fetch("/api/override/" + encodeURIComponent(essay), {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(body)
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.detail || ("HTTP " + response.status));
        return data;
      });
    }).then(function () {
      // The server-rendered page is the truth: reload rather than patch the DOM, so the score,
      // the before/after line and the panel's open state all come from the build.
      window.location.reload();
    }).catch(function (error) {
      buttons.forEach(function (b) { b.disabled = false; });
      say("Nothing was recorded — " + error.message, true);
    });
  }

  form.querySelector(".override-save").addEventListener("click", function () {
    // Two different "nothing to do" cases, and they need different advice. Saving an unchanged
    // form would append a record identical to the one already stored: a trail of duplicates says
    // the teacher acted three times when they decided once.
    var changed = selects.some(function (s) { return s.value !== s.getAttribute("data-score"); });
    if (!changed) {
      say("Nothing has changed since your last save.", true);
      return;
    }
    var corrected = {};
    selects.forEach(function (s) {
      if (s.value === s.getAttribute("data-ai")) return;
      corrected[s.getAttribute("name")] = Number(s.value);
    });
    if (!Object.keys(corrected).length) {
      say("Every trait now reads as the AI scored it — use “Clear the trait correction” to "
          + "withdraw it, so the record says what happened.", true);
      return;
    }
    post({
      kind: "trait_correction",
      corrected_traits: corrected,
      rationale: form.querySelector(".override-rationale").value
    }, "Recomputing through the aggregator…");
  });

  var clear = form.querySelector(".override-clear");
  if (clear) {
    clear.addEventListener("click", function () {
      post({ kind: "cleared", rationale: form.querySelector(".override-rationale").value },
           "Withdrawing the correction…");
    });
  }

  var dissent = form.querySelector(".dissent-save");
  if (dissent) {
    dissent.addEventListener("click", function () {
      var why = form.querySelector(".dissent-rationale").value;
      if (!why.trim()) {
        say("A dissent is a reason and no number, so the reason is the whole record.", true);
        return;
      }
      post({ kind: "dissent", rationale: why }, "Recording your dissent…");
    });
  }
})();
