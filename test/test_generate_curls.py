from typing import List, Tuple

import pytest
from src.parser import Bypasser


@pytest.fixture
def sample(request):
    with open(request.param, 'r') as streamer:
        base, *urls = streamer.read().splitlines()
        return base, urls


@pytest.mark.usefixtures('parser', 'sample')
class TestGenerateCurls:
    @pytest.mark.parametrize(
        'sample',
        [
            './test/sample/domain_only.txt',
            './test/sample/domain_with_path.txt',
            './test/sample/domain_with_paths.txt'
        ],
        indirect=True
    )
    def test(self, parser: Bypasser, sample: Tuple[str, List[str]]):
        base_url, true_urls = sample
        pred_urls = parser.generate_curls(base_url, headers=dict())

        assert len(pred_urls) == len(true_urls)
        assert set(pred_urls) == set(true_urls)
