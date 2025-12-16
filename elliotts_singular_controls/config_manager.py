"""Configuration management for Elliott's Singular Controls."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from copy import deepcopy

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "version": "1.1.6",
    "modules": {
        "tfl": {
            "enabled": True,
            "name": "TfL Line Status",
            "description": "Live Transport for London line status updates"
        },
        "tricaster": {
            "enabled": True,
            "name": "TriCaster Control",
            "description": "DDR timer sync and control",
            "settings": {
                "host": "localhost",
                "port": 5951
            }
        },
        "cuez": {
            "enabled": True,
            "name": "Cuez Automator",
            "description": "Full rundown control and navigation",
            "settings": {
                "host": "localhost",
                "port": 7788
            }
        },
        "singular": {
            "enabled": True,
            "name": "Singular.live Control",
            "description": "Control app management and triggers",
            "settings": {
                "token": ""
            }
        },
        "casparcg": {
            "enabled": True,
            "name": "CasparCG Control",
            "description": "AMCP protocol graphics and media control",
            "settings": {
                "host": "localhost",
                "port": 5250
            }
        },
        "inews": {
            "enabled": True,
            "name": "iNews Cleaner",
            "description": "Remove formatting grommets from iNews content"
        }
    },
    "server": {
        "port": 3113,
        "host": "0.0.0.0"
    }
}


class ConfigManager:
    """Manages application configuration with persistence."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            config_path = Path("elliotts_singular_controls_config.json")

        self.config_path = config_path
        self.config = deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        """Load configuration from file, creating with defaults if not exists."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)

                # Merge loaded config with defaults (to handle new settings in updates)
                self.config = self._merge_configs(DEFAULT_CONFIG, loaded)
                logger.info(f"Configuration loaded from {self.config_path}")
            else:
                # Create new config file with defaults
                self.save()
                logger.info(f"Created new configuration at {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration")
            self.config = deepcopy(DEFAULT_CONFIG)

    def save(self) -> bool:
        """
        Save current configuration to file.

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def get(self, key: str = None) -> Any:
        """
        Get configuration value(s).

        Args:
            key: Dot-notation key (e.g., "modules.tfl.enabled"). If None, returns entire config.

        Returns:
            Configuration value or entire config dict
        """
        if key is None:
            return deepcopy(self.config)

        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return deepcopy(value)
        except (KeyError, TypeError):
            logger.warning(f"Configuration key not found: {key}")
            return None

    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """
        Set configuration value.

        Args:
            key: Dot-notation key (e.g., "modules.tfl.enabled")
            value: Value to set
            save: Whether to save to file immediately

        Returns:
            True if successful, False otherwise
        """
        try:
            keys = key.split('.')
            config = self.config

            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]

            # Set the value
            config[keys[-1]] = value

            if save:
                return self.save()
            return True
        except Exception as e:
            logger.error(f"Error setting configuration {key}={value}: {e}")
            return False

    def update(self, updates: Dict[str, Any], save: bool = True) -> bool:
        """
        Update multiple configuration values.

        Args:
            updates: Dict of key-value pairs to update
            save: Whether to save to file immediately

        Returns:
            True if successful, False otherwise
        """
        try:
            for key, value in updates.items():
                self.set(key, value, save=False)

            if save:
                return self.save()
            return True
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False

    def reset(self, save: bool = True) -> bool:
        """
        Reset configuration to defaults.

        Args:
            save: Whether to save to file immediately

        Returns:
            True if successful, False otherwise
        """
        self.config = deepcopy(DEFAULT_CONFIG)
        logger.info("Configuration reset to defaults")

        if save:
            return self.save()
        return True

    def is_module_enabled(self, module: str) -> bool:
        """
        Check if a module is enabled.

        Args:
            module: Module name (e.g., "tfl", "cuez")

        Returns:
            True if enabled, False otherwise
        """
        return self.get(f"modules.{module}.enabled") or False

    def get_module_settings(self, module: str) -> Dict[str, Any]:
        """
        Get settings for a specific module.

        Args:
            module: Module name

        Returns:
            Module settings dict, or empty dict if not found
        """
        settings = self.get(f"modules.{module}.settings")
        return settings if settings is not None else {}

    def _merge_configs(self, default: Dict, loaded: Dict) -> Dict:
        """
        Merge loaded config with defaults, preserving user values.

        Args:
            default: Default configuration
            loaded: Loaded configuration

        Returns:
            Merged configuration
        """
        merged = deepcopy(default)

        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged


# Global config instance
_config_manager = None


def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
