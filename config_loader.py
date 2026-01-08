"""
Configuration Loader
Reads and validates YAML configuration files
"""

import yaml
from pathlib import Path


class ConfigLoader:
    """Loads and validates YAML configuration"""
    
    @staticmethod
    def load(config_path):
        """
        Load YAML config file and validate required fields
        
        Args:
            config_path: Path to YAML file
            
        Returns:
            dict: Parsed configuration
            
        Raises:
            ValueError: If required fields are missing
        """
        with open(config_path, 'r', encoding='utf-8-sig') as f:
            config = yaml.safe_load(f)
        
        # Validate required fields
        ConfigLoader._validate_config(config, config_path)
        
        return config
    
    @staticmethod
    def _validate_config(config, config_path):
        """
        Check that config has all required fields
        
        Required structure:
        - file: {path: "..."}
        - validations: [...]
        """
        if 'file' not in config:
            raise ValueError("Config missing 'file' section")
        
        if 'path' not in config['file']:
            raise ValueError("Config missing 'file.path'")


        config_folder = config_path.resolve().parent


        csv_path = config_folder / config['file']['path']
        if not csv_path.exists():
            raise ValueError(f"CSV file not found: {csv_path}")
        
        if 'validations' not in config:
            raise ValueError("Config missing 'validations' section")
        
        if not isinstance(config['validations'], list):
            raise ValueError("'validations' must be a list")
        
        if len(config['validations']) == 0:
            raise ValueError("At least one validation is required")
        
        # Validate each validation entry
        for i, validation in enumerate(config['validations']):
            ConfigLoader._validate_validation(validation, i)
    
    @staticmethod
    def _validate_validation(validation, index):
        """
        Validate a single validation entry
        
        Required fields:
        - name: Description of this validation
        - sql: SELECT query to execute
        - expect: Assertions to check
        """
        if 'name' not in validation:
            raise ValueError(f"Validation {index} missing 'name'")
        
        if 'sql' not in validation:
            raise ValueError(f"Validation {index} ({validation['name']}) missing 'sql'")
        
        if 'expect' not in validation:
            raise ValueError(f"Validation {index} ({validation['name']}) missing 'expect'")
        
        # Validate 'expect' section has at least one assertion
        expect = validation['expect']
        has_assertions = (
            'row_count' in expect or
            'columns' in expect or
            'not_null' in expect
        )
        
        if not has_assertions:
            raise ValueError(
                f"Validation {index} ({validation['name']}) has no assertions in 'expect'"
            )
