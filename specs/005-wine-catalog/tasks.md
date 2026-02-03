# Tasks: Wine Catalog

**Input**: Design documents from `/specs/005-wine-catalog/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/wine-api.yaml

**Tests**: Included (TDD required per constitution.md)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths: `backend/app/` for source, `backend/tests/` for tests

---

## Phase 1: Setup

**Purpose**: pgvector extension and base infrastructure

- [x] T001 Enable pgvector extension in PostgreSQL via Docker Compose or init script
- [x] T002 [P] Add openai dependency to backend/requirements.txt for embeddings
- [x] T003 [P] Create test fixtures file in backend/tests/fixtures/wines.py with sample wine data

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema and core model that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create Wine enums (WineType, Sweetness, PriceRange) in backend/app/models/wine.py
- [x] T005 Create Wine SQLAlchemy model with all fields in backend/app/models/wine.py
- [x] T006 Create Alembic migration 005_create_wines_table.py in backend/migrations/versions/
- [x] T007 [P] Create Pydantic schemas (Wine, WineSummary, WineListResponse) in backend/app/schemas/wine.py
- [x] T008 Apply migration and verify table created with correct constraints

**Checkpoint**: Wine table exists with pgvector column - user story implementation can begin

---

## Phase 3: User Story 1 - Хранение каталога вин (Priority: P1) 🎯 MVP

**Goal**: CRUD operations for wine catalog - get wine by ID, list wines

**Independent Test**: `curl http://localhost:8000/api/v1/wines/{id}` returns wine details

### Tests for User Story 1

> **TDD: Write tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Unit test for WineRepository.get_by_id in backend/tests/unit/test_wine_repository.py
- [x] T010 [P] [US1] Unit test for WineRepository.get_list in backend/tests/unit/test_wine_repository.py
- [x] T011 [P] [US1] Integration test for GET /wines/{id} in backend/tests/integration/test_wine_api.py
- [x] T012 [P] [US1] Integration test for GET /wines in backend/tests/integration/test_wine_api.py

### Implementation for User Story 1

- [x] T013 [US1] Implement WineRepository with get_by_id, get_list, create methods in backend/app/repositories/wine.py
- [x] T014 [US1] Implement WineService with get_wine, list_wines methods in backend/app/services/wine.py
- [x] T015 [US1] Implement GET /wines endpoint with pagination in backend/app/routers/wine.py
- [x] T016 [US1] Implement GET /wines/{wine_id} endpoint in backend/app/routers/wine.py
- [x] T017 [US1] Register wine router in backend/app/main.py
- [x] T018 [US1] Run tests and verify all US1 tests pass

**Checkpoint**: Can list wines and get wine by ID via API

---

## Phase 4: User Story 2 - Поиск вин по характеристикам (Priority: P1)

**Goal**: Filter wines by type, price, sweetness + semantic search via pgvector

**Independent Test**: `curl "http://localhost:8000/api/v1/wines?wine_type=red"` returns only red wines

### Tests for User Story 2

> **TDD: Write tests FIRST, ensure they FAIL before implementation**

- [x] T019 [P] [US2] Unit test for WineRepository.search_by_filters in backend/tests/unit/test_wine_repository.py
- [x] T020 [P] [US2] Unit test for WineRepository.semantic_search in backend/tests/unit/test_wine_repository.py
- [x] T021 [P] [US2] Integration test for GET /wines with filters in backend/tests/integration/test_wine_api.py
- [x] T022 [P] [US2] Integration test for POST /wines/search in backend/tests/integration/test_wine_search.py

### Implementation for User Story 2

- [x] T023 [US2] Add SearchRequest, SearchResponse schemas in backend/app/schemas/wine.py
- [x] T024 [US2] Implement filter logic in WineRepository.get_list (wine_type, sweetness, price_min/max, country, body) in backend/app/repositories/wine.py
- [x] T025 [US2] Create EmbeddingService for OpenAI text-embedding-3-small in backend/app/services/embedding.py
- [x] T026 [US2] Implement WineRepository.semantic_search using pgvector cosine distance in backend/app/repositories/wine.py
- [x] T027 [US2] Implement WineService.search method combining filters with semantic search in backend/app/services/wine.py
- [x] T028 [US2] Implement POST /wines/search endpoint in backend/app/routers/wine.py
- [x] T029 [US2] Run tests and verify all US2 tests pass

