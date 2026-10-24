#!/usr/bin/env python3
"""report.py: the report page and the run summary for the branch `filtered`.

Reads the filtered history (every commit carries an Upstream-Commit: trailer), upstream's main and
the fork's `lite`, and writes:

  - index.html: the filtered commits newest first, with a separator where the fork's `lite`
    stands. Above it the commits after the newest upstream commit `lite` has taken - by that definition
    none of them is in `lite`; a cherry-pick out of order moves the line up, and the older commits
    it jumped over show below the line marked "not in lite". Below the line the older ones, capped
    at OLDER_CAP entries;
  - state.json: the upstream commits seen so far, with the date of the run that first saw them, so
    a commit stays marked "new" until a later run brings newer ones;
  - summary.md: the run's summary for $GITHUB_STEP_SUMMARY.

"Taken by lite" (the boundary detection) is, per upstream commit:
  1. an ancestor of lite (everything up to merge-base(lite, main)), or
  2. named by a lite commit's "(cherry picked from commit <sha>)" line or Upstream-Commit: trailer, or
  3. the same change on our paths: the patch-id of the filtered commit (upstream's diff limited to
     the paths file) equals the patch-id of a lite commit's diff limited to the same paths, or
  4. the same subject: a lite commit's subject equals the upstream subject without its " (#N)"
     suffix (upstream squash-merges a PR of ours under the PR's title; the review may have changed
     the diff, so the patch-id differs).
The boundary is the taken upstream commit that is newest in upstream's order.
"""

import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys

UPSTREAM = "https://github.com/OpenCCU/OpenCCU-Base"
OLDER_CAP = 100
TRAILER = re.compile(r"^Upstream-Commit: \S+ " + re.escape(UPSTREAM) + r"/commit/([0-9a-f]{40})\s*$", re.M)
PICKED = re.compile(r"\(cherry picked from commit ([0-9a-f]{40})\)")
LITE_TRAILER = re.compile(r"^Upstream(?:-Commit)?: .*?([0-9a-f]{40})", re.M)
PR = re.compile(r"\(#(\d+)\)\s*$")


def git(repo, *args, data=None):
    r = subprocess.run(["git", "-C", repo, *args], input=data, capture_output=True, check=True)
    return r.stdout.decode("utf-8", "replace")


class Paths:
    """git filter-repo's --paths-from-file matching: a literal path matches itself and everything
    below it, a "regex:" line matches at the start of the path."""

    def __init__(self, text):
        self.literal, self.regex = [], []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("regex:"):
                self.regex.append(re.compile(line[len("regex:"):]))
            else:
                self.literal.append(line.rstrip("/"))

    def match(self, path):
        if any(path == p or path.startswith(p + "/") for p in self.literal):
            return True
        return any(r.match(path) for r in self.regex)


def patch_id(repo, diff):
    if not diff.strip():
        return None
    out = git(repo, "patch-id", "--stable", data=diff.encode()).split()
    return out[0] if out else None


def strip_pr(subject):
    return PR.sub("", subject).strip()


def filtered_commits(repo, ref):
    """The filtered commits, newest first, with their upstream commit and their numstat."""
    commits, cur = [], None
    raw = git(repo, "log", "--numstat", "--format=%x1e%H%x1f%an%x1f%aI%x1f%s%x1f%B%x1f", ref)
    for rec in raw.split("\x1e")[1:]:
        sha, author, date, subject, body, rest = rec.split("\x1f", 5)
        m = TRAILER.search(body)
        files = []
        for line in rest.strip().splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                files.append((parts[2], parts[0], parts[1]))
        cur = {"sha": sha, "upstream": m.group(1) if m else None, "author": author,
               "date": date, "subject": subject, "files": files}
        commits.append(cur)
    return commits


