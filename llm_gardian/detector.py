"""
Prompt Injection Detection Module
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from .config import DetectorConfig


@dataclass
class DetectionResult:
    """Result of prompt injection detection"""
    
    is_injection: bool
    confidence_score: float
    detected_patterns: List[str]
    risk_level: str  # "low", "medium", "high", "critical"
    explanation: str
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            "is_injection": self.is_injection,
            "confidence_score": self.confidence_score,
            "detected_patterns": self.detected_patterns,
            "risk_level": self.risk_level,
            "explanation": self.explanation,
        }


class PromptInjectionDetector:
    """Detector for prompt injection attacks"""
    
    # Common prompt injection patterns
    INJECTION_PATTERNS = [
        # Direct instruction injection
        r"ignore\s+(all\s+)?(previous|above|prior|the|your)?\s*(instructions|directions|prompts?|rules?)",
        r"ignore\s+all\s+(instructions|directions|prompts?|rules?)",
        r"disregard\s+(all\s+)?(previous|above|prior|the|your)?\s*(instructions|directions|prompts?|rules?)",
        r"forget\s+(all\s+)?(previous|above|prior|the|your)?\s*(instructions|directions|prompts?|rules?)",
        r"ignore\s+the\s+(above|previous|prior)",
        
        # System prompt extraction attempts
        r"(show|reveal|display|print|output)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions)",
        r"what\s+(is|are)\s+your\s+(initial|original|system)\s+(prompt|instructions)",
        
        # Role manipulation
        r"you\s+are\s+now\s+(a|an)\s+\w+",
        r"act\s+as\s+(a|an)\s+\w+",
        r"pretend\s+(you\s+are|to\s+be)\s+",
        r"simulate\s+(a|an)\s+\w+",
        
        # Delimiter-based injections
        r"(\-{3,}|\={3,}|\*{3,})",
        r"<\|.*?\|>",
        r"\[SYSTEM\]|\[USER\]|\[ASSISTANT\]",
        
        # Encoding/obfuscation attempts
        r"\\x[0-9a-fA-F]{2}",
        r"&#\d+;",
        r"%[0-9a-fA-F]{2}",
        
        # Context switching
        r"new\s+conversation",
        r"reset\s+conversation",
        r"start\s+over",
        r"begin\s+new\s+(session|context)",
        
        # Output manipulation
        r"say\s+(exactly|only|just):",
        r"respond\s+with\s+(only|exactly|just):",
        r"output\s+(only|exactly|just):",
        
        # Jailbreak attempts
        r"\b(DAN|STAN)\b",
        r"developer\s+mode",
        r"jailbreak",
        r"sudo\s+mode",
        
        # Prompt leakage
        r"repeat\s+(your|the)\s+(instructions|prompt)",
        r"list\s+(your|the)\s+rules",
    ]
    
    def __init__(self, config: DetectorConfig = None):
        """Initialize the detector with optional configuration"""
        self.config = config or DetectorConfig()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        all_patterns = self.INJECTION_PATTERNS + self.config.custom_patterns
        self.compiled_patterns = [
            (pattern, re.compile(pattern, re.IGNORECASE))
            for pattern in all_patterns
        ]
        
        self.whitelisted_compiled = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.whitelisted_patterns
        ]
    
    def _check_whitelist(self, text: str) -> bool:
        """Check if text matches any whitelisted pattern"""
        for pattern in self.whitelisted_compiled:
            if pattern.search(text):
                return True
        return False
    
    def _pattern_matching_detection(self, text: str) -> Tuple[float, List[str]]:
        """Detect injection using pattern matching"""
        if not self.config.enable_pattern_matching:
            return 0.0, []
        
        detected = []
        for pattern_str, compiled_pattern in self.compiled_patterns:
            if compiled_pattern.search(text):
                detected.append(pattern_str)
        
        # Calculate score based on number of patterns matched
        if not detected:
            return 0.0, []
        
        # Higher base score for pattern matches since they're explicit indicators
        base_score = min(0.7 + (len(detected) * 0.15), 1.0)
        return base_score, detected
    
    def _heuristic_detection(self, text: str) -> Tuple[float, List[str]]:
        """Detect injection using heuristic analysis"""
        if not self.config.enable_heuristic_detection:
            return 0.0, []
        
        indicators = []
        score = 0.0
        
        # Check for excessive special characters
        special_chars = sum(1 for c in text if c in "{}[]()<>|\\")
        if len(text) > 0:
            special_ratio = special_chars / len(text)
            if special_ratio > 0.1:
                score += 0.2
                indicators.append("High special character density")
        
        # Check for multiple consecutive newlines (potential delimiter injection)
        if "\n\n\n" in text:
            score += 0.15
            indicators.append("Multiple consecutive newlines")
        
        # Check for unusual capitalization patterns
        if len(text) > 10:
            upper_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if upper_ratio > 0.5:
                score += 0.1
                indicators.append("Excessive capitalization")
        
        # Check for prompt-like structure
        if re.search(r"(Human:|AI:|Assistant:|User:|System:)", text, re.IGNORECASE):
            score += 0.3
            indicators.append("Contains role-like labels")
        
        # Check for multiple question marks or exclamation marks
        if re.search(r"[!?]{3,}", text):
            score += 0.1
            indicators.append("Excessive punctuation")
        
        # Check for script-like content
        if re.search(r"<script|javascript:|data:", text, re.IGNORECASE):
            score += 0.4
            indicators.append("Script-like content detected")
        
        return min(score, 1.0), indicators
    
    def _encoding_detection(self, text: str) -> Tuple[float, List[str]]:
        """Detect obfuscation through encoding"""
        if not self.config.enable_encoding_detection:
            return 0.0, []
        
        indicators = []
        score = 0.0
        
        # Check for hex encoding
        hex_matches = re.findall(r"\\x[0-9a-fA-F]{2}", text)
        if len(hex_matches) > 3:
            score += 0.3
            indicators.append("Hex encoding detected")
        
        # Check for HTML entities
        entity_matches = re.findall(r"&#\d+;", text)
        if len(entity_matches) > 3:
            score += 0.3
            indicators.append("HTML entities detected")
        
        # Check for URL encoding
        url_encoded = re.findall(r"%[0-9a-fA-F]{2}", text)
        if len(url_encoded) > 3:
            score += 0.3
            indicators.append("URL encoding detected")
        
        # Check for Base64-like patterns (consecutive alphanumeric with = padding)
        if re.search(r"[A-Za-z0-9+/]{20,}={0,2}", text):
            score += 0.2
            indicators.append("Potential Base64 encoding")
        
        return min(score, 1.0), indicators
    
    def detect(self, prompt: str) -> DetectionResult:
        """
        Detect prompt injection in the given text
        
        Args:
            prompt: The prompt text to analyze
            
        Returns:
            DetectionResult with detection findings
        """
        # Check prompt length
        if len(prompt) > self.config.max_prompt_length:
            return DetectionResult(
                is_injection=True,
                confidence_score=0.9,
                detected_patterns=["Excessive prompt length"],
                risk_level="high",
                explanation=f"Prompt exceeds maximum length ({self.config.max_prompt_length})"
            )
        
        # Check whitelist first
        if self._check_whitelist(prompt):
            return DetectionResult(
                is_injection=False,
                confidence_score=0.0,
                detected_patterns=[],
                risk_level="low",
                explanation="Prompt matched whitelisted pattern"
            )
        
        # Run all detection methods
        pattern_score, pattern_matches = self._pattern_matching_detection(prompt)
        heuristic_score, heuristic_indicators = self._heuristic_detection(prompt)
        encoding_score, encoding_indicators = self._encoding_detection(prompt)
        
        # Combine scores (use max for higher sensitivity with weighted contribution from others)
        # Pattern matching is given priority as it's the most reliable indicator
        if pattern_score > 0:
            # If pattern is matched, give it priority but cap at reasonable level
            combined_score = min(pattern_score + (heuristic_score * 0.15) + (encoding_score * 0.15), 1.0)
        else:
            # If no pattern match, use weighted average of heuristic and encoding
            combined_score = (heuristic_score * 0.6 + encoding_score * 0.4)
        
        # Combine all detected patterns
        all_detected = pattern_matches + heuristic_indicators + encoding_indicators
        
        # Determine risk level and if it's an injection
        is_injection = combined_score >= self.config.suspicion_threshold
        
        if combined_score >= self.config.block_threshold:
            risk_level = "critical"
            explanation = "High confidence prompt injection detected"
        elif combined_score >= self.config.suspicion_threshold:
            risk_level = "high"
            explanation = "Likely prompt injection detected"
        elif combined_score >= 0.4:
            risk_level = "medium"
            explanation = "Possible prompt injection detected"
        else:
            risk_level = "low"
            explanation = "No significant injection indicators found"
        
        return DetectionResult(
            is_injection=is_injection,
            confidence_score=combined_score,
            detected_patterns=all_detected,
            risk_level=risk_level,
            explanation=explanation
        )
