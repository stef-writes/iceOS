"""Extract structured intent and requirements from natural language.

This module provides utilities for parsing user specifications and extracting
key components like goals, constraints, inputs, and outputs.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


class IntentExtractor:
    """Extracts structured intent from natural language specifications."""
    
    # Keywords that indicate input sources
    INPUT_KEYWORDS = {
        "file", "csv", "json", "xml", "database", "api", "url", "path",
        "input", "source", "data", "from", "read", "load", "fetch"
    }
    
    # Keywords that indicate output/deliverables
    OUTPUT_KEYWORDS = {
        "output", "result", "report", "summary", "dashboard", "export",
        "save", "write", "generate", "create", "produce", "return"
    }
    
    # Keywords that indicate constraints
    CONSTRAINT_KEYWORDS = {
        "must", "should", "require", "ensure", "limit", "maximum", "minimum",
        "only", "exclude", "avoid", "within", "before", "after", "constraint"
    }
    
    # Common tool/service mentions
    TOOL_PATTERNS = {
        "openai": r"(?i)\b(openai|gpt|chatgpt)\b",
        "anthropic": r"(?i)\b(anthropic|claude)\b",
        "google": r"(?i)\b(google|gemini|bard)\b",
        "pandas": r"(?i)\b(pandas|dataframe)\b",
        "web": r"(?i)\b(web|scrape|crawl|browse)\b",
        "email": r"(?i)\b(email|smtp|send mail)\b",
        "database": r"(?i)\b(database|sql|postgres|mysql|sqlite)\b",
    }
    
    def extract(self, specification: str) -> Dict[str, Any]:
        """Extract structured intent from a specification.
        
        Args:
            specification: Natural language description.
            
        Returns:
            Dictionary containing:
            - goal: Primary objective
            - constraints: List of identified constraints
            - inputs: List of potential input sources
            - outputs: List of expected outputs
            - tools_mentioned: List of identified tools/services
        """
        # Normalize specification
        spec_lower = specification.lower()
        sentences = self._split_sentences(specification)
        
        return {
            "goal": self._extract_goal(sentences),
            "constraints": self._extract_constraints(sentences, spec_lower),
            "inputs": self._extract_inputs(sentences, spec_lower),
            "outputs": self._extract_outputs(sentences, spec_lower),
            "tools_mentioned": self._extract_tools(specification),
        }
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_goal(self, sentences: List[str]) -> str:
        """Extract the primary goal (usually the first sentence)."""
        if not sentences:
            return "Process data"
        
        # Look for action verbs in the first sentence
        goal = sentences[0]
        
        # If it starts with a question word, look for the next sentence
        if goal.lower().startswith(("how", "what", "when", "where", "why")):
            goal = sentences[1] if len(sentences) > 1 else goal
        
        return goal
    
    def _extract_constraints(self, sentences: List[str], spec_lower: str) -> List[str]:
        """Extract constraints from the specification."""
        constraints = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            # Check if sentence contains constraint keywords
            if any(keyword in sentence_lower for keyword in self.CONSTRAINT_KEYWORDS):
                constraints.append(sentence)
        
        return constraints
    
    def _extract_inputs(self, sentences: List[str], spec_lower: str) -> List[str]:
        """Extract potential input sources."""
        inputs = set()
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            words = sentence_lower.split()
            
            for i, word in enumerate(words):
                if word in self.INPUT_KEYWORDS:
                    # Try to get context (next word or phrase)
                    if i + 1 < len(words):
                        input_phrase = f"{word} {words[i + 1]}"
                        inputs.add(input_phrase)
                    else:
                        inputs.add(word)
        
        # Look for file paths or URLs
        paths = re.findall(r'[./][\w/.-]+', spec_lower)
        urls = re.findall(r'https?://[\w/.-]+', spec_lower)
        inputs.update(paths + urls)
        
        return list(inputs)
    
    def _extract_outputs(self, sentences: List[str], spec_lower: str) -> List[str]:
        """Extract expected outputs."""
        outputs = set()
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            words = sentence_lower.split()
            
            for i, word in enumerate(words):
                if word in self.OUTPUT_KEYWORDS:
                    # Try to get context
                    if i + 1 < len(words):
                        output_phrase = f"{word} {words[i + 1]}"
                        outputs.add(output_phrase)
                    else:
                        outputs.add(word)
        
        return list(outputs)
    
    def _extract_tools(self, specification: str) -> List[str]:
        """Extract mentioned tools or services."""
        tools = []
        
        for tool_name, pattern in self.TOOL_PATTERNS.items():
            if re.search(pattern, specification):
                tools.append(tool_name)
        
        return tools