#!/usr/bin/env python3
"""Build a user's private dashboard (#120) in ~/.bk-charterline/dashboard/: an
overview and a Tools and calls page, in the site's styles, opened from the file.
Each page carries its own CSS and JS, so it shows styled even where only the HTML
file is read (the Claude app's browser pane, #234).

    python3 scripts/my_metrics.py [--local-only] [--if-changed]
"""
from __future__ import annotations

import datetime
import html
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import my_metrics_data as data  # noqa: E402

REPO = os.path.dirname(HERE)
ASSETS = os.path.join(HERE, "dashboard_assets")
CSS = [os.path.join(REPO, "site", f) for f in ("styles.css", "layout.css", "numbers.css", "demo.css", "charts.css")] \
    + [os.path.join(ASSETS, "dashboard.css")]
JS = [os.path.join(REPO, "site", f) for f in ("site.js", "charts.js")]
SOURCES = ("hook-log.jsonl", "ai-approvals.jsonl", "ai-tools.json", "ai-inventory.json", "projects.yaml")
SEV = {4: ("Critical", "critical", "Asks you every time"), 3: ("High", "high", "Asks you once per session"),
       2: ("Low", "low", "Reads only; no question"), 1: ("Minimal", "minimal", "Stays on your machine; no question")}
with open(os.path.join(ASSETS, "actions.json")) as f:
    WORDS = json.load(f)
e = html.escape


def action(label: str, tool: str | None, tier: int) -> str:
    if label in ("Built-in browser", "Claude in Chrome") and tool and tier >= 3:
        return WORDS["web_actions"]
    words = WORDS["actions"].get(label, {})
    return words.get(tool or "*") or (tool or "").replace("_", " ") or words.get("*") or "Uses " + label


def area(label: str) -> str:
    return WORDS["areas"].get(label) or ("Claude app" if label.startswith("App ") else "Design and dev tools")


def by_severity(tools: list[dict]) -> dict:
    """tier -> {tool label: (area, [what it can do])}, riskiest areas first."""
    out = {t: {} for t in SEV}
    for t in tools:
        label, tier = t["label"], t["tier"] if t["tier"] in SEV else 3
        out[tier].setdefault(label, (area(label), []))[1].append(action(label, None, tier))
        for tool, raised in t["overrides"].items():
            if raised in SEV and raised > tier:
                out[raised].setdefault(label, (area(label), []))[1].append(action(label, tool, raised))
    order = WORDS["area_order"]
    return {tier: dict(sorted(group.items(), key=lambda kv: (order.index(kv[1][0]) if kv[1][0] in order else 99, kv[0])))
            for tier, group in out.items()}


def call_row(call: dict, tools: list[dict]) -> tuple[str, str, str, str, str]:
    _, server, tool = (call["tool"].split("__", 2) + ["", ""])[:3]
    entry = next((t for t in tools if t["key"] == "mcp:" + server), {"label": server, "tier": 3, "overrides": {}})
    tier = 4 if call["critical"] else entry["overrides"].get(tool, max(entry["tier"], 3))
    when = data.parse_ts(call["ts"]).strftime("%b %-d, %H:%M")
    return when, SEV[min(tier, 4)][1], entry["label"], action(entry["label"], tool, tier), tool


def figure(kind: str, caption: str, head: tuple, rows: list, extra: str = "") -> str:
    body = "".join(f'<tr><th scope="row">{e(str(a))}</th><td>{b}</td></tr>' for a, b in rows)
    return (f'<figure class="card{" card-wide" if kind == "columns" else ""}" data-chart="{kind}"{extra}><figcaption>{caption}</figcaption>'
            f'<details open><summary>Show data</summary><table><thead><tr><th scope="col">{head[0]}</th><th scope="col">{head[1]}</th></tr>'
            f"</thead><tbody>{body}</tbody></table></details></figure>")


def section(eyebrow: str, title: str, body: str, sid: str = "") -> str:
    sid = f' id="{sid}"' if sid else ""
    return (f'<section class="section"{sid}><div class="section-head">'
            f'<p class="eyebrow">{eyebrow}</p><h2>{title}</h2></div>{body}</section>')


def duration(hours: float | None) -> str:
    if hours is None:
        return "–"
    return f"{max(1, round(hours * 60))} min" if hours < 1 else f"{hours:.1f} h"


def empty(part: dict) -> str:
    return f'<p class="empty">{e(part["error"])}</p>'


def inline(tag: str, paths: list) -> str:
    out = ""
    for path in paths:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if "</" + tag in text.lower():
            raise ValueError(f"{path} contains </{tag}, which would end the inline block early")
        out += f"<{tag}>\n{text}</{tag}>"
    return out


