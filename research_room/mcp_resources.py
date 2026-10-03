"""Read-only stdio MCP resources for Research Room."""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import os
import re
import selectors
import subprocess
import time
from typing import Any
from urllib.parse import urlsplit

from .evidence_pipeline import sanitize_untrusted_content
from .tools import Connector, ConnectorRegistry


class MCPError(ValueError):
    """A configured MCP server failed or returned an invalid response."""


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: tuple[str, ...]
    env: dict[str, str]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.command or any(not part for part in self.command):
            raise ValueError("MCP server name and command are required.")
        if any(not key or "=" in key for key in self.env):
            raise ValueError("MCP environment variable names are invalid.")


class MCPStdioSession:
    """One request-scoped MCP JSON-RPC session over the stdio transport."""

    _MAX_MESSAGE_BYTES = 1_000_000
    _SAFE_INHERITED_ENV = (
        "PATH", "HOME", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT", "WINDIR",
        "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS",
    )

    def __init__(self, config: MCPServerConfig, *, timeout_seconds: float = 30) -> None:
        if timeout_seconds <= 0:
            raise ValueError("MCP timeout must be positive.")
        self.config = config
        self.timeout_seconds = timeout_seconds
        self._process: subprocess.Popen[bytes] | None = None
        self._selector = selectors.DefaultSelector()
        self._buffer = bytearray()
        self._messages: list[dict[str, Any]] = []
        self._next_id = 1

    def __enter__(self) -> MCPStdioSession:
        env = {key: os.environ[key] for key in self._SAFE_INHERITED_ENV if key in os.environ}
        env.update(self.config.env)
        try:
            self._process = subprocess.Popen(
                self.config.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                bufsize=0,
            )
        except OSError as error:
            self._selector.close()
            raise MCPError(f"Could not start configured MCP server {self.config.name!r}.") from error
        assert self._process.stdout is not None
        self._selector.register(self._process.stdout, selectors.EVENT_READ)
        try:
            initialized = self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "coolie-research-room", "version": "1.0"},
            })
            if not isinstance(initialized, dict):
                raise MCPError(f"MCP server {self.config.name!r} returned an invalid initialize result.")
            self._notify("notifications/initialized", {})
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        process, self._process = self._process, None
        self._selector.close()
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if process.stdout is not None:
            process.stdout.close()

    def list_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            params = {"cursor": cursor} if cursor is not None else {}
            result = self._request("tools/list", params)
            page = result.get("tools")
            if not isinstance(page, list) or any(
                not isinstance(tool, dict) or not isinstance(tool.get("name"), str)
                for tool in page
            ):
                raise MCPError(f"MCP server {self.config.name!r} returned an invalid tool list.")
            tools.extend(page)
            next_cursor = result.get("nextCursor")
            if next_cursor is None:
                return tools
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                raise MCPError(f"MCP server {self.config.name!r} returned an invalid tool-list cursor.")
            seen_cursors.add(next_cursor)
            if len(seen_cursors) >= 100:
                raise MCPError(f"MCP server {self.config.name!r} exceeded the tool-list page limit.")
            cursor = next_cursor

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict) or result.get("isError") is True:
            raise MCPError(f"MCP server {self.config.name!r} reported a tool-call failure.")
        return result

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        deadline = time.monotonic() + self.timeout_seconds
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            message = self._read_message(deadline)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise MCPError(f"MCP server {self.config.name!r} rejected {method}.")
            result = message.get("result")
            if not isinstance(result, dict):
                raise MCPError(f"MCP server {self.config.name!r} returned an invalid {method} result.")
            return result

    def _write(self, message: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise MCPError(f"MCP server {self.config.name!r} is not running.")
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        try:
            process.stdin.write(payload)
            process.stdin.flush()
        except OSError as error:
            raise MCPError(f"Could not send a request to MCP server {self.config.name!r}.") from error

    def _read_message(self, deadline: float) -> dict[str, Any]:
        while not self._messages:
            line_end = self._buffer.find(b"\n")
            if line_end >= 0:
                if line_end > self._MAX_MESSAGE_BYTES:
                    raise MCPError(f"MCP server {self.config.name!r} exceeded the message-size limit.")
                line = bytes(self._buffer[:line_end])
                del self._buffer[:line_end + 1]
                try:
                    value = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise MCPError(f"MCP server {self.config.name!r} sent malformed JSON-RPC.") from error
                if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
                    raise MCPError(f"MCP server {self.config.name!r} sent an invalid JSON-RPC message.")
                if "id" not in value:
                    continue
                self._messages.append(value)
                break
            if len(self._buffer) > self._MAX_MESSAGE_BYTES:
                raise MCPError(f"MCP server {self.config.name!r} exceeded the message-size limit.")
            process = self._process
            if process is None or process.poll() is not None:
                raise MCPError(f"MCP server {self.config.name!r} exited before replying.")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPError(f"MCP server {self.config.name!r} timed out.")
            ready = self._selector.select(remaining)
            if not ready:
                raise MCPError(f"MCP server {self.config.name!r} timed out.")
            assert process.stdout is not None
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                raise MCPError(f"MCP server {self.config.name!r} closed its response stream.")
            self._buffer.extend(chunk)
        return self._messages.pop(0)


def _clean_result(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_untrusted_content(value)[0]
    if isinstance(value, list):
        return [_clean_result(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_result(item) for key, item in value.items()}
    return value


def _tool_text(result: dict[str, Any]) -> str:
    structured = result.get("structuredContent")
    if structured is not None:
        return json.dumps(_clean_result(structured), ensure_ascii=False, separators=(",", ":"))
    content = result.get("content", [])
    if not isinstance(content, list):
        raise MCPError("MCP tool returned malformed content.")
    chunks: list[str] = []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            chunks.append(sanitize_untrusted_content(item["text"])[0])
    return "\n".join(chunks)


def _public_http_url(value: str, allowed_hosts: tuple[str, ...] | None) -> bool:
    if any(ord(character) < 32 for character in value):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return False
        if parsed.port not in {None, 80, 443}:
            return False
        hostname = parsed.hostname.rstrip(".").lower()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".localhost", ".local", ".internal")):
            return False
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            return False
        if allowed_hosts is None:
            return True
        return any(hostname == allowed or (allowed.startswith("*.") and hostname.endswith(allowed[1:]) and hostname != allowed[2:]) for allowed in allowed_hosts)
    except ValueError:
        return False


def _result_urls(value: Any, allowed_hosts: tuple[str, ...] | None) -> list[str]:
    candidates: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in {"url", "link", "source_url"} and isinstance(item, str):
                candidates.append(item)
            candidates.extend(_result_urls(item, allowed_hosts))
    elif isinstance(value, list):
        for item in value:
            candidates.extend(_result_urls(item, allowed_hosts))
    elif isinstance(value, str):
        candidates.extend(re.findall(r"https?://[^\s\"'<>]+", value))
    result: list[str] = []
    for candidate in candidates:
        candidate = candidate.rstrip(".,;:)]}")
        if candidate not in result and _public_http_url(candidate, allowed_hosts):
            result.append(candidate)
    return result


class ResearchMCPBridge:
    """Combines Firecrawl, OpenSearch, and read-only Playwright results."""

    def __init__(
        self,
        servers: dict[str, MCPServerConfig],
        *,
        opensearch_index: str,
        browser_allowed_hosts: tuple[str, ...],
        timeout_seconds: float = 30,
        max_result_bytes: int = 500_000,
        browser_page_limit: int = 3,
    ) -> None:
        if not isinstance(opensearch_index, str) or not opensearch_index.strip():
            raise ValueError("An OpenSearch index is required.")
        if not browser_allowed_hosts:
            raise ValueError("Browser navigation requires an explicit host allowlist.")
        if timeout_seconds <= 0 or max_result_bytes <= 0 or not 1 <= browser_page_limit <= 10:
            raise ValueError("MCP result and browser page limits are invalid.")
        required = {"firecrawl", "opensearch", "browser"}
        if not required <= servers.keys():
            raise ValueError(f"MCP server configuration is missing: {sorted(required - servers.keys())}")
        self.servers = servers
        self.opensearch_index = opensearch_index
        hosts = tuple(host.casefold().rstrip(".") for host in browser_allowed_hosts)
        if any(
            not host
            or (host.startswith("*.") and (host[2:].count(".") < 1 or "*" in host[2:]))
            or ("*" in host and not host.startswith("*."))
            or "/" in host
            or ":" in host
            for host in hosts
        ):
            raise ValueError("Browser allowlist entries must be exact hosts or non-broad *.subdomain patterns.")
        self.browser_allowed_hosts = hosts
        self.timeout_seconds = timeout_seconds
        self.max_result_bytes = max_result_bytes
        self.browser_page_limit = browser_page_limit

    @classmethod
    def from_environment(cls) -> ResearchMCPBridge:
        env = os.environ
        required = ("FIRECRAWL_API_KEY", "OPENSEARCH_URL", "OPENSEARCH_INDEX", "COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS")
        missing = [key for key in required if not env.get(key, "").strip()]
        if missing:
            raise ValueError(f"Research MCP configuration is missing: {', '.join(missing)}")
        firecrawl_env = {"FIRECRAWL_API_KEY": env["FIRECRAWL_API_KEY"]}
        opensearch_env = {"OPENSEARCH_URL": env["OPENSEARCH_URL"]}
        for key in (
            "OPENSEARCH_USERNAME", "OPENSEARCH_PASSWORD", "AWS_REGION",
            "AWS_DEFAULT_REGION", "AWS_PROFILE", "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
            "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_ROLE_ARN",
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI", "AWS_EC2_METADATA_DISABLED",
        ):
            if env.get(key):
                opensearch_env[key] = env[key]
        servers = {
            "firecrawl": MCPServerConfig("firecrawl", ("npx", "-y", "firecrawl-mcp"), firecrawl_env),
            "opensearch": MCPServerConfig("opensearch", ("uvx", "opensearch-mcp-server-py"), opensearch_env),
            "browser": MCPServerConfig("playwright", ("npx", "-y", "@playwright/mcp@latest", "--headless"), {}),
        }
        allowed_hosts = tuple(host.strip() for host in env["COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS"].split(",") if host.strip())
        return cls(servers, opensearch_index=env["OPENSEARCH_INDEX"], browser_allowed_hosts=allowed_hosts)

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        objective = arguments.get("objective")
        markets = arguments.get("markets")
        if not isinstance(objective, str) or not objective.strip():
            raise ValueError("Research MCP calls require a non-empty objective.")
        if not isinstance(markets, list) or any(not isinstance(market, str) for market in markets):
            raise ValueError("Research MCP markets must be a list of strings.")
        query = f"{objective.strip()} — markets: {', '.join(markets)}" if markets else objective.strip()
        output: dict[str, Any] = {}

        with MCPStdioSession(self.servers["firecrawl"], timeout_seconds=self.timeout_seconds) as firecrawl:
            available = {item.get("name") for item in firecrawl.list_tools()}
            self._require_tools("firecrawl", available, {"firecrawl_search", "firecrawl_scrape"})
            search = firecrawl.call_tool("firecrawl_search", {
                "query": query,
                "limit": 5,
                "scrapeOptions": {"formats": ["markdown"]},
            })
            output["firecrawl_search"] = _tool_text(search)
            urls = _result_urls(search, None)[:self.browser_page_limit]
            browser_urls = [url for url in urls if _public_http_url(url, self.browser_allowed_hosts)]
            if urls:
                output["firecrawl_scrape"] = [
                    _tool_text(firecrawl.call_tool("firecrawl_scrape", {"url": url, "formats": ["markdown"]}))
                    for url in urls
                ]

        with MCPStdioSession(self.servers["opensearch"], timeout_seconds=self.timeout_seconds) as opensearch:
            available = {item.get("name") for item in opensearch.list_tools()}
            self._require_tools("opensearch", available, {"SearchIndexTool"})
            result = opensearch.call_tool("SearchIndexTool", {
                "index": self.opensearch_index,
                "query_dsl": {"query": {"query_string": {"query": objective.strip()}}},
                "size": 10,
                "format": "json",
            })
            output["opensearch"] = _tool_text(result)

        if browser_urls:
            with MCPStdioSession(self.servers["browser"], timeout_seconds=self.timeout_seconds) as browser:
                available = {item.get("name") for item in browser.list_tools()}
                self._require_tools("browser", available, {"browser_navigate", "browser_snapshot"})
                pages = []
                for url in browser_urls:
                    browser.call_tool("browser_navigate", {"url": url})
                    pages.append({"url": url, "snapshot": _tool_text(browser.call_tool("browser_snapshot", {}))})
                output["browser"] = pages

        encoded = json.dumps(output, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > self.max_result_bytes:
            raise MCPError("Combined MCP result exceeded the Research Room size limit.")
        return output

    @staticmethod
    def _require_tools(server: str, available: set[Any], required: set[str]) -> None:
        missing = required - available
        if missing:
            raise MCPError(f"Configured {server} MCP server is missing required read tools: {sorted(missing)}")


def register_research_mcp_connector(registry: ConnectorRegistry, bridge: ResearchMCPBridge) -> None:
    """Install the bridge using the connector name already used by Research Room agents."""
    registry.register(Connector(
        "search",
        "research:web:search",
        "web",
        bridge.execute,
        source_types=("web", "internal"),
    ))
