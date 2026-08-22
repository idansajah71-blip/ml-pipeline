"""Auth Scraper — Login/session management, cookie persistence, OAuth support."""
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    login_url: str = ""
    login_method: str = "POST"
    credentials: dict = field(default_factory=dict)
    form_fields: dict = field(default_factory=dict)
    cookie_file: str = ""
    headers: dict = field(default_factory=dict)
    timeout: int = 30
    verify_ssl: bool = True
    proxy: str = None
    max_retries: int = 3
    auto_refresh: bool = True
    refresh_interval: int = 3600
    oauth_config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "login_url": self.login_url,
            "login_method": self.login_method,
            "has_credentials": bool(self.credentials),
            "has_oauth": bool(self.oauth_config),
            "cookie_file": self.cookie_file,
            "verify_ssl": self.verify_ssl,
            "auto_refresh": self.auto_refresh,
        }


@dataclass
class AuthConfig:
    login_url: str = ""
    username: str = ""
    password: str = ""
    auth_type: str = "session"
    api_key: str = ""
    api_header: str = "Authorization"
    extra: dict = field(default_factory=dict)


@dataclass
class SessionState:
    is_authenticated: bool = False
    cookies: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    token: str = ""
    token_type: str = ""
    expires_at: Optional[str] = None
    last_refresh: Optional[str] = None
    domain: str = ""
    user_agent: str = ""

    def to_dict(self) -> dict:
        return {
            "is_authenticated": self.is_authenticated,
            "cookie_count": len(self.cookies),
            "has_token": bool(self.token),
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "domain": self.domain,
        }


