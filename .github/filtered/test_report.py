#!/usr/bin/env python3
"""Tests filter.sh and report.py on a small synthetic upstream and lite (needs git-filter-repo).

    python3 -I .github/filtered/test_report.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import report  # noqa: E402

PATHS = "# ours\nsrc/core/\nregex:^lib/(?!skip/)\n"
EXCLUDE = "# noise\nsrc/core/lang/\n"


def sh(repo, *args, env=None):
    e = dict(os.environ, GIT_AUTHOR_NAME="A", GIT_AUTHOR_EMAIL="a@example.org", GIT_COMMITTER_NAME="A",
             GIT_COMMITTER_EMAIL="a@example.org", GIT_AUTHOR_DATE="2026-01-01T00:00:00Z",
             GIT_COMMITTER_DATE="2026-01-01T00:00:00Z", **(env or {}))
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, env=e).stdout.decode().strip()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def commit(repo, msg, files):
    for path, text in files.items():
        full = os.path.join(repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "a", encoding="utf-8") as f:
            f.write(text)
        sh(repo, "add", path)
    sh(repo, "commit", "-q", "-m", msg)
    return sh(repo, "rev-parse", "HEAD")


class Boundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.tmp.name
        up = cls.up = os.path.join(t, "up")
        sh(t, "init", "-q", "-b", "main", up)
        c = cls.c = {}
        c[1] = commit(up, "core: one", {"src/core/a.c": "1\n"})
        c[2] = commit(up, "webui: noise", {"src/webui/x.js": "1\n"})
        c[3] = commit(up, "core: mixed, not taken", {"src/core/b.c": "1\n", "src/webui/x.js": "2\n"})
        c[4] = commit(up, "core: picked with a line", {"src/core/a.c": "2\n"})
        c[5] = commit(up, "lib: picked and adapted", {"lib/c.c": "1\n"})
        c[10] = commit(up, "core: translations only", {"src/core/lang/de.js": "1\n"})
        c[11] = commit(up, "core: mixed with translations", {"src/core/g.c": "1\n", "src/core/lang/de.js": "2\n"})
        c[6] = commit(up, "lib: skipped path only", {"lib/skip/d.c": "1\n"})
        c[7] = commit(up, "core: our PR, changed in review (#7)", {"src/core/e.c": "upstream\n"})
        c[8] = commit(up, "core: after lite (#8)", {"src/core/f.c": "1\n"})
        c[9] = commit(up, "webui: only noise", {"src/webui/x.js": "3\n"})
        sh(up, "tag", "v1", c[4])

        # lite: branched at c2, then a cherry-pick with -x of c4, an adapted pick of c5 (plus a
        # file outside our paths), and our own commit that upstream merged as c7 after a review
        sh(up, "checkout", "-q", "-b", "lite", c[2])
        sh(up, "cherry-pick", "-x", c[4])
        commit(up, "lib: picked and adapted, with a lite-only file", {"lib/c.c": "1\n", "src/webui/lite.js": "1\n"})
        commit(up, "core: our PR, changed in review", {"src/core/e.c": "ours\n"})
        # c11 taken without -x and with a translation of our own: the same change once the
        # excluded paths are left out on both sides
        commit(up, "core: g, with our translation", {"src/core/g.c": "1\n", "src/core/lang/de.js": "ours\n"})
        sh(up, "checkout", "-q", "main")

        cls.paths = os.path.join(t, "paths.txt")
        with open(cls.paths, "w", encoding="utf-8") as f:
            f.write(PATHS)
        cls.exclude = os.path.join(t, "exclude.txt")
        with open(cls.exclude, "w", encoding="utf-8") as f:
            f.write(EXCLUDE)
        cls.fl = os.path.join(t, "fl")
        sh(t, "clone", "-q", "--no-local", "--single-branch", "--branch", "main", up, cls.fl)
        subprocess.run(["bash", os.path.join(HERE, "filter.sh"), cls.fl, cls.paths, cls.exclude],
                       check=True, capture_output=True)
        cls.out = os.path.join(t, "out")
        os.mkdir(cls.out)
        cls.res = report.build(cls.args(None, "2026-02-01"))

    @classmethod
    def args(cls, state, date):
        class A:
            pass
        a = A()
        a.filtered, a.filtered_ref, a.upstream, a.main, a.lite = cls.fl, "main", cls.up, "main", "lite"
        a.paths, a.paths_url, a.paths_commit, a.fork = cls.paths, "u", "p" * 40, "me/fork"
        a.state_in, a.run_date, a.out = state, date, cls.out
        a.exclude = getattr(cls, "exclude", None)
        return a

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_filtered_history(self):
        subjects = sh(self.fl, "log", "--format=%s").splitlines()
        self.assertEqual(subjects, ["core: after lite (#8)", "core: our PR, changed in review (#7)",
                                    "core: mixed with translations", "lib: picked and adapted", "core: picked with a line",
                                    "core: mixed, not taken", "core: one"])
        body = sh(self.fl, "log", "-1", "--format=%B", "main~5")
        self.assertIn("Upstream-Commit: OpenCCU/OpenCCU-Base@%s https://github.com/OpenCCU/OpenCCU-Base/commit/%s"
                      % (self.c[3][:10], self.c[3]), body)
        self.assertEqual(sh(self.fl, "show", "--format=", "--name-only", "main~5"), "src/core/b.c")
        # the excluded paths are gone, and with them the commit that touched nothing else
        self.assertEqual(sh(self.fl, "show", "--format=", "--name-only", "main~2"), "src/core/g.c")
        self.assertEqual(sh(self.fl, "log", "--format=%s", "--", "src/core/lang"), "")

    def test_taken(self):
        t, c = self.res["taken"], self.c
        self.assertEqual(t[c[1]], "ancestor of lite")
        self.assertEqual(t[c[2]], "ancestor of lite")
        self.assertTrue(t[c[4]].startswith("cherry-picked"))
        self.assertTrue(t[c[5]].startswith("same change as"))
        self.assertTrue(t[c[7]].startswith("same subject as"))
        self.assertTrue(t[c[11]].startswith("same change as"))
        for n in (3, 6, 8, 9, 10):
            self.assertNotIn(c[n], t)
        self.assertEqual(self.res["skipped"], [c[3]])

    def test_boundary_and_line(self):
        c = self.c
        self.assertEqual(self.res["boundary"], c[7])
        self.assertEqual(self.res["above"], [c[8]])
        page = read(os.path.join(self.out, "index.html"))
        self.assertLess(page.index("core: after lite"), page.index("our fork's lite is here"))
        self.assertLess(page.index("our fork's lite is here"), page.index("core: mixed, not taken"))
        self.assertIn('<span class="b tag">v1</span>', page)
        with open(os.path.join(self.out, "report.json"), encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["boundary"]["sha"], c[7])
        self.assertEqual([x["upstream"] for x in rep["above"]], [c[8]])
        self.assertEqual(rep["above"][0]["subject"], "core: after lite (#8)")
        self.assertEqual(rep["above"][0]["pr"], 8)
        self.assertEqual(rep["above"][0]["url"], "https://github.com/OpenCCU/OpenCCU-Base/commit/" + c[8])
        self.assertEqual(rep["skipped_below"], 1)

    def test_new_marks(self):
        self.assertEqual(self.res["new"], [])
        state = os.path.join(self.out, "state.json")
        with open(state, encoding="utf-8") as f:
            st = json.load(f)
        # pretend c8 was not there yet: the next run marks it new and keeps it marked
        del st["seen"][self.c[8]]
        with open(state, "w", encoding="utf-8") as f:
            json.dump(st, f)
        res = report.build(self.args(state, "2026-02-02"))
        self.assertEqual(res["new"], [self.c[8]])
        res = report.build(self.args(state, "2026-02-03"))
        self.assertEqual(res["fresh"], [])
        self.assertEqual(res["new"], [self.c[8]])


class OutOfOrder(unittest.TestCase):
    """A cherry-pick out of order moves the line up; the commit it jumped over shows below it as not in lite."""

    def test_out_of_order(self):
        with tempfile.TemporaryDirectory() as t:
            up = os.path.join(t, "up")
            sh(t, "init", "-q", "-b", "main", up)
            a = commit(up, "core: a", {"src/core/a.c": "1\n"})
            b = commit(up, "core: b", {"src/core/b.c": "1\n"})
            c = commit(up, "core: c", {"src/core/c.c": "1\n"})
            d = commit(up, "core: d", {"src/core/d.c": "1\n"})
            sh(up, "checkout", "-q", "-b", "lite", a)
            sh(up, "cherry-pick", "-x", c)
            sh(up, "checkout", "-q", "main")
            paths = os.path.join(t, "paths.txt")
            with open(paths, "w", encoding="utf-8") as f:
                f.write(PATHS)
            fl = os.path.join(t, "fl")
            sh(t, "clone", "-q", "--no-local", "--single-branch", "--branch", "main", up, fl)
            subprocess.run(["bash", os.path.join(HERE, "filter.sh"), fl, paths], check=True, capture_output=True)
            out = os.path.join(t, "out")
            os.mkdir(out)
            res = report.build(Boundary.args.__func__(type("X", (), {"fl": fl, "up": up, "paths": paths, "out": out}), None, "d"))
            self.assertEqual(res["boundary"], c)
            self.assertEqual(res["above"], [d])
            self.assertEqual(res["skipped"], [b])
            page = read(os.path.join(out, "index.html"))
            # b is below the line although lite does not have it, and marked so
            sep = page.index("our fork's lite is here")
            self.assertLess(sep, page.index("core: b"))
            self.assertLess(page.index("core: b"), page.index("not in lite</span>", sep))


if __name__ == "__main__":
    unittest.main()
