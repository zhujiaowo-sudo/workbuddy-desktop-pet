# Project instructions

- This is a Windows x64 desktop pet for WorkBuddy only. Do not add Codex integration.
- Read the design and implementation plan under `docs/` before changing application behavior.
- Keep application code, hook integration, and the pure state reducer separate.
- Do not describe planned features or synthetic-event demonstrations as live-tested integration.
- Use synthetic fixtures for automated tests. Do not commit real conversations, logs, settings, credentials, databases, or personal paths.
- Preserve existing WorkBuddy plugin configuration when adding or removing this project's hook integration.
- Do not alter permission decisions in WorkBuddy. The first release only reminds the user and opens WorkBuddy.
- Do not import third-party character assets or source files without their applicable attribution and license.
- Keep public documentation in clear Chinese, with English identifiers for code.
- Keep unrelated local applications and existing desktop pets unchanged.
- For every feature change, check interactions with existing features and record the result. Present concrete conflicts or unreasonable behavior, their impact and a recommendation to the user for a decision before implementing a tradeoff. Continue independent work while awaiting that decision; do not invent hypothetical approval gates.
- Review animation changes as complete loops and action transitions, including native rendered frames and shared anatomy. Static keyframes or metadata-only checks are insufficient. Do not present unvalidated draft art as a completed fix.
