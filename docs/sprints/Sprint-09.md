# Sprint-09: Intelligence Runtime

Milestone: Intelligence Runtime

Status: Completed

---

## Sprint Goal

Build an intelligence layer that records operational results, analyzes performance, generates recommendations, and improves future strategy decisions.

---

## Completed

- Added `IntelligenceRuntime`.
- Added `ReplyScoreService`.
- Added mock/local `EmbeddingService`.
- Added content performance collection.
- Added reply scoring.
- Added strategy performance.
- Added account performance.
- Added platform performance.
- Added time optimization table.
- Added recommendation engine.
- Added duplicate reply similarity detection.
- Added experiment model.
- Added prompt version `performance_score`.
- Added Intelligence API.
- Added Intelligence Dashboard page.
- Added Dashboard intelligence metrics.
- Added seed data for performance, recommendations, similarity, and experiment demo.

---

## API

Added:

- GET `/intelligence/dashboard`
- GET `/intelligence/recommendations`
- GET `/intelligence/performance`
- POST `/intelligence/score`
- POST `/intelligence/feedback`
- POST `/intelligence/similarity`
- GET `/intelligence/similarity`

---

## UI

Added:

- Intelligence Runtime page
- Funnel overview
- Top Strategies
- Top Replies
- Best Accounts
- Best Time
- Platform Ranking
- Recommendations
- Duplicate Reply Detection

---

## State Flow

```text
Post / Reply / Execution / Engagement
-> Performance Collection
-> Scoring
-> Aggregation
-> Recommendation
-> Next Strategy
```

---

## Tests

Covered:

- Reply scoring
- Performance collection
- Recommendation generation
- Similarity detection

Executed:

- `PYTHONPATH=backend .venv/bin/python -m unittest backend.tests.test_intelligence_runtime`
- `PYTHONPATH=backend .venv/bin/python -m unittest discover backend/tests`
- `DATABASE_URL=sqlite:////private/tmp/atos_sprint09_migration.db PYTHONPATH=. ../.venv/bin/alembic -c alembic.ini upgrade head`
- `DATABASE_URL=sqlite:////private/tmp/atos_sprint09_migration.db PYTHONPATH=backend .venv/bin/python backend/scripts/seed_data.py`
- `PYTHONPYCACHEPREFIX=/private/tmp/atos_pycache PYTHONPATH=backend .venv/bin/python -m compileall -q backend/app backend/scripts backend/tests`
- `PATH=/Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH /Users/zhangkaikai/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/pnpm run build`

---

## Known Issues

- Embedding service is mock/local only.
- Recommendation engine is rule-based.
- No external analytics warehouse or vector database is used.

---

## Commit Hash

See final Git commit hash reported after commit.

---

## Next Sprint

Recommended next sprint:

- Production embedding provider
- Prompt optimization diffs
- Advanced strategy experiment analysis
- Operator feedback UI
- Cohort and campaign-level intelligence
