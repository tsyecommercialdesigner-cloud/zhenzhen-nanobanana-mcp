"""Provider adapters: never retry a potentially billable request."""

import asyncio
import json
import re
from typing import Any

import httpx

from .config import BusinessError, Settings
from .media import MIB, Media, MediaLoader, bounded_read, decode_b64, decode_image
from .models import ApiFormat, ImageSpec, ModelName, resolve_api


class SafeConnectFailure(BusinessError):
    """All attempts failed during connection establishment, before a POST was sent."""


def image_sources(payload: dict, api_format: ApiFormat) -> list[str]:
    """Accept image fields only, not arbitrary links in explanatory text."""
    sources: list[Any] = []
    if api_format == "dalle":
        for item in payload.get("data", []):
            if isinstance(item, dict):
                value = item.get("b64_json") or item.get("url")
                if isinstance(value, str):
                    sources.append(value)
    elif api_format == "gemini":
        for candidate in payload.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                value = part.get("inlineData", part.get("inline_data", {})).get("data")
                if isinstance(value, str):
                    sources.append(value)
    else:
        for choice in payload.get("choices", []):
            message = choice.get("message", {})
            content = message.get("content", [])
            if isinstance(content, str):
                # Only explicit Markdown images or complete data URLs are accepted from text.
                sources.extend(re.findall(r"!\[[^\]]*\]\(([^\s)]+)\)", content))
                if content.startswith("data:image/"):
                    sources.append(content.strip())
            elif isinstance(content, list):
                for part in content:
                    if part.get("type") == "image_url":
                        value = part.get("image_url", {})
                        sources.append(value.get("url") if isinstance(value, dict) else value)
            for part in message.get("images", []):
                value = part.get("image_url", {})
                sources.append(value.get("url") if isinstance(value, dict) else value)
    sources = list(dict.fromkeys(s for s in sources if isinstance(s, str) and s))
    if not sources:
        raise BusinessError("上游未返回可识别图片；请核对模型权限及响应格式。")
    if len(sources) > 4:
        raise BusinessError("上游返回图片数超过每项最多 4 张的限制。")
    return sources


class Provider:
    def __init__(
        self,
        settings: Settings,
        loader: MediaLoader,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings, self.loader, self.transport = settings, loader, transport

    async def render(
        self, spec: ImageSpec, references: list[Media], model: ModelName, api_format: ApiFormat
    ) -> list[Media]:
        try:
            _, endpoint = resolve_api(
                model, api_format, getattr(spec, "endpoint", "auto"), bool(references)
            )
        except ValueError as exc:
            raise BusinessError(str(exc)) from exc
        headers = {"Authorization": f"Bearer {self.settings.api_key}", "Accept": "application/json"}
        key = getattr(spec, "_provider_key", "")
        if key:
            headers["Idempotency-Key"] = key
        args: dict[str, Any]
        if api_format == "dalle":
            body: dict[str, Any] = {
                "model": model,
                "prompt": spec.prompt,
                "aspect_ratio": spec.aspect_ratio,
                "response_format": "url",
            }
            if endpoint == "edits":
                path = "/v1/images/edits"
                files = [
                    ("image", (f"reference_{i}{ref.suffix}", ref.data, ref.mime))
                    for i, ref in enumerate(references)
                ]
                # Force multipart even for the documented no-reference Edits request.
                args = {"files": [(key, (None, value)) for key, value in body.items()] + files}
            else:
                if references:
                    body["image"] = [ref.b64 for ref in references]
                path, args = "/v1/images/generations", {"json": body}
        elif api_format == "chat":
            text_prompt = f"{spec.prompt}\n画面比例：{spec.aspect_ratio}。"
            content: list[dict[str, Any]] = [{"type": "text", "text": text_prompt}]
            content.extend(
                {"type": "image_url", "image_url": {"url": ref.data_url}} for ref in references
            )
            path = "/v1/chat/completions"
            args = {
                "json": {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": content if references else text_prompt}
                    ],
                }
            }
        else:
            parts: list[dict[str, Any]] = [
                {"text": f"{spec.prompt}\n画面比例：{spec.aspect_ratio}。"}
            ]
            parts.extend(
                {"inlineData": {"mimeType": ref.mime, "data": ref.b64}} for ref in references
            )
            path = f"/v1beta/models/{model}:generateContent"
            args = {
                "json": {
                    "contents": [{"role": "user", "parts": parts}],
                }
            }
        async with httpx.AsyncClient(
            timeout=self.settings.timeout, trust_env=False, transport=self.transport
        ) as client:
            for attempt in range(self.settings.safe_attempts):
                notify = getattr(spec, "_on_post_attempt", None)
                if notify:
                    notify()
                try:
                    async with client.stream(
                        "POST", self.settings.base_url + path, headers=headers, **args
                    ) as response:
                        if response.status_code != 200:
                            raise BusinessError(
                                f"绘图接口返回 HTTP {response.status_code}；未自动重试。"
                            )
                        raw = await bounded_read(response, 80 * MIB)
                    break
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    if attempt + 1 == self.settings.safe_attempts:
                        raise SafeConnectFailure(
                            "建立连接失败，确认未发送绘图请求；可按原幂等键安全重试。"
                        ) from None
                    await asyncio.sleep(self.settings.retry_delay * 2**attempt)
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict) or payload.get("error"):
                raise BusinessError("绘图接口返回业务错误；未自动重试。")
            sources = image_sources(payload, api_format)
        except (ValueError, AttributeError, TypeError, KeyError) as exc:
            raise BusinessError("绘图接口响应结构无效。") from exc
        checkpoint = getattr(spec, "_on_response", None)
        if checkpoint:
            checkpoint(sources)
        return await self.collect(sources)

    async def collect(self, sources: list[str]) -> list[Media]:
        """Replay an existing response using GET/decoding only, without a billable POST."""
        images = []
        for source in sources:
            raw = (
                await self.loader.download(source)
                if source.lower().startswith(("https://", "http://"))
                else decode_b64(source)
            )
            images.append(decode_image(raw))
        return images
