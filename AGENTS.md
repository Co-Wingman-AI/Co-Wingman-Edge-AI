# Shared repository handoff rules

At the start of every device, Codex, or assistant session:

1. Read `WORK_LOG.md` first for the latest handoff, verified checks, and next action.
2. Run `git status --short`, inspect the current branch and `git remote -v`, then read
   the README and only the detailed docs related to your task.
3. Preserve all existing edits and untracked files. Never reset, clean, or force-push
   to make a checkout look tidy. Fetch and reconcile before editing if main advanced.

At the end of each completed unit of work:

1. Run the relevant tests/checks and record the exact results and environment.
2. Append a short entry to `WORK_LOG.md` before committing. Include the date, a
   non-identifying device/session label, change summary, validation, remaining work,
   and source commit(s) when continuing someone else's work. Git history supplies
   commit hashes for the entry itself.
3. Keep the log limited to project metadata. Never record API keys, private profile
   facts, prompts, cues, transcripts, recordings, home paths, serial numbers, or
   user/participant information.
4. Commit and push the tested change to the organization repository when authorized.
   If a branch rule blocks a direct push, use the repository's approved review path.
   Do not force-push or overwrite another device's work.

The work log is a collaboration handoff, not a runtime, user, conversation, or
microphone log. Co-Wingman's privacy rules remain in force.
