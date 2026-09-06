"""Serialising writes to the two ledgers, and swapping each into place atomically.

Both ledgers are read-modify-write: load the whole list, append one record, write the whole list
back. FastAPI dispatches a sync endpoint on anyio's threadpool, so two saves from one teacher with
two tabs open genuinely run at once, and for a correction the window between the read and the
write is wide -- two full builds sit inside it, because the recomputed holistic is whatever the
build produces (teacher_ui/decisions_log.md ui_13).

A lock only around the write would not help: the lost update happens BETWEEN the read and the
write, so the second writer's list predates the first writer's record and that record is simply
gone from a file whose entire contract is that nothing is ever lost. The lock therefore has to be
held across the whole span, which is what `lock()` is for.

See decisions_log.md ui_19, which amends ui_7.
"""

import json
import os
import threading

_LOCKS = {}
_REGISTRY = threading.Lock()


def lock(path):
    """The lock guarding one ledger file, to be held across read, modify and write alike.

    Per path, so a correction and a gold reveal do not block each other, and reentrant because
    the correction path takes it once around the builds and again inside the append it performs.
    A test that points a ledger at a temp file gets its own lock for that file.
    """
    key = os.path.abspath(path)
    with _REGISTRY:
        if key not in _LOCKS:
            _LOCKS[key] = threading.RLock()
        return _LOCKS[key]


def write_json(path, data):
    """Replace `path` with `data` as JSON, atomically.

    The pending file is named for this process and this thread, so two writers can never land on
    one pending name and interleave their `json.dump` calls into a single truncated file -- which
    would leave the ledger holding invalid JSON and every later page load raising on the way in.
    Writing beside the target and calling `os.replace` also means an interrupted write loses the
    record being added rather than every record already there.
    """
    pending = "%s.%d-%d.pending" % (path, os.getpid(), threading.get_ident())
    try:
        with open(pending, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(pending, path)
    except BaseException:
        if os.path.exists(pending):
            os.remove(pending)
        raise
