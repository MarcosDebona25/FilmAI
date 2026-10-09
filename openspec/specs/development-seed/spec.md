# development-seed Specification

## Purpose

Populate related ratings and reviews for development while natural user activity
is unavailable. The command uses existing development users and catalog rows.

## Requirements

### Requirement: Add ratings without replacing existing domain data

`python manage.py seed --solo-resenas` MUST use active, non-staff development
users (`@filmai.com`) and existing catalog productions. It MUST preserve
existing users, productions, ratings, and reviews. Each rating MUST belong to
one user and one production, have a value from 1 to 10, and be unique for that
user-production pair. A review MUST belong to a rating and remain optional.
Each seeded rating's production MUST also be in its user's `Vistas` list, as
the reviews API does since 30/09/2026 (`reviews-api`); the seed writes through
the factories, so it applies that rule itself. The full `seed` follows it too.

#### Scenario: A user already rated one production

- GIVEN a development user with an existing rating and review
- WHEN the command runs on a catalog with more than 15 productions
- THEN that rating and review remain unchanged
- AND the user has 15 ratings in total

### Requirement: Repeating the command does not grow the data

The command MUST complete each eligible user up to 15 ratings, or the number
of available productions when the catalog is smaller. Repeating it with the
same users and catalog MUST leave rating and review counts unchanged.

#### Scenario: Run twice on a large catalog

- GIVEN one development user and 120 catalog productions
- WHEN `seed --solo-resenas` runs twice
- THEN the user has 15 ratings after each run
- AND the review count after the second run equals the first

### Requirement: Provide moderation examples

Approximately 60 percent of newly seeded ratings SHOULD receive a review.
For each development user, the command MUST ensure reviews on at least 60
percent of up to 15 ratings, adding text to ratings without it while preserving
existing reviews.
Every seventh review created by a run MUST start inactive so the Admin can
exercise its moderation filter. Reviews MUST remain attached to valid ratings.

### Requirement: Known bilingual development accounts

The full `seed` MUST assign `es` to usuario001/usuario003 and `en` to
usuario002, preserving the existing documented credentials. Repeating a full
seed recreates the same language assignments. `seed --solo-resenas` MUST NOT
assign or replace any account language, including null for older accounts.
No automatic database reset or language backfill is introduced.

#### Scenario: Seed accounts in a test database

- WHEN the full command runs twice
- THEN the three known development emails keep the documented ES/EN assignments
- AND the preserved administrator's language is unchanged
- WHEN only reviews are seeded for previous accounts
- THEN their saved or null languages remain unchanged
