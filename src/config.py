from ipaddress import IPv4Address
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field, HttpUrl, validator

DESCRIPTION = '''
Bypass Url Parser, made with love by @TheLaluka
A tool that tests MANY url bypasses to reach a 40X protected page.
'''
VERSION = '0.1.0'


class Config(BaseModel):
    description: str = DESCRIPTION
    version: str = VERSION
    url: HttpUrl
    outdir: Path
    timeout: int
    threads: int
    header: Dict[str, str] = Field(default_factory=dict)
    spoofip: Optional[IPv4Address]
    debug: bool

    @validator('url')
    def check_ending_slash(cls, url: HttpUrl) -> HttpUrl:
        if not url.endswith('/'):
            return f'{url}/'
        return url
