import time

import requests


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

    def get_access_token(self) -> str:
        token_data = self._post(
            self.token_url,
            {
                "appId": self.appid,
                "secret": self.appsecret,
                "timestamp": int(round(time.time() * 1000)),
                "scope": "app",
            },
        )
        return token_data["data"]["accessToken"]

    def acquire_user_context(self, ticket: str) -> dict:
        access_token = self.get_access_token()
        url = f"{self.user_context_url}?accessToken={access_token}"
        return self._post(url, {"appid": self.appid, "ticket": ticket})
