"""
Manifest Loader
Loads and validates test manifest files
"""

import yaml
from pathlib import Path


class ManifestLoader:
    """Loads test suite manifests"""
    
    @staticmethod
    def load(manifest_path):
        """
        Load and validate test manifest YAML
        
        Args:
            manifest_path: Path to manifest file
            
        Returns:
            dict: Parsed manifest
        """
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
        
        ManifestLoader._validate_manifest(manifest)
        
        return manifest
    
    @staticmethod
    def _validate_manifest(manifest):
        """
        Validate manifest structure
        
        Required:
        - suites: list of test suites
        
        Optional:
        - name: manifest name
        - database: connection settings
        - execution: runtime settings
        - reporting: output settings
        """
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be a YAML object/dictionary")
        
        if 'suites' not in manifest:
            raise ValueError("Manifest missing 'suites' section")
        
        if not isinstance(manifest['suites'], list):
            raise ValueError("'suites' must be a list")
        
        if len(manifest['suites']) == 0:
            raise ValueError("At least one suite must be defined")
        
        # Validate each suite
        for i, suite in enumerate(manifest['suites']):
            ManifestLoader._validate_suite(suite, i)
    
    @staticmethod
    def _validate_suite(suite, index):
        """
        Validate a single suite entry
        
        Required:
        - name: Suite name
        - config: Path to suite config YAML
        
        Optional:
        - enabled: true/false (default: true)
        - critical: true/false (default: false)
        - tags: list of tags
        """
        if not isinstance(suite, dict):
            raise ValueError(f"Suite {index} must be an object/dictionary")
        
        if 'name' not in suite:
            raise ValueError(f"Suite {index} missing 'name'")
        
        if 'config' not in suite:
            raise ValueError(f"Suite {index} ({suite['name']}) missing 'config' path")
        
        # Validate optional fields
        if 'enabled' in suite and not isinstance(suite['enabled'], bool):
            raise ValueError(f"Suite {index} ({suite['name']}) 'enabled' must be true/false")
        
        if 'critical' in suite and not isinstance(suite['critical'], bool):
            raise ValueError(f"Suite {index} ({suite['name']}) 'critical' must be true/false")
        
        if 'tags' in suite and not isinstance(suite['tags'], list):
            raise ValueError(f"Suite {index} ({suite['name']}) 'tags' must be a list")