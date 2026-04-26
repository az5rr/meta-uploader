from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from app.config import Settings


class MetaApiError(RuntimeError):
    pass


class MetaApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_reel_container(
        self,
        video_url: str,
        caption: str,
        trial_params: dict[str, str] | None = None,
    ) -> str:
        payload: dict[str, object] = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
        }
        if trial_params:
            payload["trial_params"] = trial_params
        response = self._post(f"/{self.settings.meta_ig_user_id}/media", payload)
        creation_id = response.get("id")
        if not creation_id:
            raise MetaApiError(f"Unexpected create container response: {response}")
        return creation_id

    def create_post_container(self, image_url: str, caption: str) -> str:
        payload: dict[str, object] = {
            "image_url": image_url,
            "caption": caption,
        }
        response = self._post(f"/{self.settings.meta_ig_user_id}/media", payload)
        creation_id = response.get("id")
        if not creation_id:
            raise MetaApiError(f"Unexpected create container response: {response}")
        return creation_id

    def wait_for_container(self, creation_id: str, timeout_seconds: int = 300) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            response = self._get(f"/{creation_id}", {"fields": "status_code,status"})
            status_code = response.get("status_code", "")
            if status_code == "FINISHED":
                return
            if status_code in {"ERROR", "EXPIRED"}:
                raise MetaApiError(f"Container {creation_id} failed with status {status_code}: {response}")
            time.sleep(self.settings.meta_poll_seconds)
        raise MetaApiError(f"Timed out waiting for container {creation_id} to finish")

    def publish_container(self, creation_id: str) -> str:
        response = self._post(
            f"/{self.settings.meta_ig_user_id}/media_publish",
            {"creation_id": creation_id},
        )
        media_id = response.get("id")
        if not media_id:
            raise MetaApiError(f"Unexpected publish response: {response}")
        return media_id

    def get_content_publishing_limit(self) -> dict:
        return self._get(f"/{self.settings.meta_ig_user_id}/content_publishing_limit", {})

    def list_recent_media(self, limit: int = 2) -> list[dict]:
        response = self._get(
            f"/{self.settings.meta_ig_user_id}/media",
            {
                "fields": "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
                "limit": str(limit),
            },
        )
        data = response.get("data", [])
        return data if isinstance(data, list) else []

    def get_media_details(self, media_id: str) -> dict:
        return self._get(
            f"/{media_id}",
            {"fields": "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count"},
        )

    def get_media_insights(self, media_id: str, metrics: list[str]) -> dict[str, int | float | str]:
        response = self._get(f"/{media_id}/insights", {"metric": ",".join(metrics)})
        result: dict[str, int | float | str] = {}
        for item in response.get("data", []):
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            values = item.get("values")
            if not name or not isinstance(values, list) or not values:
                continue
            first_value = values[0]
            if isinstance(first_value, dict) and "value" in first_value:
                result[str(name)] = first_value["value"]
        return result

    def publish_reel(
        self,
        video_url: str,
        caption: str,
        trial_params: dict[str, str] | None = None,
    ) -> dict[str, str]:
        creation_id = self.create_reel_container(
            video_url=video_url,
            caption=caption,
            trial_params=trial_params,
        )
        self.wait_for_container(creation_id)
        media_id = self.publish_container(creation_id)
        return {"creation_id": creation_id, "media_id": media_id}

    def publish_post(self, image_url: str, caption: str) -> dict[str, str]:
        creation_id = self.create_post_container(
            image_url=image_url,
            caption=caption,
        )
        self.wait_for_container(creation_id)
        media_id = self.publish_container(creation_id)
        return {"creation_id": creation_id, "media_id": media_id}

    def _get(self, path: str, params: dict[str, str]) -> dict:
        query = urllib.parse.urlencode(params)
        url = f"{self.settings.graph_base_url}{path}?{query}"
        return self._request("GET", url)

    def _post(self, path: str, payload: dict[str, object]) -> dict:
        encoded = json.dumps(payload).encode("utf-8")
        url = f"{self.settings.graph_base_url}{path}"
        return self._request("POST", url, data=encoded)

    def _request(self, method: str, url: str, data: bytes | None = None) -> dict:
        request = urllib.request.Request(
            url=url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.settings.meta_access_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise MetaApiError(f"Meta API HTTP {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            raise MetaApiError(f"Meta API request failed: {exc.reason}") from exc
