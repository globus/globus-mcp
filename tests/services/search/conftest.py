from collections.abc import Iterator

import pytest
from globus_sdk import SearchClient


@pytest.fixture
def search_client() -> Iterator[SearchClient]:
    client = SearchClient()
    with client.retry_config.tune(max_retries=0):
        yield client
