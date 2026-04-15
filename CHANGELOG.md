# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
