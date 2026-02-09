"""Configuration management for Imago."""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = {
    "anthropic_api_key": "",
    "default_model": "claude-sonnet-4-20250514",
    "repos_dir": "~/local-coding/documentations",
    "index_path": "~/.imago/index.db",
    "cache_dir": "~/.imago/cache",
}


class Config:
    """Manages Imago configuration."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or Path.home() / ".imago" / "config.yaml"
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from file."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}

    def _save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, DEFAULT_CONFIG.get(key, default))

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._config[key] = value
        self._save()

    def delete(self, key: str) -> bool:
        """Delete a configuration value."""
        if key in self._config:
            del self._config[key]
            self._save()
            return True
        return False

    def all(self) -> dict[str, Any]:
        """Get all configuration values with defaults."""
        result = DEFAULT_CONFIG.copy()
        result.update(self._config)
        return result

    @property
    def repos_dir(self) -> Path:
        """Get the repositories directory path."""
        return Path(self.get("repos_dir")).expanduser()

    @property
    def index_path(self) -> Path:
        """Get the index database path."""
        return Path(self.get("index_path")).expanduser()

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory path."""
        return Path(self.get("cache_dir")).expanduser()

    @property
    def anthropic_api_key(self) -> str:
        """Get the Anthropic API key."""
        import os
        return self.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
