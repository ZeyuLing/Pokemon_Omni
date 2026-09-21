# Project collaboration

- Canonical remote: https://github.com/ZeyuLing/Pokemon_Omni .
- The user authorizes regular GitHub synchronization: commit and push coherent, verified increments after meaningful work. This is part of active development, not a timed background automation.
- Check local and remote changes before pushing. Preserve existing history and user work. Do not force-push or rewrite published commits unless explicitly requested.
- Keep build outputs, ROMs, save files, dependency installs, local toolchains, caches and credentials out of Git. Commit reproducible sources, dependency locks, source manifests and relevant documentation.
- Record actual validation and content limitations honestly. A compiled ARM object is not a playable GBA ROM, and a reference form record is not official per-species verification.
- Keep shared gameplay logic in portable C; platform presentation belongs in adapters. Prefer the same core for GBA and host preview.
- Basic in-game UI must follow the archived Rocket ROM's actual running screens and verified layout data. Do not invent or relocate information panels (for example, money does not appear in its normal bag). Reuse source assets, verify text and sprite placement in the built ROM, and distinguish remaining prototype screens from faithfully aligned screens.
