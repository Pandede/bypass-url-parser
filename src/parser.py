import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger('bup')


class Bypasser:
    def __init__(self, constant: Path = Path('./src/constant.yaml')):
        with open(constant, 'r') as streamer:
            self.constant: Dict[str, List[str]] = yaml.load(streamer, Loader=yaml.FullLoader)

    def __replacenth(self, string: str, sub: str, wanted: str, n: int) -> str:
        where = [m.start() for m in re.finditer(sub, string)][n - 1]
        return string[:where] + string[where:].replace(sub, wanted, 1)

    def wrap_curl(self, content: str) -> str:
        header_user_agent = "-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36'"
        base_curl = f"curl -sS -kgi --path-as-is {header_user_agent}"
        return f"{base_curl} {content}"

    def generate_curls(self, url: str, headers: Dict[str, str]) -> List[str]:
        split_at = re.search(r"^https?://[^/]+", url, re.IGNORECASE).span()[1]

        # Dirty af but shitty escaping issues in bash -c
        full_url = url.replace("'", '%27')
        base_url = url[:split_at].replace("'", '%27')
        base_path = url[split_at:].replace("'", '%27')

        for key, value in headers.items():
            base_url += f" -H '{key}: {value}'"

        curls = set()

        # Original request
        curls.add(self.wrap_curl(f"'{full_url}'"))

        # Custom methods
        for http_method in self.constant['http_methods']:
            curls.add(
                self.wrap_curl(f"-X '{http_method}' '{full_url}'")
            )

        # Custom host injection headers
        for header_host in self.constant['header_hosts']:
            for internal_ip in self.constant['internal_ips']:
                curls.add(
                    self.wrap_curl(f"-H '{header_host}: {internal_ip}' '{full_url}'")
                )

        # Custom proto rewrite
        for header_scheme in self.constant['header_schemes']:
            for proto in self.constant['protos']:
                curls.add(
                    self.wrap_curl(f"-H '{header_scheme}: {proto}' '{full_url}'")
                )

        # Custom port rewrite
        for header_port in self.constant['header_ports']:
            for port in self.constant['ports']:
                curls.add(
                    self.wrap_curl(f"-H '{header_port}: {port}' '{full_url}'")
                )

        # Custom paths with extra-mid-slash
        for idx_slash in range(base_path.count("/")):
            for path in self.constant['paths']:
                path_post = self.__replacenth(base_path, "/", f"/{path}", idx_slash)
                curls.add(self.wrap_curl(f"'{base_url}{path_post}'"))
                curls.add(self.wrap_curl(f"'{base_url}/{path_post}'"))
                if idx_slash <= 1:
                    continue
                path_pre = self.__replacenth(base_path, "/", f"{path}/", idx_slash)
                curls.add(self.wrap_curl(f"'{base_url}{path_pre}'"))
                curls.add(self.wrap_curl(f"'{base_url}/{path_pre}'"))

        # Other bypasses
        abc_indexes = [span.start() for span in re.finditer(r"[a-zA-Z]", base_path)]
        for idx in abc_indexes:
            # Case-Inversion
            char_case = base_path[idx]
            if char_case.islower():
                char_case = char_case.upper()
            else:
                char_case = char_case.lower()
            curls.add(
                self.wrap_curl(f"'{base_url}/{base_path[:idx]}{char_case}{base_path[idx+1:]}'")
            )

            # Url-Encoding
            char_urlencoded = format(ord(base_path[idx]), "02x")
            curls.add(
                self.wrap_curl(f"'{base_url}/{base_path[:idx]}%{char_urlencoded}{base_path[idx+1:]}'")
            )

        # Sanitize and debug-print
        return sorted(list(curls))

    def run_curl(self, curl: str, timeout: float) -> Optional[str]:
        try:
            response = subprocess.check_output(
                ['sh', '-c', curl], timeout=timeout
            ).decode()
            return f'{curl}\n{response}'
        except subprocess.CalledProcessError as e:
            logger.warning(
                f'command "{e.cmd}" returned non-zero error code {e.returncode}: {e.output}'
            )
        except subprocess.TimeoutExpired as e:
            logger.warning(
                f'command "{e.cmd}" timed out: {e.output}'
            )

    def run_curls(self, curls: List[str], timeout: float, max_workers: int = 1):
        def run_timeout(curl: str) -> str:
            return self.run_curl(curl, timeout)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            yield from executor.map(run_timeout, curls)
            executor.shutdown(wait=True)
