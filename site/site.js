// BK Charterline page (#177): the motion switch, the theme switcher, the copy
// buttons, the real numbers from data.js, the gauges and the entrances.
(function () {
  "use strict";
  var root = document.documentElement;

  // The one place that reads the reduced-motion setting (Animation Guide §2.1).
  // Everything that moves checks data-motion, so a settings toggle can be
  // added later without touching the rest.
  var reduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  function setMotion() {
    root.dataset.motion = reduce && reduce.matches ? "off" : "on";
  }
  setMotion();
  if (reduce && reduce.addEventListener) reduce.addEventListener("change", setMotion);

  function motionOn() {
    return root.dataset.motion === "on";
  }

  function token(name) {
    return parseFloat(getComputedStyle(root).getPropertyValue(name)) || 0;
  }

  window.DFMotion = { on: motionOn, ms: token };

  // Theme switcher: System follows the OS; Light or Dark sets data-theme,
  // which the CSS tokens read. The choice is kept in this browser only.
  var switcher = document.querySelector(".theme");
  if (switcher) {
    var saved = document.getElementById("theme-" + (root.dataset.theme || "system"));
    if (saved) saved.checked = true;
    switcher.hidden = false;
    switcher.addEventListener("change", function (event) {
      var choice = event.target.value;
      if (choice === "system") delete root.dataset.theme;
      else root.dataset.theme = choice;
      try {
        if (choice === "system") localStorage.removeItem("df-theme");
        else localStorage.setItem("df-theme", choice);
      } catch (e) { /* storage is blocked: the choice lasts for this visit */ }
    });
  }

  // Copy buttons: the clipboard when allowed, otherwise select the text.
  document.querySelectorAll("[data-copy]").forEach(function (button) {
    var source = document.getElementById(button.getAttribute("data-copy"));
    var status = document.getElementById(button.getAttribute("aria-describedby"));
    button.addEventListener("click", function () {
      var done = function () { status.textContent = button.dataset.copied || "Copied. Paste it into your terminal."; };
      var fallback = function () {
        var range = document.createRange();
        range.selectNodeContents(source);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        status.textContent = "Selected. Press Ctrl+C or ⌘C to copy.";
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(source.textContent).then(done, fallback);
      } else {
        fallback();
      }
    });
  });

  // Real numbers: data.js is newer than the HTML fallback when the page
  // wasn't rebuilt. A changed number counts on from the value shown, never
  // from 0, and a screen reader gets the final value at once.
  var numbers = (window.DF_METRICS && window.DF_METRICS.numbers) || {};

  function format(name, value) {
    return name === "prs_within_400" ? value + "%" : value.toLocaleString("en-US");
  }

  function formatDate(iso) {
    return new Date(iso + "T00:00:00Z").toLocaleDateString("en-US",
      { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
  }

  function shownValue(el) {
    return parseInt(el.textContent.replace(/[^0-9]/g, ""), 10);
  }

  function countUp(el, name, from, to) {
    var spoken = document.createElement("span");
    spoken.className = "visually-hidden";
    spoken.textContent = format(name, to);
    el.setAttribute("aria-hidden", "true");
    el.after(spoken);
    var duration = token("--motion-count");
    var start = performance.now();
    requestAnimationFrame(function step(now) {
      var t = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = format(name, Math.round(from + (to - from) * eased));
      if (t < 1) return requestAnimationFrame(step);
      el.removeAttribute("aria-hidden");
      spoken.remove();
    });
  }

  document.querySelectorAll("[data-metric]").forEach(function (el) {
    var name = el.dataset.metric;
    var n = numbers[name];
    if (!n || typeof n.value !== "number") return;
    var shown = shownValue(el);
    if (shown === n.value) return;
    if (motionOn() && !isNaN(shown)) countUp(el, name, shown, n.value);
    else el.textContent = format(name, n.value);
  });

  document.querySelectorAll("time[data-metric-date]").forEach(function (el) {
    var n = numbers[el.dataset.metricDate];
    if (!n || !n.as_of) return;
    el.setAttribute("datetime", n.as_of);
    el.textContent = formatDate(n.as_of);
  });

  // Gauges: each fill is its value against a real limit (the 400-line
  // ceiling, the 33,000-token budget). The fill is a scaleX, never a width.
  document.querySelectorAll(".gauge[data-gauge]").forEach(function (gauge) {
    var n = numbers[gauge.dataset.gauge];
    var value = n ? n.value : shownValue(gauge.querySelector("[data-metric]"));
    var max = parseFloat(gauge.dataset.max);
    if (isNaN(value) || !max) return;
    gauge.querySelector(".fill").style.setProperty("--fill", Math.max(0, Math.min(1, value / max)));
  });

  // Entrances: everything rests visible. A section still below the fold
  // grows in once as it starts to scroll into view, and the gauges fill.
  if (!motionOn() || !("IntersectionObserver" in window)) return;
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add(entry.target.classList.contains("gauges") ? "filling" : "enter");
      observer.unobserve(entry.target);
    });
  });
  document.querySelectorAll(".section, .gauges").forEach(function (el) {
    if (el.getBoundingClientRect().top > window.innerHeight) observer.observe(el);
  });
})();
