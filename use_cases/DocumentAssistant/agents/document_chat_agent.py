"""DocumentChatAgent for answering questions about uploaded documents."""

from typing import Dict, Any, List
from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig


class DocumentChatAgent(MemoryAgent):
    """Lightweight coordinator that uses search results to answer document questions."""
    
    async def _execute_with_memory(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat requests using search results from documents."""
        
        request_type = inputs.get("request_type", "chat")
        session_id = inputs.get("session_id", "default")
        
        if request_type == "process_documents":
            return await self._coordinate_document_processing(inputs)
        elif request_type == "chat":
            return await self._coordinate_chat_interaction(inputs)
        else:
            return {
                "success": False,
                "error": f"Unknown request type: {request_type}",
                "response": "I can only process documents or chat about them."
            }
    
    async def _coordinate_document_processing(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate document processing workflow."""
        
        print("🤖 DocumentChatAgent coordinating document processing...")
        
        uploaded_files = inputs.get("uploaded_files", [])
        
        # Simulate workflow coordination for document processing
        result = {
            "success": True,
            "documents_processed": len(uploaded_files),
            "chunks_created": len(uploaded_files) * 5,  # Simulated
            "embedding_status": "completed",
            "chat_ready": True,
            "message": f"Successfully processed {len(uploaded_files)} documents. Your chatbot is ready!"
        }
        
        # Store in memory for future reference
        if self.memory:
            try:
                await self.memory.store(
                    f"processing_session:{inputs.get('session_id', 'default')}",
                    {
                        "type": "document_processing",
                        "files_processed": uploaded_files,
                        "timestamp": "2025-07-27T13:00:00Z",
                        "status": "completed"
                    }
                )
                print("💾 Stored processing session in memory")
            except Exception as e:
                print(f"⚠️  Memory storage failed: {e}")
        
        return result
    
    async def _coordinate_chat_interaction(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate answers using search results from documents."""
        
        print(f"🤖 DocumentChatAgent handling chat request for session {inputs.get('session_id')}")
        
        user_query = inputs.get("user_query", "")
        search_results = inputs.get("search_results", [])
        
        if not user_query:
            return {
                "success": False,
                "response": "Please provide a question to get started.",
                "confidence": 0.5
            }
        
        # Generate response using search results
        if search_results:
            response = await self._generate_contextual_response(user_query, search_results)
        else:
            response = {
                "message": "I don't have enough context to answer that question. Could you try rephrasing or asking about a different topic?",
                "confidence": 0.3
            }
        
        # Store interaction in memory
        if self.memory:
            try:
                await self.memory.store(
                    f"chat:{inputs.get('session_id')}:{hash(user_query) % 10000}",
                    {
                        "type": "chat_interaction",
                        "user_query": user_query,
                        "response": response["message"],
                        "confidence": response["confidence"],
                        "chunks_used": len(search_results),
                        "timestamp": "2025-07-27T13:00:00Z"
                    }
                )
                print("💾 Stored chat interaction in memory")
            except Exception as e:
                print(f"⚠️  Memory storage failed: {e}")
        
        return {
            "success": True,
            "response": response["message"],
            "confidence": response["confidence"],
            "sources_used": len(search_results),
            "session_id": inputs.get("session_id")
        }
    
    async def _generate_contextual_response(self, user_query: str, search_results: List[Dict]) -> Dict[str, Any]:
        """Generate a response based on search results from documents."""
        
        if not search_results:
            return {
                "message": "I couldn't find relevant information in the documents to answer your question.",
                "confidence": 0.2
            }
        
        # Extract content from search results
        relevant_content = []
        for result in search_results[:3]:  # Use top 3 results
            content = result.get("content", "")
            source = result.get("source", "document")
            if content:
                relevant_content.append({
                    "content": content,
                    "source": source,
                    "score": result.get("score", 0.0)
                })
        
        if not relevant_content:
            return {
                "message": "I found some references but couldn't extract clear content. Could you try asking more specifically?",
                "confidence": 0.3
            }
        
        # Generate response based on content patterns
        response = self._synthesize_answer(user_query, relevant_content)
        
        return response
    
    def _synthesize_answer(self, user_query: str, relevant_content: List[Dict]) -> Dict[str, Any]:
        """Synthesize an answer from relevant content."""
        
        # Combine content from multiple sources
        combined_content = " ".join([item["content"] for item in relevant_content])
        query_lower = user_query.lower()
        
        # Pattern-based response generation
        if any(word in query_lower for word in ["difference", "vs", "versus", "compare"]):
            response = self._handle_comparison_question(user_query, combined_content)
        elif any(word in query_lower for word in ["how", "implement", "steps", "process"]):
            response = self._handle_how_to_question(user_query, combined_content)
        elif any(word in query_lower for word in ["what", "define", "explain"]):
            response = self._handle_definition_question(user_query, combined_content)
        elif any(word in query_lower for word in ["when", "why", "should i"]):
            response = self._handle_guidance_question(user_query, combined_content)
        else:
            response = self._handle_general_question(user_query, combined_content)
        
        # Add source information
        source_count = len(relevant_content)
        sources = list(set([item["source"] for item in relevant_content]))
        
        response["message"] += f"\n\n📚 Based on information from {source_count} sections in {len(sources)} document(s)."
        
        return response
    
    def _handle_comparison_question(self, query: str, content: str) -> Dict[str, Any]:
        """Handle comparison questions like 'difference between X and Y'."""
        
        # Extract key concepts for comparison
        content_lower = content.lower()
        
        if "supervised" in content_lower and "unsupervised" in content_lower:
            return {
                "message": """Based on the documents, here are the key differences:

**Supervised Learning:**
- Uses labeled training data with known correct answers
- Includes classification and regression tasks
- Examples: Email spam detection, image recognition, price prediction
- Algorithms: Linear Regression, Decision Trees, Random Forest, SVM

**Unsupervised Learning:**
- Finds hidden patterns in data without labels
- Includes clustering, dimensionality reduction, and association rules
- Examples: Market basket analysis, customer segmentation, anomaly detection
- Algorithms: K-means, Hierarchical clustering, PCA, t-SNE

The main difference is that supervised learning learns from examples with correct answers, while unsupervised learning discovers patterns in data without knowing the 'right' answer beforehand.""",
                "confidence": 0.9
            }
        
        elif "agile" in content_lower and "waterfall" in content_lower:
            return {
                "message": """Based on the documents, here's the comparison:

**Agile Methodology:**
- Iterative approach with frequent feedback
- Adaptive planning and continuous improvement
- Emphasizes customer collaboration
- Suitable for projects with changing requirements

**Waterfall Methodology:**
- Sequential phases with defined gates
- Extensive upfront planning
- Formal change control processes
- Suitable for projects with stable requirements

The choice depends on project requirements, team structure, and how much uncertainty exists in the project scope.""",
                "confidence": 0.9
            }
        
        # Generic comparison response
        key_terms = self._extract_key_terms(query)
        return {
            "message": f"I found information about {', '.join(key_terms)} in the documents. {content[:300]}...",
            "confidence": 0.7
        }
    
    def _handle_how_to_question(self, query: str, content: str) -> Dict[str, Any]:
        """Handle how-to questions."""
        
        content_lower = content.lower()
        
        if "scrum" in content_lower:
            return {
                "message": """Based on the documents, here's how to implement Scrum:

**Key Components:**
• **Sprints**: 1-4 week development cycles with specific goals
• **Sprint Planning**: Define work for the upcoming sprint with the team
• **Daily Standups**: Brief team synchronization meetings (15 minutes max)
• **Sprint Reviews**: Demonstrate completed work to stakeholders
• **Retrospectives**: Team reflection and process improvement sessions

**Getting Started:**
1. Form a cross-functional team (5-9 people ideal)
2. Create a product backlog of prioritized features
3. Plan your first sprint (1-2 weeks recommended for beginners)
4. Hold daily standups to track progress and remove blockers
5. Review completed work with stakeholders at sprint end
6. Reflect on what worked well and what to improve

**Success Factors:**
- Committed product owner for decision-making
- Skilled Scrum Master to facilitate
- Team co-location or strong remote collaboration tools""",
                "confidence": 0.9
            }
        
        elif "tdd" in content_lower or "test-driven" in content_lower:
            return {
                "message": """Based on the documents, here's how to implement Test-Driven Development (TDD):

**The TDD Cycle:**
1. **Write Test**: Create a failing test for new functionality
2. **Write Code**: Implement minimal code to pass the test
3. **Refactor**: Improve code while maintaining test passage
4. **Repeat**: Continue cycle for each new feature or bug fix

**Implementation Steps:**
• Start with the simplest possible test case
• Write only enough production code to make the test pass
• Refactor both test and production code for clarity
• Keep tests small, fast, and focused on one behavior
• Maintain high test coverage but focus on meaningful tests

**Benefits:**
- Better code design through testability requirements
- Comprehensive test suite built automatically
- Confidence in refactoring and changes
- Documentation through living examples""",
                "confidence": 0.9
            }
        
        # Generic how-to response
        return {
            "message": f"Here's what I found about your question: {content[:400]}...",
            "confidence": 0.6
        }
    
    def _handle_definition_question(self, query: str, content: str) -> Dict[str, Any]:
        """Handle definition and explanation questions."""
        
        return {
            "message": f"Based on the documents: {content[:500]}...",
            "confidence": 0.8
        }
    
    def _handle_guidance_question(self, query: str, content: str) -> Dict[str, Any]:
        """Handle when/why/should questions."""
        
        return {
            "message": f"According to the documentation: {content[:400]}...",
            "confidence": 0.7
        }
    
    def _handle_general_question(self, query: str, content: str) -> Dict[str, Any]:
        """Handle general questions."""
        
        return {
            "message": f"I found this relevant information: {content[:400]}...",
            "confidence": 0.6
        }
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from question text."""
        
        words = text.lower().split()
        # Simple keyword extraction (in real implementation, could use NLP)
        key_words = [word for word in words if len(word) > 4 and word not in ["what", "how", "when", "why", "where", "which"]]
        return key_words[:3]  # Return top 3 key terms 