class AuthScraper:

    def __init__(self):
        self._sessions: Dict[str, httpx.AsyncClient] = {}
        self._states: Dict[str, SessionState] = {}
        self._configs: Dict[str, SessionConfig] = {}

    async def login(self, config: SessionConfig) -> SessionState:
        state = SessionState(domain=urlparse(config.login_url).netloc)
        self._configs[state.domain] = config

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            **config.headers,
        }

        client_kwargs = {
            "timeout": config.timeout,
            "follow_redirects": True,
            "headers": headers,
            "verify": config.verify_ssl,
        }
        if config.proxy:
            client_kwargs["proxy"] = config.proxy

        client = httpx.AsyncClient(**client_kwargs)

        try:
            if config.login_method.upper() == "GET":
                resp = await client.get(config.login_url)
            else:
                form_data = {}
                for field_name, value in config.credentials.items():
                    form_field = config.form_fields.get(field_name, field_name)
                    form_data[form_field] = value
                resp = await client.post(config.login_url, data=form_data)

            state.cookies = dict(resp.cookies)
            state.headers = dict(resp.headers)
            state.is_authenticated = resp.status_code == 200

            token = resp.headers.get("authorization", "")
            if token:
                state.token = token
                state.token_type = "Bearer" if token.startswith("Bearer") else "token"

            state.last_refresh = datetime.now().isoformat()
            old_client = self._sessions.get(state.domain)
            if old_client and not old_client.is_closed:
                await old_client.aclose()
            self._sessions[state.domain] = client
            self._states[state.domain] = state

            logger.info(f"Login {'successful' if state.is_authenticated else 'failed'} for {state.domain}")

        except Exception as e:
            state.is_authenticated = False
            logger.error(f"Login failed for {config.login_url}: {e}")
            await client.aclose()

        return state

    async def login_oauth(self, config: SessionConfig) -> SessionState:
        state = SessionState(domain=urlparse(config.login_url).netloc)
        client = httpx.AsyncClient(timeout=config.timeout, follow_redirects=True)

        try:
            token_url = config.oauth_config.get("token_url", "")
            client_id = config.oauth_config.get("client_id", "")
            client_secret = config.oauth_config.get("client_secret", "")
            grant_type = config.oauth_config.get("grant_type", "client_credentials")

            resp = await client.post(token_url, data={
                "grant_type": grant_type,
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": config.oauth_config.get("scope", ""),
            })

            if resp.status_code == 200:
                data = resp.json()
                state.token = data.get("access_token", "")
                state.token_type = data.get("token_type", "Bearer")
                expires_in = data.get("expires_in", 3600)
                from datetime import timedelta
                state.expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
                state.is_authenticated = True
                state.headers["Authorization"] = f"{state.token_type} {state.token}"

            self._sessions[state.domain] = client
            self._states[state.domain] = state

        except Exception as e:
            state.is_authenticated = False
            logger.error(f"OAuth login failed: {e}")
            await client.aclose()

        return state

    async def login_jwt(self, config: SessionConfig) -> SessionState:
        state = SessionState(domain=urlparse(config.login_url).netloc)
        client = httpx.AsyncClient(timeout=config.timeout, follow_redirects=True)

        try:
            resp = await client.post(config.login_url, json=config.credentials)
            if resp.status_code == 200:
                data = resp.json()
                state.token = data.get("access_token", data.get("token", ""))
                state.token_type = "Bearer"
                state.is_authenticated = bool(state.token)
                if state.token:
                    state.headers["Authorization"] = f"Bearer {state.token}"

            self._sessions[state.domain] = client
            self._states[state.domain] = state

        except Exception as e:
            state.is_authenticated = False
            logger.error(f"JWT login failed: {e}")
            await client.aclose()

        return state

    async def login_api_key(self, config: SessionConfig) -> SessionState:
        state = SessionState(domain=urlparse(config.login_url).netloc)
        client = httpx.AsyncClient(timeout=config.timeout, follow_redirects=True)

        try:
            api_key = config.credentials.get("api_key", "")
            header_name = config.form_fields.get("header", "X-API-Key")

            headers = {header_name: api_key}
            resp = await client.get(config.login_url, headers=headers)
            state.is_authenticated = resp.status_code == 200
            state.cookies = dict(resp.cookies)
            state.headers = {**resp.headers, header_name: api_key}

            self._sessions[state.domain] = client
            self._states[state.domain] = state

        except Exception as e:
            state.is_authenticated = False
            logger.error(f"API key auth failed: {e}")
            await client.aclose()

        return state

    async def scrape_with_session(self, url: str, method: str = "GET",
                                  data: dict = None, json_data: dict = None) -> dict:
        domain = urlparse(url).netloc
        client = self._sessions.get(domain)
        state = self._states.get(domain)
        config = self._configs.get(domain)

        if not client or not state:
            client = httpx.AsyncClient(timeout=30, follow_redirects=True)
            state = SessionState()
            domain = urlparse(url).netloc
            self._sessions[domain] = client
            self._states[domain] = state

        if config and config.auto_refresh and state.last_refresh:
            try:
                last = datetime.fromisoformat(state.last_refresh)
                if (datetime.now() - last).total_seconds() > config.refresh_interval:
                    await self.login(config)
                    client = self._sessions.get(domain, client)
            except Exception:
                pass

        try:
            headers = state.headers if state.is_authenticated else {}
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                resp = await client.post(url, data=data, json=json_data, headers=headers)
            elif method.upper() == "PUT":
                resp = await client.put(url, data=data, json=json_data, headers=headers)
            elif method.upper() == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                resp = await client.request(method, url, headers=headers)

            return {
                "status_code": resp.status_code,
                "text": resp.text,
                "headers": dict(resp.headers),
                "cookies": dict(resp.cookies),
                "url": str(resp.url),
            }
        except Exception as e:
            return {"error": str(e), "status_code": 0}

    async def save_session(self, domain: str, filepath: str) -> bool:
        state = self._states.get(domain)
        if not state:
            return False
        data = {
            "domain": domain,
            "cookies": state.cookies,
            "headers": state.headers,
            "token": state.token,
            "token_type": state.token_type,
            "is_authenticated": state.is_authenticated,
            "saved_at": datetime.now().isoformat(),
        }
        await asyncio.to_thread(self._write_session_sync, filepath, data)
        return True

    def _write_session_sync(self, filepath: str, data: dict) -> None:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    async def load_session(self, filepath: str) -> SessionState:
        data = await asyncio.to_thread(self._read_session_sync, filepath)
        state = SessionState(
            domain=data.get("domain", ""),
            cookies=data.get("cookies", {}),
            headers=data.get("headers", {}),
            token=data.get("token", ""),
            token_type=data.get("token_type", ""),
            is_authenticated=data.get("is_authenticated", False),
        )
        self._states[state.domain] = state
        return state

    def _read_session_sync(self, filepath: str) -> dict:
        with open(filepath) as f:
            return json.load(f)

    def get_state(self, domain: str) -> Optional[SessionState]:
        return self._states.get(domain)

    def list_sessions(self) -> List[dict]:
        return [s.to_dict() for s in self._states.values()]

    async def close_all(self):
        for client in self._sessions.values():
            await client.aclose()
        self._sessions.clear()

    async def scrape(self, url: str, method: str = "GET") -> dict:
        """Scrape a URL using existing session."""
        return await self.scrape_with_session(url, method)

    async def scrape_multiple(self, session: Any, urls: List[str],
                              max_pages: int = 10) -> list[dict]:
        """Scrape multiple URLs using provided session or default session."""
        results = []
        for url in urls[:max_pages]:
            try:
                if session and isinstance(session, httpx.AsyncClient):
                    domain = urlparse(url).netloc
                    state = self._states.get(domain)
                    headers = state.headers if state and state.is_authenticated else {}
                    resp = await session.get(url, headers=headers)
                    results.append({
                        "status_code": resp.status_code,
                        "text": resp.text,
                        "headers": dict(resp.headers),
                        "url": str(resp.url),
                    })
                else:
                    result = await self.scrape_with_session(url)
                    results.append(result)
            except Exception as e:
                results.append({"url": url, "error": str(e)})
        return results

    async def session_auth(self, config: AuthConfig) -> SessionState:
        """Authenticate using session-based login."""
        session_config = SessionConfig(
            login_url=config.login_url,
            credentials={"username": config.username, "password": config.password},
        )
        return await self.login(session_config)

    async def api_key_auth(self, config: AuthConfig) -> SessionState:
        """Authenticate using API key."""
        session_config = SessionConfig(
            login_url=config.login_url,
            credentials={"api_key": config.api_key},
            form_fields={"header": config.api_header},
        )
        return await self.login_api_key(session_config)


class AuthenticatedScraper(AuthScraper):
    """Extended scraper with auth helpers used by the API."""
