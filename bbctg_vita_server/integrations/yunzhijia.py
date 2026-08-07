import time

import requests

# appid -> (access_token, expires_at_epoch)
_access_token_cache: dict[str, tuple[str, float]] = {}
_TOKEN_EXPIRY_BUFFER_SECONDS = 60
_DEFAULT_TOKEN_TTL_SECONDS = 7200


class YunzhijiaClient:
    token_url = "https://yunzhijia.com/gateway/oauth2/token/getAccessToken"
    user_context_url = "https://yunzhijia.com/gateway/ticket/user/acquirecontext"

    def __init__(self, appid: str, appsecret: str) -> None:
        self.appid = appid
        self.appsecret = appsecret

    def _post(self, url: str, data: dict) -> dict:
        response = requests.post(
            url,
            json=data,
            headers={"Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def get_access_token(self, *, force_refresh: bool = False) -> str:
        now = time.time()
        cached = _access_token_cache.get(self.appid)
        if cached and cached[1] > now and not force_refresh:
            return cached[0]

        token_data = self._post(
            self.token_url,
            {
                "appId": self.appid,
                "secret": self.appsecret,
                "timestamp": int(round(time.time() * 1000)),
                "scope": "app",
            },
        )
        data = token_data.get("data") or {}
        token = data["accessToken"]
        expire_in = data.get("expireIn") or data.get("expiresIn") or _DEFAULT_TOKEN_TTL_SECONDS
        try:
            ttl = int(expire_in)
        except (TypeError, ValueError):
            ttl = _DEFAULT_TOKEN_TTL_SECONDS
        ttl = max(ttl - _TOKEN_EXPIRY_BUFFER_SECONDS, 60)
        _access_token_cache[self.appid] = (token, now + ttl)
        return token

    def acquire_user_context(self, ticket: str) -> dict:
        access_token = self.get_access_token()
        url = f"{self.user_context_url}?accessToken={access_token}"
        return self._post(url, {"appid": self.appid, "ticket": ticket})
