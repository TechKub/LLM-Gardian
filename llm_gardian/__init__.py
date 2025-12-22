"""
LLM-Gardian: A pipeline to protect against Prompt Injection attacks
"""

from .detector import PromptInjectionDetector
from .pipeline import PromptInjectionPipeline
from .config import DetectorConfig

__version__ = "0.1.0"
__all__ = ["PromptInjectionDetector", "PromptInjectionPipeline", "DetectorConfig"]
