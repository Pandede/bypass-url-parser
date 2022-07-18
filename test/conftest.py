import pytest
from src.parser import Bypasser


@pytest.fixture
def parser() -> Bypasser:
    return Bypasser('./src/constant.yaml')
