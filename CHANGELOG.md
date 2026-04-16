# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-04-15

2026-redesign release: proactive relevance-gated context injection with
sanitization, decay, opt-in LLM curation, and outcome-based promote/demote.

### Added
- `hooks/pattern-injector.py` — UserPromptSubmit hook (Phase 5.2).
- `lib/sanitizer.py` — error-text sanitization (Phase 5.1).
- `lib/tokenizer.py`, `lib/ranker.py`, `lib/renderer.py` — stdlib TF-IDF.
- `lib/decay.py` — auto-demote patterns stale >30 days (Phase 5.3).
- `lib/curation.py` — opt-in Haiku-based merge/prune (Phase 5.4).
- `lib/vote.py` — thumbs-up/down with auto-disable (Phase 5.5,
  subsumes original Phase 4).
- `lib/config.py` — centralized config with safe defaults.
- `tests/` — unittest suite for all new modules, stdlib only.
- `Makefile` — `make test` / `make test-verbose`.
- CLI: `error-curator.py --decay`, `--vote`, `--llm-curate`.
- Slash: `/error-learning vote <id> up|down`.

### Changed
- `hooks/command-validator.py` — stamps `last_triggered_at` on blocks,
  appends a vote hint to block messages.
- `hooks/error-logger.py` — sanitizes error text before storage.
- `config.json` — new keys with backwards-compatible defaults.
- `plugin.json` — registers UserPromptSubmit hook; version 1.1.0.

### Known limitations
- TF-IDF tokenizer strips non-alphanumeric characters, so prompts with heavy
  symbols (`&&`, `--xyz`) score low against relevant patterns. Reactive
  blocking still catches these; proactive injection may miss them.

## [1.0.0] - 2026-04-15

First release as an installable Claude Code plugin.

### Added
- `.claude-plugin/plugin.json` manifest with hooks registered in-plugin (no more manual `settings.json` editing)
- `.claude-plugin/marketplace.json` so the repo is self-installable via `/plugin marketplace add`
- `CHANGELOG.md`

### Changed
- Plugin manifest moved from repo root to `.claude-plugin/plugin.json` per Claude Code plugin spec
- `author` upgraded from string to object form with homepage URL
- Dropped the invalid `commands` manifest field — slash commands are auto-discovered from `commands/`
- README installation instructions lead with marketplace install; manual install preserved as a fallback

### Included features (rolled up from pre-publication development)
- PostToolUseFailure hook captures errors with an `awaiting_fix` flag
- PostToolUse (Bash) hook links successful commands to prior errors
- PreToolUse (Bash) hook blocks known-bad commands and surfaces the learned fix
- SessionEnd hook pairs errors with fixes and curates patterns
- Pattern packs: `common`, `windows`, `linux`, `learned`, `custom`
- Smart error-message detection (blocks specific bad flags, not whole commands)
- Environmental error skipping (path-not-found / permission-denied are not learned)
- Allowlist override (prefix, exact, contains, regex match types)
- `/error-learning` slash command for pack management and pattern review
