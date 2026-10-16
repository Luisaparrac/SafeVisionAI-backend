import pytest

from safevision.adapters.outbound.persistence.readiness import DatabaseReadinessProbe

pytestmark = pytest.mark.integration


def test_reachable_database_is_ready(pg_engine):
    assert DatabaseReadinessProbe(pg_engine).is_ready() is True
