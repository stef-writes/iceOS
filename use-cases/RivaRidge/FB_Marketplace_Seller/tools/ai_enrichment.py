"""AI-powered product enrichment tool using real LLM calls."""

from typing import Dict, Any, List
from ice_sdk.tools.base import ToolBase
from ice_sdk.services.locator import ServiceLocator
from ice_core.models.llm import LLMConfig, ModelProvider


class AIEnrichmentTool(ToolBase):
    """Uses LLM to generate optimized titles and descriptions for marketplace items."""
    
    name: str = "ai_enrichment"
    description: str = "AI-powered product title and description optimization for marketplace listings"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        # Merge input_data with kwargs for flexibility
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(self, clean_items: List[Dict], model_name: str = "gpt-4o-mini", **kwargs) -> Dict[str, Any]:
        """Enrich products with AI-generated titles and descriptions."""
        
        if not clean_items:
            return {
                "success": True,
                "items_processed": 0,
                "llm_calls_made": 0,
                "enriched_items": []
            }
        
        # Get LLM service
        llm_service = ServiceLocator.get("llm_service")
        if not llm_service:
            # Fallback to rule-based enrichment
            return await self._fallback_enrichment(clean_items)
        
        enriched_items = []
        llm_calls_made = 0
        
        for item in clean_items:
            try:
                # Create optimized title and description
                enhanced_item = await self._enhance_item_with_llm(item, llm_service, model_name)
                enriched_items.append(enhanced_item)
                llm_calls_made += 1
                
            except Exception as e:
                print(f"⚠️  LLM enrichment failed for {item.get('sku', 'unknown')}: {e}")
                # Fallback to original item with basic enhancement
                enhanced_item = self._basic_enhancement(item)
                enriched_items.append(enhanced_item)
        
        return {
            "success": True,
            "items_processed": len(enriched_items),
            "llm_calls_made": llm_calls_made,
            "model_used": model_name,
            "enriched_items": enriched_items
        }
    
    async def _enhance_item_with_llm(self, item: Dict[str, Any], llm_service: Any, model_name: str) -> Dict[str, Any]:
        """Use LLM to enhance a single item."""
        
        # Create LLM configuration with multiple provider support
        if "claude" in model_name.lower():
            llm_config = LLMConfig(
                provider=ModelProvider.ANTHROPIC,
                model=model_name,  # e.g., "claude-3-haiku-20240307"
                temperature=0.7,
                max_tokens=500
            )
        elif "gemini" in model_name.lower():
            llm_config = LLMConfig(
                provider=ModelProvider.GOOGLE,
                model=model_name,  # e.g., "gemini-pro"
                temperature=0.7,
                max_tokens=500
            )
        elif "deepseek" in model_name.lower():
            llm_config = LLMConfig(
                provider=ModelProvider.DEEPSEEK,
                model=model_name,  # e.g., "deepseek-chat"
                temperature=0.7,
                max_tokens=500
            )
        else:
            # Default to OpenAI
            llm_config = LLMConfig(
                provider=ModelProvider.OPENAI,
                model=model_name,  # e.g., "gpt-4o-mini"
                temperature=0.7,
                max_tokens=500
            )
        
        # Create prompt for title and description optimization
        prompt = self._create_optimization_prompt(item)
        
        # Make LLM call
        text_response, usage, error = await llm_service.generate(
            llm_config=llm_config,
            prompt=prompt
        )
        
        if error:
            raise Exception(f"LLM call failed: {error}")
        
        # Parse LLM response
        enhanced_data = self._parse_llm_response(text_response)
        
        # Merge with original item
        enhanced_item = {**item}
        enhanced_item.update({
            "optimized_title": enhanced_data.get("title", item.get("name", "")),
            "optimized_description": enhanced_data.get("description", item.get("description", "")),
            "suggested_keywords": enhanced_data.get("keywords", []),
            "marketplace_category": enhanced_data.get("category", item.get("category", "")),
            "ai_enhanced": True,
            "llm_usage": usage
        })
        
        return enhanced_item
    
    def _create_optimization_prompt(self, item: Dict[str, Any]) -> str:
        """Create a prompt for optimizing item title and description."""
        
        return f"""
You are an expert Facebook Marketplace listing optimizer. Your job is to create compelling, SEO-optimized titles and descriptions that will attract buyers and rank well in search results.

ITEM TO OPTIMIZE:
- Name: {item.get('name', 'Unknown')}
- Current Description: {item.get('description', 'No description')}
- Brand: {item.get('brand', 'Unknown')}
- Category: {item.get('category', 'Unknown')}
- Condition: {item.get('condition', 'Used')}
- Price: ${item.get('price', 0):.2f}

GUIDELINES:
- Title should be 50-80 characters, include brand, key features, and condition
- Description should be 150-300 words, highlighting benefits and condition details
- Include relevant keywords for searchability
- Use engaging, trustworthy language that builds buyer confidence
- Mention any unique selling points or value propositions

Please respond in this exact JSON format:
{{
    "title": "optimized title here",
    "description": "optimized description here",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "category": "suggested category"
}}
"""
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response with fallback."""
        
        import json
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Fallback parsing
        lines = response.strip().split('\n')
        result = {
            "title": "",
            "description": "",
            "keywords": [],
            "category": ""
        }
        
        for line in lines:
            if "title" in line.lower():
                result["title"] = line.split(":", 1)[-1].strip().strip('"')
            elif "description" in line.lower():
                result["description"] = line.split(":", 1)[-1].strip().strip('"')
        
        return result
    
    async def _fallback_enrichment(self, items: List[Dict]) -> Dict[str, Any]:
        """Fallback enhancement without LLM."""
        
        enriched_items = []
        
        for item in items:
            enhanced_item = self._basic_enhancement(item)
            enriched_items.append(enhanced_item)
        
        return {
            "success": True,
            "items_processed": len(enriched_items),
            "llm_calls_made": 0,
            "enriched_items": enriched_items,
            "fallback_mode": True
        }
    
    def _basic_enhancement(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Basic rule-based enhancement."""
        
        name = item.get("name", "")
        brand = item.get("brand", "")
        condition = item.get("condition", "Used")
        
        # Create basic optimized title
        title_parts = []
        if brand:
            title_parts.append(brand)
        title_parts.append(name)
        if condition and condition.lower() != "used":
            title_parts.append(f"({condition})")
        
        optimized_title = " ".join(title_parts)[:75]
        
        # Create basic description
        description = item.get("description", "")
        if not description:
            description = f"Quality {name.lower()} in {condition.lower()} condition."
        
        enhanced_item = {**item}
        enhanced_item.update({
            "optimized_title": optimized_title,
            "optimized_description": description,
            "suggested_keywords": [name.lower(), brand.lower()] if brand else [name.lower()],
            "marketplace_category": item.get("category", "Other"),
            "ai_enhanced": False
        })
        
        return enhanced_item 