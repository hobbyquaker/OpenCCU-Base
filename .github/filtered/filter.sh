#!/bin/bash
# filter.sh <clone> <paths-file>: rewrites a fresh clone of OpenCCU/OpenCCU-Base (its main and tags,
# nothing else) in place into the history of the branch `filtered`:
#  - keeps only the paths the paths file names (git filter-repo's --paths-from-file format: a path
#    matches itself and everything below it, "regex:" lines are Python regular expressions);
#    commits that touch none of them vanish, mixed commits keep only their changes on those paths;
#  - appends the trailer
#      Upstream-Commit: OpenCCU/OpenCCU-Base@<short> https://github.com/OpenCCU/OpenCCU-Base/commit/<full>
#    to every kept commit, naming the upstream commit it was rewritten from;
#  - keeps authors, committers, dates and the rest of every message as upstream wrote them.
# Deterministic: the same upstream history, paths file and git-filter-repo version give the same
# commit ids, and a longer upstream history gives a history that contains the shorter one.
set -euo pipefail

clone=${1:?usage: filter.sh <clone> <paths-file>}
paths=$(cd "$(dirname "${2:?usage: filter.sh <clone> <paths-file>}")" && pwd -P)/$(basename "$2")
filter_repo=${GIT_FILTER_REPO:-git-filter-repo}

# The trailer joins the message's last paragraph when that already is a trailer block
# (Signed-off-by:, Co-authored-by: ...), so git and GitHub still read those trailers; otherwise it
# starts a paragraph of its own.
callback='
import re
full = commit.original_id
line = b"Upstream-Commit: OpenCCU/OpenCCU-Base@" + full[:10] + b" https://github.com/OpenCCU/OpenCCU-Base/commit/" + full
msg = commit.message.rstrip(b"\n")
paragraphs = msg.split(b"\n\n")
last = paragraphs[-1].split(b"\n") if msg else []
trailer = re.compile(rb"^[A-Za-z0-9][A-Za-z0-9-]*: \S")
if len(paragraphs) > 1 and last and all(trailer.match(l) for l in last):
    commit.message = msg + b"\n" + line + b"\n"
elif msg:
    commit.message = msg + b"\n\n" + line + b"\n"
else:
    commit.message = line + b"\n"
'

cd "$clone"
"$filter_repo" --force --quiet \
	--paths-from-file "$paths" \
	--commit-callback "$callback"
