"""
Mode Configuration Framework for RangerIO Testing

Defines test configurations for different query modes:
- Basic: No Assistant or Deep Search (fastest)
- Assistant: Smart features enabled (confidence, clarification, constraints)
- Deep Search: Thorough analysis (compound queries, validation, map-reduce)
- Both: All features enabled (most comprehensive)
"""
from dataclasses import dataclass
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModeConfig:
    """Configuration for a specific query mode."""
    name: str
    assistant_mode: bool
    deep_search_mode: bool
    expected_response_time: Tuple[int, int]  # (min_ms, max_ms)
    description: str
    
    def to_api_params(self) -> Dict[str, bool]:
        """Convert to API request parameters."""
        return {
            'assistant_mode': self.assistant_mode,
            'deep_search_mode': self.deep_search_mode,
        }
    
    def __str__(self) -> str:
        return f"{self.name} (Assistant={self.assistant_mode}, Deep={self.deep_search_mode})"


# Standard mode configurations
MODES = {
    'basic': ModeConfig(
        name='Basic',
        assistant_mode=False,
        deep_search_mode=False,
        expected_response_time=(1000, 3000),
        description='Fastest responses, no advanced features'
    ),
    'assistant': ModeConfig(
        name='Assistant',
        assistant_mode=True,
        deep_search_mode=False,
        expected_response_time=(2000, 5000),
        description='Smart features: confidence scoring, clarification, constraints'
    ),
    'deep': ModeConfig(
        name='Deep Search',
        assistant_mode=False,
        deep_search_mode=True,
        expected_response_time=(5000, 15000),
        description='Thorough analysis: compound queries, validation, map-reduce'
    ),
    'both': ModeConfig(
        name='Both',
        assistant_mode=True,
        deep_search_mode=True,
        expected_response_time=(5000, 20000),
        description='All features enabled for maximum accuracy'
    ),
}


def get_mode(mode_name: str) -> ModeConfig:
    """Get a mode configuration by name."""
    if mode_name not in MODES:
        raise ValueError(f"Unknown mode: {mode_name}. Available: {list(MODES.keys())}")
    return MODES[mode_name]


def get_all_modes() -> Dict[str, ModeConfig]:
    """Get all available mode configurations."""
    return MODES.copy()


def get_mode_names() -> list:
    """Get list of all mode names."""
    return list(MODES.keys())


class ModeValidator:
    """Validates query responses based on mode expectations."""
    
    def __init__(self, mode: ModeConfig):
        self.mode = mode
    
    def validate_response_time(self, response_time_ms: int) -> bool:
        """Check if response time is within expected range for this mode."""
        min_time, max_time = self.mode.expected_response_time
        return min_time <= response_time_ms <= max_time
    
    def validate_assistant_features(self, response: Dict[str, Any]) -> Dict[str, bool]:
        """Validate that Assistant mode features are present/absent as expected."""
        results = {}
        
        # Confidence scoring
        has_confidence = 'confidence' in response and response['confidence'] is not None
        results['confidence_present'] = has_confidence == self.mode.assistant_mode
        
        # Disambiguation
        has_disambiguation = 'disambiguation' in response and response['disambiguation'] is not None
        results['disambiguation_available'] = has_disambiguation
        
        # Hallucination check
        has_hallucination_check = 'hallucination_check' in response and response['hallucination_check'] is not None
        results['hallucination_check_present'] = has_hallucination_check == self.mode.assistant_mode
        
        # Constraints
        has_constraints = 'constraints' in response and response['constraints'] is not None
        results['constraints_available'] = has_constraints
        
        return results
    
    def validate_deep_search_features(self, response: Dict[str, Any]) -> Dict[str, bool]:
        """Validate that Deep Search mode features are present/absent as expected."""
        results = {}
        
        # Validation metadata
        has_validation = 'validation' in response and response['validation'] is not None
        results['validation_present'] = has_validation
        
        # Compound query handling
        metadata = response.get('metadata', {})
        has_compound_info = 'compound_query' in metadata
        results['compound_handling_available'] = has_compound_info
        
        # Map-reduce metadata
        has_mapreduce = 'map_reduce' in metadata or 'strategy' in metadata
        results['mapreduce_available'] = has_mapreduce
        
        return results
    
    def get_validation_summary(self, response: Dict[str, Any], response_time_ms: int) -> Dict[str, Any]:
        """Get complete validation summary for a response."""
        return {
            'mode': str(self.mode),
            'response_time_valid': self.validate_response_time(response_time_ms),
            'response_time_ms': response_time_ms,
            'expected_range': self.mode.expected_response_time,
            'assistant_features': self.validate_assistant_features(response) if self.mode.assistant_mode else None,
            'deep_search_features': self.validate_deep_search_features(response) if self.mode.deep_search_mode else None,
        }


def create_mode_comparison_table(results: Dict[str, Dict[str, Any]]) -> str:
    """
    Create a markdown comparison table for mode test results.
    
    Args:
        results: Dict mapping mode names to result dictionaries
        
    Returns:
        Markdown formatted table string
    """
    lines = []
    lines.append("| Mode | Avg Time (ms) | Accuracy | Features Active |")
    lines.append("|------|---------------|----------|-----------------|")
    
    for mode_name, result in results.items():
        mode = MODES[mode_name]
        avg_time = result.get('avg_response_time_ms', 'N/A')
        accuracy = result.get('accuracy_score', 'N/A')
        
        features = []
        if mode.assistant_mode:
            features.append('Assistant')
        if mode.deep_search_mode:
            features.append('Deep Search')
        if not features:
            features.append('None')
        
        features_str = ', '.join(features)
        lines.append(f"| {mode.name} | {avg_time} | {accuracy} | {features_str} |")
    
    return '\n'.join(lines)


# Export key classes and functions
__all__ = [
    'ModeConfig',
    'MODES',
    'get_mode',
    'get_all_modes',
    'get_mode_names',
    'ModeValidator',
    'create_mode_comparison_table',
]








