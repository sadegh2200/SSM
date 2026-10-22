# Two tools the reel depends on

The reel skill writes Arabic copy and cites ḥadīth. Both are places where a language model fails in
the same two ways: it produces text that *looks* right and a sanad that *sounds* right. These two
skills are the check, and they are installed next to `maalsadiqeen-reel` so the agent can call them.

| skill | what it answers | how to call it |
|---|---|---|
| `arabic-editor/` | «هل هذه الجملة فصحى، موقوفة، ومشكولة كما ينبغي؟» | `python3 scripts/ar_copycheck.py FILE` / `--spec spec.json` |
| `hadith-sanad/` | «من روى هذا؟ وبأيّ لفظ حُكم عليه؟ وهل يجوز أن نختمه؟» | `python3 scripts/sanad_check.py FILE` / `--spec spec.json` |

Both are **offline and deterministic**: no network, no model, no opinion about meaning. They check the
mechanics that a reader notices — hamza and tāʾ marbūṭa, dialect, honourifics, tashkeel floors,
Arabic-Indic digits, grade vocabulary, `graded_by`, the seal rule — and print `✗`/`⚠` with a line
number. `--spec` reads a reel spec and checks every on-screen field, which is how `reel.py build`
expects them to be used.

## Install

`install-skill.sh` in the repository root installs all three skills (the reel and these two) into
`.claude/skills/`, `~/.claude/skills/` and `~/.agents/skills/`, then compares every copy byte for
byte with its master:

```bash
bash install-skill.sh          # install / re-sync
bash install-skill.sh --check  # exit 0 only when every copy matches a master
```

Edit the masters only (`maalsadiqeen-reel-maker/skills/<name>/`); the installed copies are outputs.

## Where the line is

They check **mechanics, not judgement**. A text can pass `ar_copycheck.py` and still be clumsy; a
sanad can pass `sanad_check.py` and still be the wrong ḥadīth for the idea. The skill's own rules
(`references/hadith.md`, `references/arabic-copy.md`) decide what to say; these tools decide whether
what was said is written correctly. When the two disagree, the reference wins and the tool is fixed.

Companion third-party skills and the precedence rules between all of them: `vendor/skills/README.md`.
