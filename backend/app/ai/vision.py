"""Conservative vision observations for resource images.

This module never makes compatibility decisions. It only describes visible
features for a coordinator to review in the resource verification workflow.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel


class ResourceImageObservations(BaseModel):
    stairs_visible: Optional[bool] = None
    ramp_visible: Optional[bool] = None
    step_free_access_visible: Optional[bool] = None
    wheelchair_accessibility_verified: Optional[bool] = None
    evidence: list[str] = []


async def observe_resource_image(image_bytes: bytes, content_type: str, inspection_note: str = "") -> ResourceImageObservations:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Vision service is unavailable.")

    image_data = base64.b64encode(image_bytes).decode("ascii")
    client = AsyncOpenAI(api_key=api_key)
    prompt = """You inspect a shelter or vehicle image for emergency-accessibility evidence.
Return JSON only with stairs_visible, ramp_visible, step_free_access_visible,
wheelchair_accessibility_verified (true, false, or null) and evidence (short list).
Describe only what is visually observable. A visible staircase does NOT prove
wheelchair inaccessibility. If an entrance, ramp, or access route is not clearly
visible, return null rather than false. Never make SAFE, UNKNOWN, or BLOCKED decisions."""
    if inspection_note:
        prompt += f"\nCoordinator inspection focus: {inspection_note[:500]}"
    response = await client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{image_data}", "detail": "low"}},
            ],
        }],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=250,
    )
    return ResourceImageObservations(**json.loads(response.choices[0].message.content or "{}"))
