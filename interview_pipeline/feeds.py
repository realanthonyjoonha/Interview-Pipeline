from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape

from interview_pipeline.catalog import watched_people
from interview_pipeline.http import fetch
from interview_pipeline.models import Episode, Show

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
PODCAST_NS = "https://podcastindex.org/namespace/1.0"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

_NS = {
    "itunes": ITUNES_NS,
    "podcast": PODCAST_NS,
    "content": CONTENT_NS,
}


def parse_duration_seconds(value: str | None) -> int | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    parts = raw.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    nums = [int(part) for part in parts]
    if len(nums) == 3:
        hours, minutes, seconds = nums
        return hours * 3600 + minutes * 60 + seconds
    if len(nums) == 2:
        minutes, seconds = nums
        return minutes * 60 + seconds
    return None


def _local(tag: str) -> str:
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[-1]
    return tag


def _child_text(item: ET.Element, name: str) -> str:
    for child in item:
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def _first_text(item: ET.Element, *names: str) -> str:
    for name in names:
        found = item.find(name, _NS)
        if found is not None and found.text:
            return found.text.strip()
        text = _child_text(item, name.split(":")[-1])
        if text:
            return text
    return ""


def _strip_html(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"[ \t]+\n", "\n", re.sub(r"[ \t]{2,}", " ", text)).strip()


def _published(item: ET.Element) -> str:
    raw = _first_text(item, "pubDate", "published", "updated")
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError, IndexError):
        return raw


def _rss_transcript_url(item: ET.Element) -> str | None:
    for child in item:
        if _local(child.tag) != "transcript":
            continue
        url = (child.attrib.get("url") or "").strip()
        if url:
            return url
    return None


def _episode_url(item: ET.Element) -> str:
    link = _first_text(item, "link")
    if link:
        return link
    guid = item.find("guid")
    if guid is not None and (guid.text or "").startswith("http"):
        return guid.text.strip()
    return ""


def parse_rss(xml_text: str, show: Show) -> list[Episode]:
    root = ET.fromstring(xml_text)
    items = root.findall("./channel/item")
    if not items:
        items = root.findall(".//item")
    people = watched_people()
    episodes: list[Episode] = []
    for item in items:
        title = unescape(_first_text(item, "title"))
        description = _strip_html(
            _first_text(item, f"{{{CONTENT_NS}}}encoded", "description", f"{{{ITUNES_NS}}}summary")
        )
        duration = parse_duration_seconds(
            _first_text(item, f"{{{ITUNES_NS}}}duration", "itunes:duration")
        )
        blob = f"{title}\n{description}"
        mentioned = [name for name in people if name.lower() in blob.lower()]
        episodes.append(
            Episode(
                show_id=show.id,
                show_name=show.name,
                title=title,
                published=_published(item),
                url=_episode_url(item),
                guid=_first_text(item, "guid") or _episode_url(item) or title,
                duration_seconds=duration,
                description=description,
                rss_transcript_url=_rss_transcript_url(item),
                watched_people=mentioned,
            )
        )
    return episodes


def fetch_episodes(show: Show) -> list[Episode]:
    if not show.feed_url:
        raise ValueError(f"Show {show.id} has no feed_url")
    response = fetch(show.feed_url, accept="application/rss+xml, application/xml, text/xml")
    return parse_rss(response.text(), show)
