// BK Charterline page (#177): the analytics demo. Each chart is drawn from
// the data table in its figure, so the table stays the one source and the
// page reads the same without JavaScript. Bars grow with a scale, never a
// width, and only once, when they come into view (Animation Guide).
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var motion = window.DFMotion || { on: function () { return false; } };

  function el(name, cls, parent) {
    var node = document.createElement(name);
    if (cls) node.className = cls;
    if (parent) parent.appendChild(node);
    return node;
  }

  function svg(name, attrs, parent) {
    var node = document.createElementNS(NS, name);
    Object.keys(attrs).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    parent.appendChild(node);
    return node;
  }

  function rows(figure) {
    return Array.prototype.map.call(figure.querySelectorAll("tbody tr"), function (tr) {
      var shown = tr.querySelector("td").textContent.trim();
      return { label: tr.querySelector("th").textContent.trim(), shown: shown,
               value: parseFloat(shown.replace(/,/g, "")) || 0 };
    });
  }

  // Horizontal bars, or a funnel: each step also shows its share of the step before.
  function bars(figure, data, funnel) {
    var max = Math.max.apply(null, data.map(function (d) { return d.value; })) || 1;
    var list = el("div", "hbars");
    data.forEach(function (d, i) {
      var row = el("div", "hbar", list);
      el("span", "hbar-label", row).textContent = d.label;
      var track = el("span", "hbar-track", row);
      var fill = el("span", "hbar-fill", track);
      fill.style.setProperty("--v", d.value / max);
      fill.style.setProperty("--i", Math.min(i, 8));
      var value = el("span", "hbar-value", row);
      value.textContent = d.shown;
      if (funnel && i > 0) {
        el("span", "hbar-step", value).textContent = Math.round(100 * d.value / data[i - 1].value) + "%";
      }
    });
    return list;
  }

  // Columns, with the ones over a limit set apart by a ceiling line.
  function columns(figure, data) {
    var max = Math.max.apply(null, data.map(function (d) { return d.value; })) || 1;
    var over = figure.dataset.over;
    var wrap = el("div", "cols");
    data.forEach(function (d, i) {
      var col = el("div", "col" + (d.label === over ? " col-over" : ""), wrap);
      el("span", "col-value", col).textContent = d.shown;
      var bar = el("span", "col-bar", col);
      var fill = el("span", "col-fill", bar);
      fill.style.setProperty("--v", d.value / max);
      fill.style.setProperty("--i", Math.min(i, 8));
      el("span", "col-label", col).textContent = d.label;
    });
    if (over) {
      var box = el("div", "cols-box");
      box.appendChild(wrap);
      el("p", "cols-note", box).textContent = "Dashed line: the 400-line ceiling of Law 31.";
      return box;
    }
    return wrap;
  }

  // A line with a soft area under it, revealed left to right by a mask.
  var lineCount = 0;
  function line(figure, data) {
    var W = 320, H = 150, L = 36, R = 10, T = 14, B = 26;
    var max = Math.max.apply(null, data.map(function (d) { return d.value; }));
    var unit = figure.dataset.unit || "";
    var top = unit === "%" ? 100 : Math.ceil(max / 5000) * 5000;
    var x = function (i) { return L + (W - L - R) * i / (data.length - 1); };
    var y = function (v) { return T + (H - T - B) * (1 - v / top); };
    var box = el("div", "line-chart");
    var root = svg("svg", { viewBox: "0 0 " + W + " " + H, "aria-hidden": "true", focusable: "false" }, box);
    var id = "reveal-" + (++lineCount);
    var clip = svg("clipPath", { id: id }, svg("defs", {}, root));
    svg("rect", { x: 0, y: 0, width: W, height: H, class: "reveal" }, clip);
    [0, top / 2, top].forEach(function (v) {
      svg("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid" }, root);
      svg("text", { x: L - 6, y: y(v) + 3, class: "axis", "text-anchor": "end" }, root)
        .textContent = (v >= 1000 ? Math.round(v / 1000) + "k" : v) + (unit && v === top ? unit : "");
    });
    var points = data.map(function (d, i) { return x(i) + "," + y(d.value); });
    var g = svg("g", { "clip-path": "url(#" + id + ")" }, root);
    svg("path", { d: "M" + x(0) + "," + y(0) + " L" + points.join(" L") + " L" + x(data.length - 1) + "," + y(0) + " Z", class: "area" }, g);
    svg("polyline", { points: points.join(" "), class: "stroke" }, g);
    data.forEach(function (d, i) {
      svg("circle", { cx: x(i), cy: y(d.value), r: i === data.length - 1 ? 4 : 2.5, class: i === data.length - 1 ? "end" : "dot" }, g);
      svg("text", { x: x(i), y: H - 8, class: "axis", "text-anchor": "middle" }, root).textContent = d.label.replace("Week ", "W");
    });
    var last = data[data.length - 1];
    svg("text", { x: x(data.length - 1) - 6, y: y(last.value) - 9, class: "end-label", "text-anchor": "end" }, root)
      .textContent = last.shown + unit;
    return box;
  }

  var charts = { bars: bars, funnel: function (f, d) { return bars(f, d, true); }, columns: columns, line: line };

  document.querySelectorAll("figure[data-chart]").forEach(function (figure) {
    var draw = charts[figure.dataset.chart];
    var data = rows(figure);
    if (!draw || !data.length) return;
    var chart = draw(figure, data);
    chart.setAttribute("aria-hidden", "true");
    figure.insertBefore(chart, figure.querySelector("details"));
    figure.querySelector("details").open = false;  // the table stays one click away
    figure.classList.add("drawn");
  });

  // Animate a figure once, the first time it is seen.
  function grow(figure) {
    if (!motion.on() || figure.dataset.grown) return;
    figure.dataset.grown = "1";
    figure.classList.add("grow");
  }
  var observer = "IntersectionObserver" in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting && e.target.offsetParent !== null) { grow(e.target); observer.unobserve(e.target); }
    });
  }, { threshold: 0.3 }) : null;

  // Tabs (ARIA tabs pattern): without JavaScript every panel shows, stacked.
  var tablist = document.querySelector(".tabs[role=tablist]");
  if (!tablist) return;
  var tabs = Array.prototype.slice.call(tablist.querySelectorAll("[role=tab]"));
  var panels = tabs.map(function (t) { return document.getElementById(t.getAttribute("aria-controls")); });
  tablist.hidden = false;

  function select(index, focus) {
    tabs.forEach(function (tab, i) {
      var on = i === index;
      tab.setAttribute("aria-selected", on ? "true" : "false");
      tab.tabIndex = on ? 0 : -1;
      panels[i].hidden = !on;
    });
    if (focus) tabs[index].focus();
    panels[index].querySelectorAll("figure.drawn").forEach(function (f) {
      if (observer && !f.dataset.grown) observer.observe(f);
    });
  }

  tabs.forEach(function (tab, i) {
    tab.addEventListener("click", function () { select(i, false); });
    tab.addEventListener("keydown", function (e) {
      var next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (next === undefined) return;
      e.preventDefault();
      select((next + tabs.length) % tabs.length, true);
    });
  });
  select(0, false);
})();
