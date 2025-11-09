# mqtt_message.py
from __future__ import annotations

import io
import json
import re
import paho.mqtt.client as mqtt
from functools import cached_property
from typing import Any, Optional, Union, Dict, Tuple
from simplemqtt import QualityOfService as QoS

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None  # type: ignore


StringOrBytes = Union[str, bytes, None]


def bytes_to_text(data: StringOrBytes, *, encoding: str) -> str:
    """Decode bytes to text with 'replace' and strip whitespace."""
    if data is None:
        return ""
    if isinstance(data, str):
        return data.strip()
    return data.decode(encoding, errors="replace").strip()


def parse_content_type(content_type_header: Optional[str]) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Parse a HTTP-like Content-Type header into (media_type, parameters).
    Example: "application/json; charset=utf-8"
    """
    if not isinstance(content_type_header, str) or not content_type_header.strip():
        return None, {}
    segments = [segment.strip() for segment in content_type_header.split(";") if segment.strip()]
    media_type = segments[0].lower() if segments else None
    parameters: Dict[str, str] = {}
    for parameter in segments[1:]:
        if "=" in parameter:
            key, value = parameter.split("=", 1)
            parameters[key.strip().lower()] = value.strip().strip('"').strip("'")
    return media_type, parameters


def sniff_image_magic(payload_bytes: bytes) -> Optional[str]:
    """Tiny magic-number sniffing for common image formats."""
    if payload_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if payload_bytes.startswith(b"GIF87a") or payload_bytes.startswith(b"GIF89a"):
        return "image/gif"
    if payload_bytes[:4] == b"RIFF" and payload_bytes[8:12] == b"WEBP":
        return "image/webp"
    if payload_bytes.startswith(b"BM"):
        return "image/bmp"
    head = payload_bytes[:256].lstrip()
    if head.startswith(b"<?xml") or head.startswith(b"<svg"):
        return "image/svg+xml"
    return None


class MQTTMessage:
    """Paho MQTTMessage wrapper with robust decoding, cached metadata, and type helpers."""

    # ---------- init ----------
    def __init__(self, message: mqtt.MQTTMessage):
        self._message = message
        self._default_text_encoding = "utf-8"

    # ---------- raw access (cheap; caching optional) ----------
    @property
    def raw(self) -> mqtt.MQTTMessage:
        return self._message

    @cached_property
    def topic(self) -> str:
        return getattr(self._message, "topic", "") or ""

    @cached_property
    def qos(self) -> Optional[QoS]:
        raw_value = getattr(self._message, "qos", None)
        if raw_value is None:
            return None
        try:
            return QoS(int(raw_value))
        except ValueError:
            return None

    @cached_property
    def retain(self) -> bool:
        return bool(getattr(self._message, "retain", False))

    @cached_property
    def _properties(self):
        return getattr(self._message, "properties", None)

    @cached_property
    def _payload_obj(self) -> StringOrBytes:
        return getattr(self._message, "payload", None)

    # ---------- v5 metadata ----------
    @cached_property
    def payload_format_indicator(self) -> Optional[int]:
        return getattr(self._properties, "PayloadFormatIndicator", None)

    @cached_property
    def content_type(self) -> Optional[str]:
        return getattr(self._properties, "ContentType", None)

    @cached_property
    def media_type_and_parameters(self) -> Tuple[Optional[str], Dict[str, str]]:
        return parse_content_type(self.content_type)

    @cached_property
    def media_type(self) -> Optional[str]:
        media_type, _ = self.media_type_and_parameters
        return media_type

    # ---------- encoding resolution ----------
    @cached_property
    def text_encoding(self) -> str:
        """
        Priority:
          1) MQTT v5 PayloadFormatIndicator == 1 => UTF-8
          2) Content-Type 'charset' parameter
          3) default_text_encoding
        """
        if self.payload_format_indicator == 1:
            return "utf-8"
        _, parameters = self.media_type_and_parameters
        charset = parameters.get("charset")
        if isinstance(charset, str) and charset:
            return charset
        return self._default_text_encoding

    # ---------- cached type flags ----------
    @cached_property
    def is_text(self) -> bool:
        if self.payload_format_indicator == 1:
            return True
        if not self.media_type:
            return False
        if self.media_type.startswith("text/"):
            return True
        if self.media_type in ("application/json", "application/xml"):
            return True
        if self.media_type.endswith("+json") or self.media_type.endswith("+xml"):
            return True
        if self.media_type == "image/svg+xml":
            return True
        return False

    @cached_property
    def is_json(self) -> bool:
        if self.media_type and (
            self.media_type == "application/json"
            or self.media_type.endswith("+json")
            or self.media_type == "text/json"
        ):
            return True
        try:
            _ = self.text  # will raise if undecodable
            json.loads(self.text)
            return True
        except Exception:
            return False

    @cached_property
    def is_image(self) -> bool:
        if self.media_type and (self.media_type.startswith("image/") or self.media_type == "image/svg+xml"):
            return True
        return sniff_image_magic(self.payload_bytes) is not None

    @cached_property
    def is_audio(self) -> bool:
        return bool(self.media_type and self.media_type.startswith("audio/"))

    @cached_property
    def is_binary(self) -> bool:
        return not self.is_text

    # ---------- cached conversions ----------
    @cached_property
    def payload_bytes(self) -> bytes:
        """Payload as bytes. Empty bytes if None."""
        payload = self._payload_obj
        if payload is None:
            return b""
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload)
        # Paho v3 may carry str; encode deterministically
        return bytes(str(payload), self.text_encoding)

    @cached_property
    def text(self) -> str:
        """Payload as text using resolved encoding. Always stripped."""
        return self.get_text(self.text_encoding)

    @cached_property
    def json_value(self) -> Any:
        """Parsed JSON value. Raises on invalid JSON."""
        return json.loads(self.text)

    @cached_property
    def image_bytes_and_media_type(self) -> Tuple[bytes, Optional[str]]:
        """
        Return (bytes, media_type) if the payload looks like an image.
        Raises TypeError if it does not.
        """
        media_type = self.media_type
        if not (media_type and media_type.startswith("image/")):
            sniffed = sniff_image_magic(self.payload_bytes)
            media_type = sniffed or media_type
        if not media_type or not (media_type.startswith("image/") or media_type == "image/svg+xml"):
            raise TypeError("Payload is not an image")
        return self.payload_bytes, media_type

    @cached_property
    def boolean_value(self) -> bool:
        """
        Convert payload to bool.
        Rules:
          - If JSON: return JSON boolean or numeric != 0 or string mapping.
          - Else text mapping (case-insensitive):
            true/false, on/off, yes/no, 1/0, open/closed, online/offline.
          - Fallback: non-empty string is True, empty is False.
        """
        if self.is_json:
            value = self.json_value
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            text_value = value if isinstance(value, str) else str(value)
        else:
            text_value = self.text

        normalized = text_value.strip().lower()
        truthy = {"1", "true", "t", "yes", "y", "on", "open", "online"}
        falsy = {"0", "false", "f", "no", "n", "off", "closed", "offline"}
        if normalized in truthy:
            return True
        if normalized in falsy:
            return False
        return bool(normalized)

    @cached_property
    def integer_value(self) -> int:
        """
        Convert payload to int.
        - If JSON number -> int(value).
        - Else parse trimmed text strictly.
        """
        if self.is_json:
            value = self.json_value
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            text_value = str(value).strip()
        else:
            text_value = self.text

        candidate = text_value.strip()
        if not re.fullmatch(r"[+-]?\d+", candidate):
            raise ValueError(f"Payload is not an integer: {text_value!r}")
        return int(candidate)

    @cached_property
    def float_value(self) -> float:
        """
        Convert payload to float.
        - If JSON number -> float(value).
        - Else parse trimmed text strictly (supports scientific notation).
        """
        if self.is_json:
            value = self.json_value
            if isinstance(value, bool):
                return float(int(value))
            if isinstance(value, (int, float)):
                return float(value)
            text_value = str(value).strip()
        else:
            text_value = self.text

        candidate = text_value.strip()
        if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", candidate):
            raise ValueError(f"Payload is not a float: {text_value!r}")
        return float(candidate)

    # ---------- public getters (thin wrappers) ----------
    def get_image_pil(self):
        """Return a PIL.Image.Image. Requires Pillow to be installed."""
        if Image is None:
            raise ImportError("Pillow is not installed")
        image_bytes, _ = self.image_bytes_and_media_type
        return Image.open(io.BytesIO(image_bytes))

    def get_text(self, encoding) -> str:
        return bytes_to_text(self._payload_obj, encoding=encoding)

    # ---------- comparisons ----------
    def __str__(self) -> str:
        return self.text

    def __eq__(self, other: object) -> bool:
        """
        Supported comparisons:
          - str: decoded text equality
          - bytes/bytearray: raw bytes equality
          - dict/list: JSON deep equality
          - bool: boolean conversion equality
        """
        if isinstance(other, str):
            return self.text == other
        if isinstance(other, (bytes, bytearray)):
            other_bytes = other if isinstance(other, bytes) else bytes(other)
            return self.payload_bytes == other_bytes
        if isinstance(other, (dict, list)):
            try:
                return self.json_value == other
            except Exception:
                return False
        if isinstance(other, bool):
            try:
                return self.boolean_value is other
            except Exception:
                return False
        return NotImplemented

    def __repr__(self) -> str:
        preview = self.text if self.is_text else f"<{len(self.payload_bytes)} bytes>"
        return f"MQTTMessage(topic={self.topic!r}, media_type={self.media_type!r}, preview={preview!r})"