def page(title: str, main: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<script>try {{ var t = localStorage.getItem("df-theme"); if (t === "light" || t === "dark") document.documentElement.dataset.theme = t; }} catch (e) {{}}</script>
{inline("style", CSS)}</head>
<body><header class="top"><div class="page top-inner"><a class="brand" href="index.html">My BK Charterline</a>
<nav aria-label="Pages"><a href="index.html">Overview</a><a href="tools.html">Tools and calls</a></nav>
<fieldset class="theme" hidden><legend class="visually-hidden">Theme</legend>{"".join(
    f'<label><input type="radio" name="theme" id="theme-{v}" value="{v}"{" checked" if v == "system" else ""}><span>{v.title()}</span></label>'
    for v in ("system", "light", "dark"))}</fieldset></div></header>
<div class="page"><main>{main}</main>
<footer class="bottom"><p>Private: built on this machine from your own data. Nothing is committed or sent anywhere.</p></footer></div>
{inline("script", JS)}</body></html>
"""


def overview(d: dict) -> str:
    act, tools, prs = d["activity"], d["tools"], d["pull_requests"]
    sizes = [n for p in prs.get("projects", []) for n in p["sizes"]]
    within = f"{round(100 * sum(1 for n in sizes if n <= 400) / len(sizes))}%" if sizes else "–"
    stats = "".join(f'<div class="stat"><dt>{a}</dt><dd><span>{b}</span></dd><dd class="stat-date">{c}</dd></div>' for a, b, c in (
        ("Hook blocks", sum(x["count"] for x in act.get("blocks", [])), "stopped before they happened"),
        ("Permission prompts", sum(x["count"] for x in act.get("asks", [])), "you decided"),
        ("Pull requests within 400 lines", within, f"{len(sizes)} merged")))
    main = section(f"Private · last {d['window_days']} days", "Your rules at work", f'<dl class="stats">{stats}</dl>')
    if "error" in tools:
        tiles = empty(tools)
    else:
        groups, tiles = by_severity(tools["tools"]), ""
        for tier, (name, cls, rule) in SEV.items():
            names = list(groups[tier])
            chips = "".join(f"<li>{e(n)}</li>" for n in names[:4]) + (f'<li class="more">+{len(names) - 4} more</li>' if len(names) > 4 else "")
            tiles += (f'<a class="sev sev-{cls}" href="tools.html#{cls}"><div class="sev-head"><span class="sev-name">{name}</span>'
                      f'<span class="sev-num">{len(names)}</span></div><span class="sev-rule">{rule}</span><ul class="chips">{chips}</ul></a>')
        tiles = f'<div class="sev-grid">{tiles}</div>'
        if tools["unrated"]:
            tiles += (f'<div class="unrated"><div class="unrated-text"><strong>{len(tools["unrated"])} new tools not rated yet</strong>'
                      '<span>Treated as High until you rate them. <a href="tools.html#unrated">See them</a></span></div>'
                      '<div class="cmd"><code id="cmd-classify">ai classify</code><button type="button" data-copy="cmd-classify" '
                      'data-copied="Copied. Paste it into Claude Code and press Enter." aria-describedby="cmd-status">Copy command</button></div>'
                      '<p class="cmd-status" id="cmd-status" role="status">Paste it into Claude Code to rate them.</p></div>')
    main += section("Tools", "What Claude can reach, by severity", tiles + '<a class="see" href="tools.html">See every tool and what it can do →</a>')
    if "error" in act or not act["calls"]:
        feed = empty(act) if "error" in act else '<p class="empty">Your first approved call shows up here.</p>'
    else:
        feed = "".join(f'<li><time>{w}</time><span class="dot sev-{c}"></span><span><span class="visually-hidden">{c.title()}: </span><strong>{e(l)}</strong> · {e(a)}</span></li>'
                       for w, c, l, a, _ in (call_row(x, tools.get("tools", [])) for x in act["calls"][:5]))
        feed = f'<div class="card"><ul class="feed">{feed}</ul></div><a class="see" href="tools.html#calls">See every call →</a>'
    main += section("Calls", "Latest tools you approved", feed)
    if "error" in act:
        charts = empty(act)
    else:
        checks = WORDS["checks"]
        bars = [(f"{b['law']} · {checks.get(b['check'], b['check'])}", b["count"]) for b in act["blocks"]]
        asks = [(checks.get(a["check"], a["check"]), a["count"]) for a in act["asks"]]
        cols = {k: 0 for k in ("0–100", "101–200", "201–300", "301–400", "Over 400")}
        for n in sizes:
            cols["Over 400" if n > 400 else list(cols)[min((max(n, 1) - 1) // 100, 3)]] += 1
        charts = '<div class="cards">' + (figure("bars", "Blocks per law", ("Law · check", "Blocks"), bars) if bars else "") + (
            figure("bars", "Prompts, by kind", ("Kind", "Prompts"), asks) if asks else "") + (
            figure("columns", "Pull request size", ("Lines changed", "Pull requests"), list(cols.items()), ' data-over="Over 400"') if sizes else "") + "</div>"
    return page("My BK Charterline", main + section("Activity", "What the hook did", charts))


def tools_page(d: dict) -> str:
    tools, main = d["tools"], ""
    if "error" in tools:
        main = section("Tools", "What Claude can reach", empty(tools))
    else:
        groups = by_severity(tools["tools"])
        for tier, (name, cls, rule) in SEV.items():
            cards = "".join(f'<article class="tool sev-{cls}"><span class="area">{e(a)}</span><h3>{e(l)}</h3><ul>'
                            + "".join(f"<li>{e(x)}</li>" for x in sorted(set(acts))) + "</ul></article>" for l, (a, acts) in groups[tier].items())
            main += section(rule, name, f'<div class="tool-grid">{cards or "<p class=empty>None.</p>"}</div>', cls)
        if tools["unrated"]:
            main += section("Treated as High until rated", "Not rated yet",
                            '<ul class="chips">' + "".join(f"<li>{e(u)}</li>" for u in tools["unrated"]) + "</ul>", "unrated")
    act = d["activity"]
    rows = "".join(f'<tr><td>{w}</td><td><span class="dot sev-{c}"></span> {c.title()}</td><td><strong>{e(l)}</strong></td><td>{e(a)}</td>'
                   f"<td><code>{e(t)}</code></td></tr>" for w, c, l, a, t in (call_row(x, tools.get("tools", [])) for x in act.get("calls", [])))
    head = "".join(f'<th scope="col">{h}</th>' for h in ("When", "Severity", "Tool", "What it can do", "Call"))
    main += section(f"Last {d['window_days']} days · UTC", "Every High and Critical call",
                    f'<div class="table" tabindex="0" role="region" aria-label="Every call"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>' if rows
                    else (empty(act) if "error" in act else '<p class="empty">No calls yet.</p>'), "calls")
    prs = d["pull_requests"]
    if "error" in prs:
        body = empty(prs)
    else:
        cells = lambda p: ([e(p["error"])] if p["error"] and not p["merged"] else [p["merged"], p["median_lines"] or "–", f'{p["within_400"]}%' if p["within_400"] is not None else "–",
                           duration(p["median_hours"]), p["reverts"], f'{p["claude_share"]}%' if p["claude_share"] is not None else "–"])
        rows = "".join(f'<tr><th scope="row">{e(p["name"])}</th>' + "".join(f'<td{" colspan=6" if len(cells(p)) == 1 else ""}>{c}</td>' for c in cells(p)) + "</tr>"
                       for p in prs["projects"])
        head = "".join(f'<th scope="col">{h}</th>' for h in ("Project", "Merged", "Median lines", "Within 400", "Median time to merge", "Reverts", "Made with Claude Code"))
        body = f'<div class="table" tabindex="0" role="region" aria-label="Pull requests per project"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>' if rows else '<p class="empty">No projects with a repo in projects.yaml.</p>'
    return page("Tools and calls · My BK Charterline", main + section(f"Last {d['window_days']} days", "Pull requests per project", body, "projects"))


def write(path: str, text: str) -> None:
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)  # each file is whole, even if two sessions build at once


def fingerprint(home: str) -> list:
    out = []
    for name in SOURCES:
        try:
            st = os.stat(os.path.join(home, name))
            out.append([name, st.st_size, int(st.st_mtime)])
        except OSError:
            out.append([name, None, None])
    return out


def build(home: str | None = None, *, network: bool = True, if_changed: bool = False, gh: str = "gh") -> str:
    home = home or data.rules_home()
    out = os.path.join(home, "dashboard")
    stamp = os.path.join(out, "fingerprint.json")
    now = fingerprint(home)
    if if_changed and os.path.exists(os.path.join(out, "index.html")):
        try:
            with open(stamp) as f:
                if json.load(f) == now:
                    return "unchanged"
        except (OSError, ValueError):
            pass
    d = data.collect(home, network=network, gh=gh)
    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, "tools.html"), tools_page(d))
    write(os.path.join(out, "index.html"), overview(d))
    write(stamp, json.dumps(now))
    return os.path.join(out, "index.html")


if __name__ == "__main__":
    result = build(network="--local-only" not in sys.argv, if_changed="--if-changed" in sys.argv)
    print("my metrics: nothing changed" if result == "unchanged" else f"my metrics: {result}")
