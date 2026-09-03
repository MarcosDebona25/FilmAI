# tmdb-cache Specification

## Purpose

A Redis cache-aside layer wrapping the existing `TMDBClient`. It reduces TMDB API cost and latency while adding resilience. It checks Redis first and returns cached data on hit; on miss it calls TMDB, stores the result with a TTL, and returns it. When Redis is unavailable it degrades gracefully by calling TMDB directly.

## Requirements

### Requirement: Cache-aside lookup

The system SHALL return a cached JSON payload from Redis when a matching entry exists, without calling TMDB.

#### Scenario: Cache hit returns without TMDB call

- GIVEN a cached entry exists for a given endpoint and parameter set
- WHEN the cache lookup for that endpoint and parameter set runs
- THEN the cached JSON is returned
- AND the TMDB client is NOT invoked

### Requirement: Cache miss stores and returns

The system SHALL call TMDB when no cached entry exists, store the resulting JSON in Redis with the endpoint's TTL, and return the JSON.

#### Scenario: Cache miss calls TMDB and stores

- GIVEN no cached entry exists for a given endpoint and parameter set
- WHEN the cache lookup runs
- THEN the TMDB client is invoked
- AND the returned JSON is stored in Redis with the endpoint's TTL
- AND the JSON is returned to the caller

### Requirement: Graceful degradation on Redis failure

The system SHALL bypass the cache and call TMDB directly when Redis is unavailable; a Redis failure MUST NOT cause the request to fail.

#### Scenario: Redis connection error bypasses cache

- GIVEN Redis is unavailable (connection error or timeout)
- WHEN the cache lookup runs
- THEN the cache is bypassed
- AND the TMDB client is invoked directly
- AND the request succeeds without raising a Redis-related error

### Requirement: Per-endpoint TTL

The system SHALL apply a TTL per endpoint group: lists (trending, now_playing, discover) 6 hours; search 1 hour; details (movie_detail, tv_detail, keywords) 24 hours.

#### Scenario: TTL applied per endpoint group

- GIVEN a cache miss on an endpoint
- WHEN the result is stored
- THEN a list endpoint entry expires after 6 hours
- AND a search entry expires after 1 hour
- AND a details entry expires after 24 hours

### Requirement: Stable cache key

The system SHALL derive the cache key as `tmdb:{endpoint}:{params_hash}`, where `params_hash` is a stable hash of the sorted query parameters so that identical logical calls map to the same key.

#### Scenario: Same call produces same key

- GIVEN the same endpoint with query parameters in different orders
- WHEN the cache key is computed
- THEN both calls produce the same key
- AND hits resolve to the same cached entry

### Requirement: JSON serialization round-trip

The system SHALL serialize stored entries to JSON and deserialize on retrieval such that the TMDB response structure is preserved.

#### Scenario: Round-trip preserves structure

- GIVEN a TMDB response is stored
- WHEN the entry is retrieved from cache
- THEN the deserialized structure matches the original TMDB response
