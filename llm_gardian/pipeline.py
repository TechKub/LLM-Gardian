"""
Pipeline for orchestrating prompt injection protection
"""

from typing import Optional, Callable, Dict, Any
from .detector import PromptInjectionDetector, DetectionResult
from .config import DetectorConfig


class PromptInjectionPipeline:
    """
    Pipeline to protect against prompt injection attacks
    
    This pipeline can be used to:
    1. Detect potential prompt injection attacks
    2. Block suspicious prompts
    3. Sanitize prompts (optional)
    4. Log security events
    """
    
    def __init__(
        self,
        config: Optional[DetectorConfig] = None,
        on_detection: Optional[Callable[[DetectionResult, str], None]] = None,
        on_block: Optional[Callable[[DetectionResult, str], None]] = None,
    ):
        """
        Initialize the pipeline
        
        Args:
            config: Configuration for the detector
            on_detection: Callback when injection is detected (result, prompt)
            on_block: Callback when prompt is blocked (result, prompt)
        """
        self.detector = PromptInjectionDetector(config or DetectorConfig())
        self.on_detection = on_detection
        self.on_block = on_block
        self.stats = {
            "total_prompts": 0,
            "detected_injections": 0,
            "blocked_prompts": 0,
        }
    
    def process(self, prompt: str, block_on_detection: bool = True) -> Dict[str, Any]:
        """
        Process a prompt through the pipeline
        
        Args:
            prompt: The prompt to process
            block_on_detection: Whether to block prompts that are detected as injections
            
        Returns:
            Dictionary with:
                - allowed: Whether the prompt is allowed to proceed
                - result: DetectionResult object
                - sanitized_prompt: The prompt (potentially sanitized)
        """
        self.stats["total_prompts"] += 1
        
        # Run detection
        result = self.detector.detect(prompt)
        
        # Track statistics
        if result.is_injection:
            self.stats["detected_injections"] += 1
            
            # Trigger detection callback
            if self.on_detection:
                self.on_detection(result, prompt)
        
        # Determine if prompt should be blocked
        allowed = True
        if block_on_detection and result.is_injection:
            allowed = False
            self.stats["blocked_prompts"] += 1
            
            # Trigger block callback
            if self.on_block:
                self.on_block(result, prompt)
        
        return {
            "allowed": allowed,
            "result": result,
            "sanitized_prompt": prompt,  # Could implement sanitization here
            "original_prompt": prompt,
        }
    
    def batch_process(self, prompts: list[str], block_on_detection: bool = True) -> list[Dict[str, Any]]:
        """
        Process multiple prompts in batch
        
        Args:
            prompts: List of prompts to process
            block_on_detection: Whether to block prompts that are detected as injections
            
        Returns:
            List of results for each prompt
        """
        return [self.process(prompt, block_on_detection) for prompt in prompts]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        stats = self.stats.copy()
        if stats["total_prompts"] > 0:
            stats["detection_rate"] = stats["detected_injections"] / stats["total_prompts"]
            stats["block_rate"] = stats["blocked_prompts"] / stats["total_prompts"]
        else:
            stats["detection_rate"] = 0.0
            stats["block_rate"] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset pipeline statistics"""
        self.stats = {
            "total_prompts": 0,
            "detected_injections": 0,
            "blocked_prompts": 0,
        }
    
    def validate_prompt(self, prompt: str) -> bool:
        """
        Quick validation of a prompt (returns True if safe, False if injection detected)
        
        Args:
            prompt: The prompt to validate
            
        Returns:
            True if prompt is safe, False otherwise
        """
        result = self.detector.detect(prompt)
        return not result.is_injection
