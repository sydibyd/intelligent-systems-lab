import base64
import json
from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import (
    Request,
    build_opener,
    HTTPRedirectHandler,
    ProxyHandler,
)


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


@dataclass(frozen=True)
class JenkinsState:
    reachable: bool
    building: bool | None = None
    result: str | None = None
    reason: str | None = None
    metadata: dict | None = None


class JenkinsClient:

    def __init__(
        self,
        base_url: str,
        username: str = "",
        api_token: str = "",
        timeout: float = 5.0,
        allow_loopback_http: bool = False,
    ):
        parsed = urlsplit(base_url)

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid Jenkins base URL")

        if bool(username) != bool(api_token):
            raise ValueError("Incomplete credentials")

        local_exception = (
            allow_loopback_http
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "::1"}
        )

        if api_token and parsed.scheme != "https" and not local_exception:
            raise ValueError("Credentials require HTTPS")

        if not 0 < timeout <= 30:
            raise ValueError("Invalid timeout")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Accept": "application/json"}
        self.opener = build_opener(ProxyHandler({}), RejectRedirects())

        if username and api_token:
            credentials = f"{username}:{api_token}"
            encoded = base64.b64encode(
                credentials.encode("utf-8")
            ).decode("ascii")

            self.headers["Authorization"] = (
                f"Basic {encoded}"
            )

    def get_build(
        self,
        pipeline_name: str,
        build_number: int,
    ) -> JenkinsState:

        parts = pipeline_name.split("/")

        if (
            type(build_number) is not int
            or build_number <= 0
            or any(
                not part
                or part in {".", ".."}
                or "\\" in part
                or any(ord(c) < 32 for c in part)
                for part in parts
            )
        ):
            return JenkinsState(
                False,
                reason="INVALID_BUILD_IDENTITY",
            )

        job_path = "/".join(
            f"job/{quote(part, safe='')}"
            for part in parts
        )

        query = urlencode({
            "tree": "number,building,result,timestamp,duration,url,actions[lastBuiltRevision[SHA1]]"
        })

        url = (
            f"{self.base_url}/{job_path}/"
            f"{build_number}/api/json?{query}"
        )

        try:
            request = Request(
                url,
                headers=self.headers,
                method="GET",
            )

            with self.opener.open(
                request,
                timeout=self.timeout,
            ) as response:
                raw = response.read(65537)

            if len(raw) > 65536:
                return JenkinsState(
                    False,
                    reason="RESPONSE_TOO_LARGE",
                )

            data = json.loads(raw)

            if not isinstance(data, dict):
                raise ValueError("Invalid response")

            if (
                type(data.get("number")) is not int
                or data["number"] != build_number
            ):
                return JenkinsState(
                    False,
                    reason="BUILD_IDENTITY_MISMATCH",
                )

            building = data.get("building")
            result = data.get("result")

            if type(building) is not bool:
                raise ValueError("Invalid building state")

            if result is not None and not isinstance(
                result, str
            ):
                raise ValueError("Invalid result")

            return JenkinsState(
                True,
                building=building,
                result=result,
                metadata=data,
            )

        except Exception:
            return JenkinsState(
                False,
                reason="JENKINS_QUERY_FAILED",
            )