def taken_by_lite(upstream, main, lite, paths, filtered_repo, commits):
    """{upstream sha: reason} for every upstream commit lite has, and the boundary sha."""
    order = git(upstream, "rev-list", "--topo-order", main).split()
    index = {s: i for i, s in enumerate(order)}
    taken = {}
    base = git(upstream, "merge-base", lite, main).strip()
    for s in git(upstream, "rev-list", base).split():
        taken[s] = "ancestor of lite"

    newer = [c for c in commits if c["upstream"] in index and c["upstream"] not in taken]
    by_pid, by_subject = {}, {}
    for c in newer:
        pid = patch_id(filtered_repo, git(filtered_repo, "diff-tree", "-p", "--no-commit-id", c["sha"]))
        if pid:
            by_pid.setdefault(pid, []).append(c["upstream"])
        by_subject.setdefault(strip_pr(c["subject"]), []).append(c["upstream"])

    for s in git(upstream, "rev-list", "--no-merges", main + ".." + lite).split():
        body = git(upstream, "log", "-1", "--format=%B", s)
        named = PICKED.findall(body) + LITE_TRAILER.findall(body)
        for u in named:
            if u in index:
                taken.setdefault(u, "cherry-picked (" + s[:10] + ")")
        files = [f for f in git(upstream, "diff-tree", "-r", "--no-commit-id", "--name-only", s).splitlines()
                 if paths.match(f)]
        if files:
            pid = patch_id(upstream, git(upstream, "diff-tree", "-p", "--no-commit-id", s, "--", *files))
            for u in by_pid.get(pid, []):
                taken.setdefault(u, "same change as " + s[:10])
        subject = git(upstream, "log", "-1", "--format=%s", s).strip()
        for u in by_subject.get(strip_pr(subject), []):
            taken.setdefault(u, "same subject as " + s[:10])

    in_main = [s for s in taken if s in index]
    boundary = min(in_main, key=index.get) if in_main else None
    return taken, boundary, index


def esc(s):
    return html.escape(s, quote=True)


def subject_html(subject):
    s = esc(subject)
    m = PR.search(subject)
    if m:
        n = m.group(1)
        s = PR.sub("", s).rstrip() + ' (<a href="%s/pull/%s">#%s</a>)' % (UPSTREAM, n, n)
    return s


def entry_html(c, fork, taken, new, tags):
    u = c["upstream"]
    cls = ["c"]
    badges = []
    if u in new:
        badges.append('<span class="b new">new</span>')
    if not c.get("above") and u not in taken:
        cls.append("skipped")
        badges.append('<span class="b out">not in lite</span>')
    for t in tags.get(c["sha"], []):
        badges.append('<span class="b tag">%s</span>' % esc(t))
    files = "".join(
        '<li><code>%s</code> <span class="add">+%s</span> <span class="del">-%s</span></li>'
        % (esc(f), esc(a), esc(d)) for f, a, d in c["files"])
    why = ('<div class="why">in lite: %s</div>' % esc(taken[u])) if u in taken and taken[u] != "ancestor of lite" else ""
    return (
        '<li class="%s"><div class="head"><span class="date">%s</span> <span class="subj">%s</span> %s</div>'
        '<div class="meta">%s &middot; upstream <a href="%s/commit/%s"><code>%s</code></a> &middot; '
        'filtered <a href="https://github.com/%s/commit/%s"><code>%s</code></a></div>%s'
        '<details><summary>%d file%s</summary><ul class="files">%s</ul></details></li>'
        % (" ".join(cls), esc(c["date"][:10]), subject_html(c["subject"]), " ".join(badges),
           esc(c["author"]), UPSTREAM, u, u[:10], fork, c["sha"], c["sha"][:10], why,
           len(c["files"]), "" if len(c["files"]) == 1 else "s", files))