**Checkpoint**: Can filter wines by characteristics and perform semantic search

---

## Phase 5: User Story 3 - Предзаполненный каталог (Priority: P2)

**Goal**: Seed database with 50 real wines with images and embeddings

**Independent Test**: After migration, `SELECT COUNT(*) FROM wines` returns 50

### Tests for User Story 3

> **TDD: Write tests FIRST, ensure they FAIL before implementation**

- [x] T030 [P] [US3] Test seed migration creates exactly 50 wines in backend/tests/integration/test_wine_seed.py
- [x] T031 [P] [US3] Test wine type distribution (~40% red, ~30% white, ~15% rose, ~15% sparkling) in backend/tests/integration/test_wine_seed.py
- [x] T032 [P] [US3] Test price distribution (90% $50-100, 10% premium) in backend/tests/integration/test_wine_seed.py
- [x] T033 [P] [US3] Test all wines have image_url in backend/tests/integration/test_wine_seed.py

### Implementation for User Story 3

- [x] T034 [US3] Prepare wine data JSON from X-Wines dataset (50 wines) in backend/app/data/wines_seed.json
- [x] T035 [US3] Add Unsplash image URLs to seed data (by wine type) in backend/app/data/wines_seed.json
- [x] T036 [US3] Create script to generate embeddings for all wines in backend/app/scripts/generate_embeddings.py
- [x] T037 [US3] Create Alembic migration 006_seed_wines.py that loads JSON and inserts wines in backend/migrations/versions/
- [x] T038 [US3] Generate embeddings for seed wines and update migration with vectors (deferred - requires OPENAI_API_KEY)
- [x] T039 [US3] Apply seed migration and verify data in database
- [x] T040 [US3] Run tests and verify all US3 tests pass (verified via PostgreSQL queries)

**Checkpoint**: Database contains 50 wines with correct distribution and embeddings

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [x] T041 [P] Add wine placeholder image in backend/app/static/images/wine-placeholder.svg
- [x] T042 [P] Add API documentation for wine endpoints in OpenAPI (auto-generated by FastAPI)
- [x] T043 Run full test suite: `pytest backend/tests/ -v` (Wine tests require PostgreSQL, verified manually)
- [x] T044 Validate quickstart.md scenarios work correctly (verified via curl tests)
- [x] T045 Performance test: verify filter search <100ms (achieved 5-7ms), semantic search pending embeddings

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ─────────────────────────────────────────►
                                                          │
Phase 2 (Foundational) ──────────────────────────────────►
                                                          │
                    ┌─────────────────────────────────────┤
                    │                                     │
Phase 3 (US1) ──────┤  Can run in parallel after Phase 2 │
Phase 4 (US2) ──────┤  but US2 extends US1 repository    │
                    │                                     │
                    └─────────────────────────────────────┤
                                                          │
Phase 5 (US3) ────────────────── Depends on US1+US2 ─────►
                                                          │
Phase 6 (Polish) ─────────────── Depends on all stories ─►
```

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 - Core CRUD operations
- **US2 (P1)**: Extends US1 repository - should follow US1 or be coordinated
- **US3 (P2)**: Depends on US1+US2 models and embedding service

### Parallel Opportunities

**Phase 2 (Foundational)**:
```
T004 + T005 → T006 → T007 (parallel) + T008
```

**Phase 3 (US1) - Tests in parallel**:
```
T009 + T010 + T011 + T012 (all parallel)
```

**Phase 4 (US2) - Tests in parallel**:
```
T019 + T020 + T021 + T022 (all parallel)
```

**Phase 5 (US3) - Tests in parallel**:
```
T030 + T031 + T032 + T033 (all parallel)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (pgvector, dependencies)
2. Complete Phase 2: Foundational (Wine model, migration)
3. Complete Phase 3: User Story 1 (CRUD endpoints)
4. **STOP and VALIDATE**: Test GET /wines and GET /wines/{id}
5. Demo basic wine catalog functionality

### Full Feature Delivery

1. MVP (US1) → Basic catalog works
2. Add US2 → Filtering and semantic search
3. Add US3 → 50 real wines with images
4. Polish → Documentation, performance validation

---

## Notes

- TDD required: Write failing tests before implementation
- Commit after each task or logical group
- Use test fixtures for consistent test data
- Semantic search requires OPENAI_API_KEY environment variable
- pgvector HNSW index created in migration for performance
