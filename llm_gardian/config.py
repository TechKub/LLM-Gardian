"""
Configuration management for the LLM-Gardian pipeline
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class DetectorConfig:
    """Configuration for prompt injection detection"""
    
    # Enable/disable detection strategies
    enable_heuristic_detection: bool = True
    enable_pattern_matching: bool = True
    enable_encoding_detection: bool = True
    
    # Thresholds
    suspicion_threshold: float = 0.6
    block_threshold: float = 0.8
    
    # Custom patterns to detect
    custom_patterns: List[str] = field(default_factory=list)
    
    # Whitelisted patterns (won't be flagged)
    whitelisted_patterns: List[str] = field(default_factory=list)
    
    # Maximum prompt length
    max_prompt_length: int = 10000
    
    # Verbose logging
    verbose: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "enable_heuristic_detection": self.enable_heuristic_detection,
            "enable_pattern_matching": self.enable_pattern_matching,
            "enable_encoding_detection": self.enable_encoding_detection,
            "suspicion_threshold": self.suspicion_threshold,
            "block_threshold": self.block_threshold,
            "custom_patterns": self.custom_patterns,
            "whitelisted_patterns": self.whitelisted_patterns,
            "max_prompt_length": self.max_prompt_length,
            "verbose": self.verbose,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "DetectorConfig":
        """Create config from dictionary"""
        return cls(**config_dict)