CSS = """
:root{--bg:#fff;--fg:#1f2328;--mut:#59636e;--line:#d1d9e0;--card:#f6f8fa;--acc:#0969da;--new:#1a7f37;--in:#8250df;--tag:#9a6700;--add:#1a7f37;--del:#cf222e;--sep:#bc4c00}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#9198a1;--line:#3d444d;--card:#151b23;--acc:#4493f8;--new:#3fb950;--in:#ab7df8;--tag:#d29922;--add:#3fb950;--del:#f85149;--sep:#f0883e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}h1{font-size:1.5rem;margin:0 0 4px}
a{color:var(--acc)}code{font:.85em ui-monospace,SFMono-Regular,Menlo,monospace}
.lead{color:var(--mut);margin:0 0 16px}.facts{display:grid;grid-template-columns:max-content 1fr;gap:2px 16px;margin:0 0 24px;color:var(--mut);font-size:.9em}
.facts dt{font-weight:600}.facts dd{margin:0;overflow-wrap:anywhere}
ol{list-style:none;margin:0;padding:0}.c{border:1px solid var(--line);background:var(--card);border-radius:6px;padding:8px 12px;margin:0 0 8px}
.c.skipped{border-left:4px solid var(--in)}.head{overflow-wrap:anywhere}.date{color:var(--mut);font-variant-numeric:tabular-nums}.subj{font-weight:600}
.meta,.why{color:var(--mut);font-size:.85em;overflow-wrap:anywhere}.why{font-style:italic}
details{font-size:.85em}summary{cursor:pointer;color:var(--mut)}.files{margin:4px 0 0;padding-left:18px}.files li{overflow-wrap:anywhere}
.add{color:var(--add)}.del{color:var(--del)}
.b{display:inline-block;font-size:.75em;font-weight:600;border:1px solid currentColor;border-radius:10px;padding:0 7px;margin-left:4px;white-space:nowrap}
.b.new{color:var(--new)}.b.out{color:var(--in)}.b.tag{color:var(--tag)}
.sep{margin:24px 0;padding:10px 12px;border-top:3px solid var(--sep);border-bottom:3px solid var(--sep);color:var(--sep);font-weight:600;overflow-wrap:anywhere}
.sep a{color:var(--sep)}.note{color:var(--mut);font-size:.9em}
"""


