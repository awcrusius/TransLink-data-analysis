# Tests for the GTFS-realtime ETL pipeline

## Unit tests (mocked — no network, no real database file)

From the repo root:

```bash
pip install -r requirements-dev.txt
pytest gtfs_realtime_container/tests -m "not integration"
```

These tests build small fake `FeedMessage` protobuf objects, mock HTTP with
the `responses` library, and use temporary / in-memory DuckDB connections, so
they never touch `output_database/transit.db` and never call TransLink.

## Live integration tests (opt-in)

`test_integration_live.py` hits the real TransLink GTFS-realtime endpoints
(`gtfsrealtime`, `gtfsposition`, `gtfsalerts`). It is marked
`@pytest.mark.integration` and is skipped automatically unless a real API key
is provided:

```bash
export TRANSLINK_API_KEY=<your key>
pytest gtfs_realtime_container/tests -m integration
```

Each test consumes one API call against the key's daily quota. CI (see the
root `Jenkinsfile`) runs only the mocked suite by default; the live suite is
behind the optional `RUN_LIVE_INTEGRATION` build parameter and a Jenkins
credential.
