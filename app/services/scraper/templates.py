"""Scrape Template — Save and reuse scrape configurations."""
import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ScrapeTemplate:
    id: str
    user_id: str
    name: str
    description: str = ""
    scrape_type: str = "single"
    urls: List[str] = field(default_factory=list)
    config: Dict = field(default_factory=dict)
    transform_rules: List[Dict] = field(default_factory=list)
    export_formats: List[str] = field(default_factory=lambda: ["csv", "json"])
    is_public: bool = False
    run_count: int = 0
    last_used: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "scrape_type": self.scrape_type,
            "urls": self.urls,
            "config": self.config,
            "transform_rules": self.transform_rules,
            "export_formats": self.export_formats,
            "is_public": self.is_public,
            "run_count": self.run_count,
            "last_used": self.last_used,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TemplateManager:

    def __init__(self):
        self._templates: Dict[str, ScrapeTemplate] = {}

    def create(self, user_id: str, name: str, description: str = "",
               scrape_type: str = "single", urls: List[str] = None,
               config: Dict = None, transform_rules: List[Dict] = None,
               export_formats: List[str] = None, tags: List[str] = None,
               is_public: bool = False) -> ScrapeTemplate:
        now = datetime.now().isoformat()
        template = ScrapeTemplate(
            id=str(uuid.uuid4())[:8],
            user_id=user_id,
            name=name,
            description=description,
            scrape_type=scrape_type,
            urls=urls or [],
            config=config or {},
            transform_rules=transform_rules or [],
            export_formats=export_formats or ["csv", "json"],
            tags=tags or [],
            is_public=is_public,
            created_at=now,
            updated_at=now,
        )
        self._templates[template.id] = template
        return template

    def get(self, template_id: str) -> Optional[ScrapeTemplate]:
        return self._templates.get(template_id)

    def list_user(self, user_id: str) -> List[ScrapeTemplate]:
        return [t for t in self._templates.values() if t.user_id == user_id]

    def list_public(self) -> List[ScrapeTemplate]:
        return [t for t in self._templates.values() if t.is_public]

    def update(self, template_id: str, **kwargs) -> Optional[ScrapeTemplate]:
        template = self._templates.get(template_id)
        if not template:
            return None
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        template.updated_at = datetime.now().isoformat()
        return template

    def delete(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def record_usage(self, template_id: str) -> None:
        template = self._templates.get(template_id)
        if template:
            template.run_count += 1
            template.last_used = datetime.now().isoformat()

    def clone(self, template_id: str, new_name: str = None) -> Optional[ScrapeTemplate]:
        original = self._templates.get(template_id)
        if not original:
            return None
        now = datetime.now().isoformat()
        clone = ScrapeTemplate(
            id=str(uuid.uuid4())[:8],
            user_id=original.user_id,
            name=new_name or f"{original.name} (copy)",
            description=original.description,
            scrape_type=original.scrape_type,
            urls=list(original.urls),
            config=dict(original.config),
            transform_rules=list(original.transform_rules),
            export_formats=list(original.export_formats),
            tags=list(original.tags),
            created_at=now,
            updated_at=now,
        )
        self._templates[clone.id] = clone
        return clone

    def search(self, query: str, user_id: str = None) -> List[ScrapeTemplate]:
        query_lower = query.lower()
        results = []
        for t in self._templates.values():
            if user_id and t.user_id != user_id and not t.is_public:
                continue
            if (query_lower in t.name.lower() or
                query_lower in t.description.lower() or
                any(query_lower in tag.lower() for tag in t.tags)):
                results.append(t)
        return results

    def to_json(self, template_id: str) -> Optional[str]:
        template = self._templates.get(template_id)
        if template:
            return json.dumps(template.to_dict(), indent=2, default=str)
        return None

    def from_json(self, json_str: str, user_id: str) -> Optional[ScrapeTemplate]:
        try:
            data = json.loads(json_str)
            data["user_id"] = user_id
            data["id"] = str(uuid.uuid4())[:8]
            now = datetime.now().isoformat()
            data["created_at"] = now
            data["updated_at"] = now
            template = ScrapeTemplate(**data)
            self._templates[template.id] = template
            return template
        except Exception:
            return None

    def get_popular(self, limit: int = 10) -> List[ScrapeTemplate]:
        return sorted(self._templates.values(), key=lambda t: t.run_count, reverse=True)[:limit]

    def get_recent(self, limit: int = 10) -> List[ScrapeTemplate]:
        return sorted(self._templates.values(), key=lambda t: t.created_at, reverse=True)[:limit]

    def get_tags(self) -> List[Dict]:
        tag_counts = {}
        for t in self._templates.values():
            for tag in t.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return [{"tag": tag, "count": count} for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)]
