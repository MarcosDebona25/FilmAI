---
name: conventional-commits
description: "Trigger: commit, commit message, conventional commit, type of commit, feat, fix, chore. Write conventional commits using the project's type list."
license: Apache-2.0
metadata:
  author: "marcosdebona"
  version: "1.0"
---

# Conventional Commits

## Activation Contract

Use this skill when writing, revising, or suggesting a commit message, or when the user asks which commit type to use for a change.

## Hard Rules

- Every commit message follows the format `type(scope): description`.
- `type` MUST be one of the 12 types in the table below — never invent a new type.
- `scope` is optional; when used, it names the affected area (e.g. `cart`, `auth`, `api`).
- `description` is lowercase, imperative mood, no trailing period.
- Use `revert:` without a scope: `revert: "original subject"`.
- Never add AI attribution (e.g. `Co-Authored-By`) to commits.

## Decision Gates

| Type | Use when |
|------|----------|
| feat | Adding a new user-facing feature |
| fix | Fixing a bug |
| chore | Changes not touching `src` or `test` (deps, tooling) |
| docs | Documentation-only changes |
| style | Formatting/whitespace; no meaning change |
| refactor | Code change that neither fixes a bug nor adds a feature |
| perf | Improving performance |
| test | Adding or updating tests |
| build | Build system or external dependency changes |
| ci | CI configuration and scripts |
| revert | Reverting a previous commit |

## Execution Steps

1. Classify the change against the Decision Gates table; pick exactly one type.
2. Determine the scope (optional): the module or area the change touches.
3. Write the subject: `type(scope): imperative lowercase description`.
4. Verify the type exists in the table and the subject reads as an imperative command.

## Output Contract

Return a single commit subject line in the format `type(scope): description`. If more than one type could apply, choose the most specific and state the alternative.

## References

- `references/examples.md` — full table with example messages for every type.
