#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight GraphQL client with retry logic for Aerodrome subgraph."""
from __future__ import annotations
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict

class GraphQLError(RuntimeError):
    """Raised when the GraphQL endpoint returns errors."""


def graph_query(
    query: str,
    variables: Dict[str, Any] | None = None,
    *,
    endpoint: str | None = None,
    retries: int = 3,
    backoff_seconds: float = 1.5,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Execute a GraphQL query against the Aerodrome subgraph."""

    url = endpoint or os.environ.get("AERODROME_API")
    if not url:
        raise RuntimeError("AERODROME_API environment variable not set")

    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, headers={"content-type": "application/json"}, method="POST"
    )

    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                document = json.loads(response.read())
                if "errors" in document:
                    raise GraphQLError(document["errors"])
                return document
        except (urllib.error.URLError, GraphQLError) as exc:
            if attempt >= retries:
                raise
            time.sleep(backoff_seconds * attempt)