def build(args):
    with open(args.paths, encoding="utf-8") as f:
        paths = Paths(f.read())
    commits = filtered_commits(args.filtered, args.filtered_ref)
    taken, boundary, index = taken_by_lite(args.upstream, args.main, args.lite, paths, args.filtered, commits)

    state = {}
    if args.state_in and os.path.exists(args.state_in):
        with open(args.state_in, encoding="utf-8") as f:
            state = json.load(f)
    seen = state.get("seen", {})
    first_run = not seen
    fresh = [c["upstream"] for c in commits if c["upstream"] not in seen]
    for u in fresh:
        seen[u] = "initial" if first_run else args.run_date
    if fresh and not first_run:
        last_new = fresh
        last_new_date = args.run_date
    else:
        last_new = state.get("last_new", [])
        last_new_date = state.get("last_new_date")
    new = set(last_new)

    # release tags of upstream, shown on the newest filtered commit at or before them
    tags = {}
    for name in git(args.upstream, "tag", "--list").split():
        sha = git(args.upstream, "rev-parse", name + "^{commit}").strip()
        if sha not in index:
            continue
        for c in commits:
            if index.get(c["upstream"], -1) >= index[sha]:
                tags.setdefault(c["sha"], []).append(name)
                break

    bidx = index.get(boundary, len(index))
    above = [c for c in commits if index.get(c["upstream"], len(index)) < bidx]
    below = [c for c in commits if index.get(c["upstream"], len(index)) >= bidx]
    for c in above:
        c["above"] = True
    skipped = [c for c in below if c["upstream"] not in taken]
    older = below[:OLDER_CAP]

    binfo = None
    if boundary:
        s, d = git(args.upstream, "log", "-1", "--format=%s%x1f%aI", boundary).strip().split("\x1f")
        binfo = {"sha": boundary, "subject": s, "date": d}

    fork = args.fork
    up_head = git(args.upstream, "rev-parse", args.main).strip()
    lite_head = git(args.upstream, "rev-parse", args.lite).strip()
    gen = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sep = "── our fork's lite is here"
    if binfo:
        m = PR.search(binfo["subject"])
        pr = (' (<a href="%s/pull/%s">#%s</a>)' % (UPSTREAM, m.group(1), m.group(1))) if m else ""
        sep += ': <a href="%s/commit/%s">%s</a>%s, %s ──' % (
            UPSTREAM, binfo["sha"], esc(strip_pr(binfo["subject"])), pr, esc(binfo["date"][:10]))
    else:
        sep += " (no upstream commit of main found in lite) ──"
    page = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
        "<title>OpenCCU-Base filtered</title><style>%s</style></head><body><main>" % CSS,
        "<h1>OpenCCU-Base, filtered to openccu-lite's paths</h1>",
        "<p class=\"lead\">Upstream <a href=\"%s/commits/main\">OpenCCU/OpenCCU-Base main</a> limited to the "
        "paths openccu-lite builds from, newest first. Above the line: what upstream did after the newest commit "
        "our fork's <code>lite</code> has (none of them is in <code>lite</code>); below it: the older ones (the latest %d), those <code>lite</code> skipped marked <em>not in lite</em>. The full history is the branch "
        "<a href=\"https://github.com/%s/commits/filtered\"><code>filtered</code></a>.</p>" % (UPSTREAM, OLDER_CAP, fork),
        "<dl class=\"facts\">",
        "<dt>Generated</dt><dd>%s</dd>" % gen,
        "<dt>Upstream main</dt><dd><a href=\"%s/commit/%s\"><code>%s</code></a> (%d commits, %d filtered)</dd>"
        % (UPSTREAM, up_head, up_head[:10], len(index), len(commits)),
        "<dt>Fork lite</dt><dd><a href=\"https://github.com/%s/commit/%s\"><code>%s</code></a></dd>" % (fork, lite_head, lite_head[:10]),
        "<dt>Paths file</dt><dd><a href=\"%s\">openccu-base-paths.txt</a> at <code>%s</code></dd>"
        % (esc(args.paths_url), esc(args.paths_commit[:10])),
        "<dt>Not in lite</dt><dd>%d above the line, %d below it (skipped)</dd>" % (len(above), len(skipped)),
        "<dt>New</dt><dd>%s</dd>" % (("%d, first seen %s" % (len(new), esc(last_new_date))) if new else "none since the first run"),
        "</dl><ol>",
    ]
    page += [entry_html(c, fork, taken, new, tags) for c in above]
    if not above:
        page.append("<li class=\"note\">Nothing upstream after it.</li>")
    page.append("</ol><div class=\"sep\">%s</div><ol>" % sep)
    page += [entry_html(c, fork, taken, new, tags) for c in older]
    page.append("</ol>")
    if len(below) > len(older):
        page.append("<p class=\"note\">%d older filtered commits are on the branch "
                    "<a href=\"https://github.com/%s/commits/filtered\"><code>filtered</code></a>.</p>"
                    % (len(below) - len(older), fork))
    page.append("</main></body></html>\n")
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(page))

    with open(os.path.join(args.out, "state.json"), "w", encoding="utf-8") as f:
        json.dump({"seen": seen, "last_new": last_new, "last_new_date": last_new_date,
                   "paths_commit": args.paths_commit, "filtered_head": commits[0]["sha"] if commits else None},
                  f, indent=1, sort_keys=True)
        f.write("\n")

    md = ["### OpenCCU-Base filtered", "",
          "- upstream main `%s`: %d commits, %d filtered" % (up_head[:10], len(index), len(commits)),
          "- paths file at `%s`" % args.paths_commit[:10],
          "- lite stands at: %s" % ("[%s](%s/commit/%s)" % (binfo["subject"], UPSTREAM, binfo["sha"]) if binfo else "unknown"),
          "- above it (not in lite): %d filtered commits; below it, skipped by lite: %d" % (len(above), len(skipped)), ""]
    if first_run:
        md.append("First run: every commit recorded as seen, none marked new.")
    elif fresh:
        md.append("**New in this run: %d**" % len(fresh))
        md.append("")
        for c in commits:
            if c["upstream"] in fresh:
                md.append("- %s %s ([%s](%s/commit/%s))" % (c["date"][:10], c["subject"], c["upstream"][:10], UPSTREAM, c["upstream"]))
    else:
        md.append("Nothing new since the last run.")
    with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return {"taken": taken, "boundary": boundary, "above": [c["upstream"] for c in above],
            "skipped": [c["upstream"] for c in skipped],
            "fresh": fresh, "new": sorted(new)}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--filtered", required=True, help="repository holding the filtered history")
    p.add_argument("--filtered-ref", default="main")
    p.add_argument("--upstream", required=True, help="repository holding upstream main and the fork's lite")
    p.add_argument("--main", default="main")
    p.add_argument("--lite", default="lite")
    p.add_argument("--paths", required=True)
    p.add_argument("--paths-url", default="")
    p.add_argument("--paths-commit", default="")
    p.add_argument("--fork", default="hobbyquaker/OpenCCU-Base")
    p.add_argument("--state-in")
    p.add_argument("--run-date", default=datetime.date.today().isoformat())
    p.add_argument("--out", required=True)
    build(p.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
