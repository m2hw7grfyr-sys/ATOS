# ATOS Intelligence Runtime

Version: Sprint 09

Status: Implemented Scaffold

---

## Purpose

Intelligence Runtime helps ATOS learn from historical operations.

It analyzes:

- Content performance
- Reply quality
- Platform performance
- Account performance
- Strategy performance
- Time windows
- Prompt performance

The output is a recommendation layer for future operations.

---

## Runtime Flow

```text
Operational Data
-> Performance Collection
-> Reply Scoring
-> Aggregation
-> Recommendation Engine
-> Dashboard / Feedback Loop
```

---

## Scoring

Reply scoring dimensions:

- Relevance
- Quality
- Engagement
- Conversion
- Risk

The MVP scoring model is deterministic and local.

No external AI API is required.

---

## Feedback Loop

AI feedback accepts:

- Successful replies
- Failed replies
- Prompt version
- Operator notes

The current implementation stores feedback as recommendations for prompt optimization.

Future versions can use this data to generate prompt diffs automatically.

---

## Recommendation Engine

Recommendations include:

- Best platform
- Best time window
- Account frequency reduction
- Prompt feedback

Example:

```text
Reddit performs best on Friday at 21:00.
```

---

## Embedding Foundation

Sprint 09 includes a mock embedding service.

It supports:

- Local deterministic vector generation
- Cosine-style similarity score
- Duplicate reply detection

It does not require a vector database.

---

## Tables

Added:

- content_performance
- reply_scores
- strategy_performance
- account_performance
- platform_performance
- time_performance
- intelligence_recommendations
- reply_similarities
- experiments

Prompt versions now include:

- performance_score

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

## Current Limits

- Scoring is local and heuristic.
- Embedding is mock/local only.
- Recommendation generation is rule-based.
- No large-scale vector store is implemented in this sprint.
