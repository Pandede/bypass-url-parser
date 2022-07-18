import pytest
from typing import Tuple, List

from src.parser import Bypasser


@pytest.fixture
def parser() -> Bypasser:
    return Bypasser('./src/constant.yaml')


@pytest.mark.usefixtures('parser')
class TestGenerateCurls:
    @pytest.mark.parametrize(
        'sample',
        [
            './test/sample/domain_only.txt',
            './test/sample/domain_with_path.txt',
        ],
        indirect=True
    )
    def test(self, parser: Bypasser, sample: Tuple[str, List[str]]):
        base_url, true_urls = sample
        pred_urls = parser.generate_curls(base_url, headers=dict())

        assert len(pred_urls) == len(true_urls)
        assert set(pred_urls) == set(true_urls)
