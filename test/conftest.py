import pytest


@pytest.fixture
def sample(request):
    with open(request.param, 'r') as streamer:
        base, *urls = streamer.read().splitlines()
        return base, urls
