import hashlib
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List

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

    def run_curl(self, curl: str, timeout: float) -> Dict[str, str]:
        logger.info(f'run_curl: {curl}')
        try:
            response = subprocess.check_output(
                ['sh', '-c', curl], timeout=timeout
            ).decode()
            return {curl: f'{curl}\n{response}'}
        except subprocess.CalledProcessError as e:
            logger.warning(
                f'command "{e.cmd}" returned non-zero error code {e.returncode}: {e.output}'
            )
        except subprocess.TimeoutExpired as e:
            logger.warning(
                f'command "{e.cmd}" timed out: {e.output}'
            )
        return dict()

    def run_curls(self, curls: List[str], timeout: float, max_workers: int = 1) -> Dict[str, str]:
        def run_timeout(curl: str) -> str:
            return self.run_curl(curl, timeout)

        responses = dict()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for response in executor.map(run_timeout, curls):
                responses.update(response)
            executor.shutdown(wait=True)
        return responses

    def save(self, path: Path, responses: Dict[str, str]):
        log = dict()
        padding = len(str(max([_.count(" ") for _ in responses.values()], default=0)))
        for cmd, response in responses.items():
            cmd_hash = hashlib.md5(cmd.encode()).hexdigest()
            filename = f'bypass-{cmd_hash}.html'
            with open(path / filename, 'w') as streamer:
                streamer.write(response)

            request = response[response.find('\n') + 1:]
            n_words = request.count(' ')
            n_lines = request.count('\n')
            unique_key = f'{n_words:{padding}}:{n_lines:{padding}}'
            log[unique_key] = filename

        log = dict(sorted(log.items()))

        log_output = '\n'.join(
            f'{stats}: {filename}' for stats, filename in log.items()
        )
        logger.info(f'Saving html pages and short output in: {str(path)}')
        logger.info(f'Triaged results & distinct pages:\n{log_output}')
        files_output = ','.join(log.values())
        inspect_cmd = f'echo {str(path)}/{{{files_output}}} | xargs bat'
        logger.info(f'Also, inspect them manually with batcat:\n{inspect_cmd}')

        with open(f'{str(path)}/triaged-bypass.log', 'w') as streamer:
            streamer.write(f'{log}\n{inspect_cmd}')
