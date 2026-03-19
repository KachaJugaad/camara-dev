# ADR-001: System Design — Two-Phase Architecture

**Status:** Accepted
**Date:** 2026-03-19
**Author:** Architect Agent

## Context

Canada has no public CAMARA developer sandbox. Rogers, Bell, and Telus have made
zero public commitment to providing one. Canadian fintech companies building SIM swap
fraud detection, number verification, or device location services have nowhere to
test their CAMARA integration before negotiating a carrier agreement.

We need a sandbox that:
- Simulates realistic Rogers/Bell/Telus CAMARA endpoints
- Runs locally with zero carrier dependencies
- Is CAMARA Fall25 spec-compliant so apps built against it work with real carriers
- Ships in 7 days (MVP sprint)

## Decision

### Two-phase architecture

**Phase 1 (MVP, Days 1–7): Python/FastAPI**
- Simulation engine, carrier profiles, latency model, API gateway, auth — all Python
- TypeScript/React for web portals (developer, operator, admin)
- Ship fast, prove the use cases, validate API contracts

**Phase 2 (post-launch): Rust simulation engine + Go API gateway**
- Only after MVP is validated and carriers show interest
- Phase 2 must pass the same conformance tests as Phase 1

### Key design choices

1. **TOML carrier configs** — Adding a new carrier requires only a new `.toml` file.
   No code changes. The simulation engine reads all profiles at startup.

2. **Seeded RNG simulation** — Latency injection uses linear interpolation between
   p50/p95/p99/p999 percentile anchors. Error injection is probabilistic per carrier
   error profiles. All randomness is seedable (`X-Seed` header) for deterministic tests.

3. **Sandbox bearer auth** — Simplified from production CIBA for developer convenience.
   Demo keys are pre-loaded. Custom keys issued instantly via `POST /sandbox/keys`.
   Migration guide at `GET /sandbox/auth-migration-guide`.

4. **OpenAPI 3.0 contracts** — The spec is the contract between layers. Phase 2
   rewrites must pass identical conformance tests.

5. **v0→v1 redirects** — Old v0 paths return 301 with `Deprecation: true` header
   for backward compatibility during CAMARA Fall25 migration.

## Consequences

**Positive:**
- Fast to ship — Python/FastAPI is the fastest path to working endpoints
- Easy to test — seeded RNG makes all tests deterministic
- Clear migration path — same OpenAPI contracts, same conformance tests
- Zero carrier dependency — fully self-contained simulation

**Negative:**
- Python is slower than Rust for high-throughput simulation (acceptable for sandbox)
- Two codebases to maintain during Phase 2 transition
- Simulation data does not reflect real carrier behavior exactly

**Mitigations:**
- Phase 2 only starts after MVP validation — we may never need it
- Conformance tests ensure Phase 2 matches Phase 1 behavior exactly
