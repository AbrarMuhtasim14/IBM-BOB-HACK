"""
Query builder utilities for parsing natural language overload descriptions.
Extracts zone, skill, and other requirements from user input.
"""
import re
from typing import Dict, Optional, Tuple
import logging

from data.models import Zone, Shift

logger = logging.getLogger(__name__)


class QueryBuilder:
    """Builds structured queries from natural language input."""
    
    # Zone patterns
    ZONE_PATTERNS = {
        Zone.ZONE_A: [r'zone\s*a', r'receiving', r'zone\s*1'],
        Zone.ZONE_B: [r'zone\s*b', r'packing', r'zone\s*2'],
        Zone.ZONE_C: [r'zone\s*c', r'dispatch', r'shipping', r'zone\s*3'],
        Zone.ZONE_D: [r'zone\s*d', r'storage', r'warehouse', r'zone\s*4']
    }
    
    # Shift patterns
    SHIFT_PATTERNS = {
        Shift.MORNING: [r'morning', r'6\s*am', r'early'],
        Shift.AFTERNOON: [r'afternoon', r'2\s*pm', r'mid'],
        Shift.NIGHT: [r'night', r'10\s*pm', r'late', r'overnight']
    }
    
    # Common skill keywords
    SKILL_KEYWORDS = [
        'forklift', 'packing', 'quality', 'loading', 'inventory',
        'heavy equipment', 'order picker', 'shipping', 'coordinator',
        'inspector', 'operator', 'specialist', 'manager'
    ]
    
    def parse_overload_description(self, description: str) -> Dict[str, Optional[str]]:
        """
        Parse natural language overload description.
        
        Args:
            description: Natural language description
            
        Returns:
            Dictionary with extracted information
        """
        description_lower = description.lower()
        
        result = {
            'zone': None,
            'skill': None,
            'shift': None,
            'urgency': 'normal',
            'original_text': description
        }
        
        # Extract zone
        result['zone'] = self._extract_zone(description_lower)
        
        # Extract skill
        result['skill'] = self._extract_skill(description_lower)
        
        # Extract shift
        result['shift'] = self._extract_shift(description_lower)
        
        # Detect urgency
        if any(word in description_lower for word in ['urgent', 'emergency', 'critical', 'asap']):
            result['urgency'] = 'high'
        
        logger.info(f"Parsed query: {result}")
        return result
    
    def _extract_zone(self, text: str) -> Optional[str]:
        """Extract zone from text."""
        for zone, patterns in self.ZONE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return zone.value
        return None
    
    def _extract_skill(self, text: str) -> Optional[str]:
        """Extract skill requirement from text."""
        # Look for skill keywords
        found_skills = []
        for skill in self.SKILL_KEYWORDS:
            if skill in text:
                found_skills.append(skill)
        
        if found_skills:
            # Return the longest match (most specific)
            return max(found_skills, key=len)
        
        # Try to extract skill from common patterns
        patterns = [
            r'need\s+(\w+(?:\s+\w+)?)\s+(?:help|worker|operator)',
            r'(?:require|requires)\s+(\w+(?:\s+\w+)?)',
            r'(\w+(?:\s+\w+)?)\s+(?:is|are)\s+(?:needed|required)',
            r'looking\s+for\s+(\w+(?:\s+\w+)?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_shift(self, text: str) -> Optional[str]:
        """Extract shift timing from text."""
        for shift, patterns in self.SHIFT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return shift.value
        return None
    
    def build_search_filters(
        self,
        parsed_query: Dict[str, Optional[str]]
    ) -> Dict[str, any]:
        """
        Build search filters from parsed query.
        
        Args:
            parsed_query: Parsed query dictionary
            
        Returns:
            Dictionary of filters for retriever
        """
        filters = {
            'only_available': True
        }
        
        if parsed_query.get('zone'):
            # Exclude the overloaded zone
            try:
                filters['exclude_zone'] = Zone(parsed_query['zone'])
            except ValueError:
                pass
        
        if parsed_query.get('shift'):
            try:
                filters['required_shift'] = Shift(parsed_query['shift'])
            except ValueError:
                pass
        
        return filters
    
    def generate_search_query(self, parsed_query: Dict[str, Optional[str]]) -> str:
        """
        Generate a search query string from parsed information.
        
        Args:
            parsed_query: Parsed query dictionary
            
        Returns:
            Search query string
        """
        if parsed_query.get('skill'):
            return parsed_query['skill']
        
        # Fallback: use original text
        return parsed_query.get('original_text', 'worker')
    
    def validate_query(self, parsed_query: Dict[str, Optional[str]]) -> Tuple[bool, str]:
        """
        Validate that the parsed query has enough information.
        
        Args:
            parsed_query: Parsed query dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not parsed_query.get('zone'):
            return False, "Could not identify which zone is overloaded. Please specify the zone."
        
        if not parsed_query.get('skill'):
            return False, "Could not identify required skill. Please specify what type of worker is needed."
        
        return True, ""

# Made with Bob
