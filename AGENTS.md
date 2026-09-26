# Project collaboration

- Canonical remote: https://github.com/ZeyuLing/Pokemon_Omni .
- The user authorizes regular GitHub synchronization: commit and push coherent, verified increments after meaningful work. This is part of active development, not a timed background automation.
- Check local and remote changes before pushing. Preserve existing history and user work. Do not force-push or rewrite published commits unless explicitly requested.
- Keep build outputs, ROMs, save files, dependency installs, local toolchains, caches and credentials out of Git. Commit reproducible sources, dependency locks, source manifests and relevant documentation.
- Record actual validation and content limitations honestly. A compiled ARM object is not a playable GBA ROM, and a reference form record is not official per-species verification.
- Keep shared gameplay logic in portable C; platform presentation belongs in adapters. Prefer the same core for GBA and host preview.
- Basic in-game UI must follow the archived Rocket ROM's actual running screens and verified layout data. Do not invent or relocate information panels (for example, money does not appear in its normal bag). Reuse source assets, verify text and sprite placement in the built ROM, and distinguish remaining prototype screens from faithfully aligned screens.

# Story continuity maintenance

- When writing or changing story/quest content, update the relevant prose and `content/story/worldline.json` / `characters.json` together. Register every named or anonymous narrative actor and each implemented NPC instance; distinguish candidates, written history, and prototype content.
- Keep unwritten biography fields `null` (blank in generated dossiers). Do not fill gaps from unrelated anime/game continuities or invent births, deaths, betrayals, future actions, or final outcomes merely to complete a profile.
- Character appearance must identify the anime design reference, source version and age-stage adaptation. A game illustration is not an anime reference. Original or unverified identities remain explicitly unassigned; reference images are not finished game sprites or 3D models.
- Update `content/story/CHANGELOG.md`, regenerate with `python tools/build_story_bible.py`, then run `python tools/build_story_bible.py --check` and the relevant story checks. Do not hand-edit generated `docs/story/characters/*.md` or `docs/story/worldline.md`.
- Use `content/story/atlas.json` for atlas references. Panel positions are not global geography. Omni may author global positions, distances and new terrain without official global coordinates. Review them against source-region terrain, coastline segments, exits, adjacency and era constraints; record that review rather than demanding official evidence for original geography. Follow `docs/31-world-geography-contract.md`. Do not restore the withdrawn atlas with unverified local coastlines.
- Current first-journey baseline is `docs/32-first-journey-world-premise.md`: late First Pokémon World War, decades after Cinnabar, exact year undetermined. Do not restore the retired 1967 mapping or infer Ash's biological birth from his appearance. Record author-only truths separately from character knowledge; only Oak knows Ash's AI identity at the opening. Story-bible pages contain spoilers and are not a public/game export.
