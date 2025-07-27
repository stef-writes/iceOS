"""Message Parser Tool - Parses and categorizes customer messages."""

from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import datetime
from ice_core.base_tool import ToolBase


class MessageParserTool(ToolBase):
    """Parses customer messages to extract intent, sentiment, and key information."""
    
    name: str = "message_parser"
    description: str = "Analyzes customer messages to extract intent, urgency, and key details"
    
    # Intent patterns
    INTENT_PATTERNS = {
        "price_inquiry": [
            r"how much", r"what.*price", r"cost\?", r"\$\?+", r"price\?",
            r"is it still.*\$", r"negotiable", r"best price", r"lower.*price",
            r"discount", r"offer", r"take \$\d+"
        ],
        "availability": [
            r"still available", r"is.*available", r"sold\?", r"do you still have",
            r"is it gone", r"when.*available", r"in stock", r"still.*sale"
        ],
        "condition_inquiry": [
            r"condition", r"any.*damage", r"works?\?", r"broken", r"defect",
            r"scratch", r"dent", r"perfect.*condition", r"like new", r"used"
        ],
        "pickup_logistics": [
            r"pick.*up", r"deliver", r"ship", r"meet", r"location", r"where",
            r"address", r"come.*get", r"available.*pickup", r"today", r"tomorrow"
        ],
        "feature_inquiry": [
            r"does it", r"can it", r"include", r"come with", r"what.*included",
            r"features", r"specs", r"specification", r"model", r"year", r"size"
        ],
        "purchase_intent": [
            r"i'll take it", r"want.*buy", r"interested", r"i'll buy", r"deal",
            r"sold.*me", r"want it", r"purchase", r"definitely.*want"
        ],
        "greeting": [
            r"^hi\b", r"^hello", r"^hey", r"good morning", r"good afternoon"
        ]
    }
    
    # Urgency indicators
    URGENCY_PATTERNS = {
        "high": [
            r"asap", r"urgent", r"today", r"right now", r"immediately",
            r"emergency", r"need.*now", r"hurry"
        ],
        "medium": [
            r"tomorrow", r"soon", r"this week", r"weekend", r"quickly"
        ],
        "low": [
            r"whenever", r"no rush", r"no hurry", r"when.*convenient"
        ]
    }
    
    # Sentiment indicators
    SENTIMENT_INDICATORS = {
        "positive": [
            "thanks", "thank you", "perfect", "great", "excellent", "awesome",
            "appreciate", "wonderful", "love", "excited", "😊", "😃", "👍"
        ],
        "negative": [
            "disappointed", "upset", "angry", "terrible", "horrible", "waste",
            "scam", "fraud", "rude", "unacceptable", "😠", "😡", "👎"
        ],
        "frustrated": [
            "still waiting", "no response", "been trying", "contacted before",
            "asked already", "told you", "said before"
        ]
    }
    
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Parse and analyze customer messages."""
        messages = kwargs.get("messages", [])
        
        if isinstance(messages, str):
            # Single message
            messages = [{"content": messages, "timestamp": datetime.now().isoformat()}]
        elif isinstance(messages, dict):
            # Single message dict
            messages = [messages]
        
        parsed_messages = []
        conversation_summary = self._analyze_conversation(messages)
        
        for message in messages:
            content = message.get("content", "")
            parsed = self._parse_single_message(content, message)
            parsed_messages.append(parsed)
        
        return {
            "parsed_messages": parsed_messages,
            "conversation_summary": conversation_summary,
            "requires_immediate_response": self._check_immediate_response_needed(parsed_messages),
            "suggested_response_type": self._suggest_response_type(parsed_messages)
        }
    
    def _parse_single_message(self, content: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single message."""
        content_lower = content.lower()
        
        # Extract basic info
        intents = self._extract_intents(content_lower)
        urgency = self._detect_urgency(content_lower)
        sentiment = self._analyze_sentiment(content_lower)
        entities = self._extract_entities(content)
        questions = self._extract_questions(content)
        
        # Detect special cases
        is_negotiation = self._is_negotiation(content_lower)
        has_contact_info = self._has_contact_info(content)
        
        return {
            "message_id": message_data.get("message_id", ""),
            "timestamp": message_data.get("timestamp", datetime.now().isoformat()),
            "content": content,
            "intents": intents,
            "primary_intent": intents[0] if intents else "general_inquiry",
            "urgency": urgency,
            "sentiment": sentiment,
            "entities": entities,
            "questions": questions,
            "is_negotiation": is_negotiation,
            "has_contact_info": has_contact_info,
            "word_count": len(content.split()),
            "requires_action": bool(intents or questions)
        }
    
    def _extract_intents(self, content: str) -> List[str]:
        """Extract message intents."""
        detected_intents = []
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected_intents.append(intent)
                    break
        
        return detected_intents or ["general_inquiry"]
    
    def _detect_urgency(self, content: str) -> str:
        """Detect message urgency level."""
        for level, patterns in self.URGENCY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return level
        
        # Check for multiple question marks or exclamation points
        if re.search(r'[!?]{2,}', content):
            return "medium"
            
        return "normal"
    
    def _analyze_sentiment(self, content: str) -> Dict[str, Any]:
        """Analyze message sentiment."""
        sentiment_scores = {"positive": 0, "negative": 0, "neutral": 0}
        
        # Check for sentiment indicators
        for sentiment, indicators in self.SENTIMENT_INDICATORS.items():
            for indicator in indicators:
                if indicator.lower() in content:
                    if sentiment == "frustrated":
                        sentiment_scores["negative"] += 1
                    else:
                        sentiment_scores[sentiment] += 1
        
        # Determine primary sentiment
        if sentiment_scores["positive"] > sentiment_scores["negative"]:
            primary = "positive"
        elif sentiment_scores["negative"] > sentiment_scores["positive"]:
            primary = "negative"
        else:
            primary = "neutral"
        
        # Calculate confidence
        total_indicators = sum(sentiment_scores.values())
        confidence = min(total_indicators * 0.2, 1.0) if total_indicators > 0 else 0.3
        
        return {
            "primary": primary,
            "scores": sentiment_scores,
            "confidence": confidence
        }
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract entities from message."""
        entities = {
            "prices": [],
            "times": [],
            "locations": [],
            "phone_numbers": [],
            "emails": []
        }
        
        # Extract prices
        price_matches = re.findall(r'\$\d+(?:\.\d{2})?|\d+\s*(?:dollars?|bucks?)', content)
        entities["prices"] = price_matches
        
        # Extract times
        time_patterns = [
            r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b',
            r'\b(?:today|tomorrow|tonight)\b',
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:morning|afternoon|evening)\b'
        ]
        for pattern in time_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            entities["times"].extend(matches)
        
        # Extract phone numbers
        phone_pattern = r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
        entities["phone_numbers"] = re.findall(phone_pattern, content)
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities["emails"] = re.findall(email_pattern, content)
        
        return entities
    
    def _extract_questions(self, content: str) -> List[str]:
        """Extract questions from the message."""
        # Split by sentence endings
        sentences = re.split(r'[.!?]+', content)
        questions = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            # Check if it's a question
            if sentence and (
                sentence.endswith('?') or 
                re.match(r'^(is|are|do|does|can|could|would|will|what|when|where|how|why)', sentence, re.IGNORECASE)
            ):
                questions.append(sentence)
        
        return questions
    
    def _is_negotiation(self, content: str) -> bool:
        """Check if message involves price negotiation."""
        negotiation_patterns = [
            r'take \$\d+', r'offer', r'best price', r'lower', r'discount',
            r'negotiable', r'willing to pay', r'cash', r'deal'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in negotiation_patterns)
    
    def _has_contact_info(self, content: str) -> bool:
        """Check if message contains contact information."""
        entities = self._extract_entities(content)
        return bool(entities["phone_numbers"] or entities["emails"])
    
    def _analyze_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze entire conversation thread."""
        if not messages:
            return {
                "message_count": 0,
                "conversation_stage": "initial",
                "buyer_engagement": "low"
            }
        
        # Determine conversation stage
        message_count = len(messages)
        has_price_discussion = any(
            self._is_negotiation(m.get("content", "").lower()) 
            for m in messages
        )
        has_logistics_discussion = any(
            "pickup_logistics" in self._extract_intents(m.get("content", "").lower())
            for m in messages
        )
        
        if has_logistics_discussion:
            stage = "closing"
        elif has_price_discussion:
            stage = "negotiation"
        elif message_count > 3:
            stage = "engaged"
        else:
            stage = "initial"
        
        # Determine engagement level
        avg_message_length = sum(len(m.get("content", "").split()) for m in messages) / max(message_count, 1)
        if avg_message_length > 20 or message_count > 5:
            engagement = "high"
        elif avg_message_length > 10 or message_count > 2:
            engagement = "medium"
        else:
            engagement = "low"
        
        return {
            "message_count": message_count,
            "conversation_stage": stage,
            "buyer_engagement": engagement,
            "has_price_discussion": has_price_discussion,
            "has_logistics_discussion": has_logistics_discussion
        }
    
    def _check_immediate_response_needed(self, parsed_messages: List[Dict[str, Any]]) -> bool:
        """Check if immediate response is needed."""
        if not parsed_messages:
            return False
        
        latest = parsed_messages[-1]
        
        # High urgency always needs immediate response
        if latest.get("urgency") == "high":
            return True
        
        # Purchase intent needs quick response
        if "purchase_intent" in latest.get("intents", []):
            return True
        
        # Negative sentiment might need attention
        if latest.get("sentiment", {}).get("primary") == "negative":
            return True
        
        return False
    
    def _suggest_response_type(self, parsed_messages: List[Dict[str, Any]]) -> str:
        """Suggest appropriate response type."""
        if not parsed_messages:
            return "greeting"
        
        latest = parsed_messages[-1]
        primary_intent = latest.get("primary_intent", "general_inquiry")
        
        response_map = {
            "price_inquiry": "price_response",
            "availability": "availability_confirmation",
            "condition_inquiry": "condition_details",
            "pickup_logistics": "logistics_coordination",
            "feature_inquiry": "product_details",
            "purchase_intent": "closing_sale",
            "greeting": "greeting_response"
        }
        
        return response_map.get(primary_intent, "general_response")
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool inputs."""
        return {
            "type": "object",
            "properties": {
                "messages": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "message_id": {"type": "string"},
                                    "content": {"type": "string"},
                                    "timestamp": {"type": "string"},
                                    "is_buyer": {"type": "boolean"},
                                    "conversation_id": {"type": "string"}
                                },
                                "required": ["content"]
                            }
                        }
                    ]
                }
            },
            "required": ["messages"]
        }
    
    @classmethod  
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool outputs."""
        return {
            "type": "object",
            "properties": {
                "parsed_messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "message_id": {"type": "string"},
                            "timestamp": {"type": "string"},
                            "content": {"type": "string"},
                            "intents": {"type": "array", "items": {"type": "string"}},
                            "primary_intent": {"type": "string"},
                            "urgency": {"type": "string"},
                            "sentiment": {"type": "object"},
                            "entities": {"type": "object"},
                            "questions": {"type": "array", "items": {"type": "string"}},
                            "is_negotiation": {"type": "boolean"},
                            "has_contact_info": {"type": "boolean"},
                            "word_count": {"type": "integer"},
                            "requires_action": {"type": "boolean"}
                        }
                    }
                },
                "conversation_summary": {
                    "type": "object",
                    "properties": {
                        "message_count": {"type": "integer"},
                        "conversation_stage": {"type": "string"},
                        "buyer_engagement": {"type": "string"},
                        "has_price_discussion": {"type": "boolean"},
                        "has_logistics_discussion": {"type": "boolean"}
                    }
                },
                "requires_immediate_response": {"type": "boolean"},
                "suggested_response_type": {"type": "string"}
            },
            "required": ["parsed_messages", "conversation_summary", "requires_immediate_response", "suggested_response_type"]
        } 