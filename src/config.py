from ipaddress import IPv4Address
from pathlib import Path
import re
from typing import Dict, Optional

from pydantic import BaseModel, Field, validator

DESCRIPTION = '''
Bypass Url Parser, made with love by @TheLaluka
A tool that tests MANY url bypasses to reach a 40X protected page.
'''
VERSION = '0.1.0'


class Config(BaseModel):
    description: str = DESCRIPTION
    version: str = VERSION
    url: str
    outdir: Path
    timeout: int
    threads: int
    header: Dict[str, str] = Field(default_factory=dict)
    spoofip: Optional[IPv4Address]
    debug: bool

    @validator('url')
    def check_url_validity(cls, url: str) -> str:
        if not re.match(r'^https?://[^/]+/', url, re.IGNORECASE):
            raise ValueError(
                'Url must start with http:// or https:// and contain at least 3 slashes'
            )
        return url
