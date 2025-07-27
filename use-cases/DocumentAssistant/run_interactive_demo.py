"""DocumentAssistant Interactive Demo - Real Documents + User Questions

This creates realistic documents and tests the chat-in-a-box functionality
with prepared user questions that demonstrate RAG capabilities.
"""

import asyncio
import sys
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import iceOS SDK components
from ice_sdk.builders.workflow import WorkflowBuilder
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType

# Import our tools
from tools.document_parser import DocumentParserTool
from tools.intelligent_chunker import IntelligentChunkerTool
from tools.semantic_search import SemanticSearchTool

# Import agent
from agents.document_chat_agent import DocumentChatAgent


async def register_components():
    """Register tools and agents with iceOS registry."""
    
    print("🔧 Registering DocumentAssistant components...")
    
    # Register tools
    tools = [
        DocumentParserTool(),
        IntelligentChunkerTool(),
        SemanticSearchTool()
    ]
    
    for tool in tools:
        registry.register_instance(NodeType.TOOL, tool.name, tool)
        print(f"   ✅ Registered tool: {tool.name}")
    
    # Register agent
    from ice_core.unified_registry import global_agent_registry
    global_agent_registry.register_agent(
        "document_chat_agent",
        "use_cases.DocumentAssistant.agents.document_chat_agent"
    )
    print(f"   ✅ Registered agent: document_chat_agent")
    
    print("🔧 Component registration complete!")


async def create_realistic_documents():
    """Create substantial, realistic documents for testing."""
    data_dir = Path("docs")
    data_dir.mkdir(exist_ok=True)
    
    # Document 1: Comprehensive AI/ML Guide
    ai_guide = """# Complete Guide to Artificial Intelligence and Machine Learning

## Introduction to AI

Artificial Intelligence (AI) represents one of the most transformative technologies of our time. At its core, AI is the simulation of human intelligence in machines that are programmed to think and learn like humans. The field encompasses various approaches, from rule-based systems to advanced neural networks.

## Core Machine Learning Concepts

### Supervised Learning
Supervised learning is the most common type of machine learning. In this approach:
- Models learn from labeled training data
- Examples include classification and regression tasks
- Common algorithms: Linear Regression, Decision Trees, Random Forest, SVM
- Use cases: Email spam detection, image recognition, price prediction

### Unsupervised Learning  
Unsupervised learning finds hidden patterns in data without labels:
- Clustering: Groups similar data points (K-means, Hierarchical clustering)
- Dimensionality Reduction: PCA, t-SNE for data visualization
- Association Rules: Market basket analysis, recommendation systems
- Anomaly Detection: Fraud detection, network security

### Reinforcement Learning
Reinforcement learning involves agents learning through trial and error:
- Agent takes actions in an environment
- Receives rewards or penalties for actions
- Goal is to maximize cumulative reward
- Applications: Game playing (AlphaGo), robotics, autonomous vehicles

## Deep Learning Revolution

Deep learning, a subset of machine learning, uses neural networks with multiple layers:

### Neural Network Fundamentals
- Neurons (nodes) connected in layers
- Input layer → Hidden layers → Output layer
- Activation functions: ReLU, Sigmoid, Tanh
- Backpropagation for training

### Popular Architectures
1. **Convolutional Neural Networks (CNNs)**: Image processing, computer vision
2. **Recurrent Neural Networks (RNNs)**: Sequential data, time series
3. **Long Short-Term Memory (LSTM)**: Advanced sequence modeling
4. **Transformers**: Natural language processing, GPT models

## Natural Language Processing (NLP)

NLP enables machines to understand and process human language:

### Key Techniques
- Tokenization: Breaking text into words/tokens
- Part-of-speech tagging: Identifying word types
- Named Entity Recognition: Finding people, places, organizations
- Sentiment Analysis: Determining emotional tone

### Modern NLP Applications
- Chatbots and virtual assistants
- Language translation services
- Document summarization
- Question-answering systems
- Text generation and completion

## Computer Vision Applications

Computer vision allows machines to interpret visual information:
- Object Detection: Identifying and locating objects in images
- Image Classification: Categorizing images into predefined classes
- Facial Recognition: Identifying individuals from facial features
- Medical Imaging: Analyzing X-rays, MRIs for diagnosis
- Autonomous Vehicles: Real-time environment understanding

## AI in Industry

### Healthcare
- Drug discovery and development
- Medical diagnosis assistance
- Personalized treatment plans
- Robotic surgery assistance

### Finance
- Algorithmic trading
- Fraud detection systems
- Credit scoring and risk assessment
- Robo-advisors for investment

### Technology
- Search engines and recommendation systems
- Voice assistants (Siri, Alexa)
- Predictive text and auto-complete
- Content moderation on social platforms

## Challenges and Considerations

### Technical Challenges
- Data quality and availability
- Model interpretability and explainability
- Computational resource requirements
- Overfitting and generalization

### Ethical Considerations
- Bias in AI systems
- Privacy and data protection
- Job displacement concerns
- Autonomous decision-making accountability

## Future Trends

- Artificial General Intelligence (AGI) research
- Edge AI and mobile deployment
- Federated learning for privacy
- AI-human collaboration interfaces
- Quantum machine learning possibilities

The field of AI continues to evolve rapidly, with new breakthroughs constantly pushing the boundaries of what's possible. Understanding these fundamentals provides a solid foundation for exploring specific applications and staying current with developments.
"""

    # Document 2: Complete Project Management Guide  
    pm_guide = """# Comprehensive Project Management Guide

## Introduction to Project Management

Project management is the practice of initiating, planning, executing, controlling, and closing the work of a team to achieve specific goals and meet specific success criteria at the specified time. A project is a temporary endeavor designed to produce a unique product, service, or result with a defined beginning and end.

## Project Management Lifecycle

### 1. Project Initiation
The initiation phase is where the project is formally authorized:

**Key Activities:**
- Define project charter and business case
- Identify stakeholders and their expectations
- Conduct feasibility studies
- Establish project goals and objectives
- Define high-level scope and deliverables

**Deliverables:**
- Project charter document
- Stakeholder register
- Initial risk assessment
- High-level budget estimate

### 2. Project Planning
Planning is crucial for project success and involves detailed preparation:

**Core Planning Areas:**
- **Scope Management**: Work Breakdown Structure (WBS), scope statement
- **Time Management**: Activity sequencing, duration estimation, critical path
- **Cost Management**: Budget development, cost baseline
- **Quality Management**: Quality standards, testing procedures
- **Human Resources**: Team organization, roles and responsibilities
- **Communications**: Communication plan, reporting structure
- **Risk Management**: Risk identification, assessment, response planning
- **Procurement**: Make-or-buy decisions, vendor selection

**Key Tools:**
- Gantt charts for timeline visualization
- Network diagrams for dependency mapping
- Risk matrices for probability and impact assessment
- Resource allocation charts

### 3. Project Execution
The execution phase involves coordinating people and resources:

**Management Activities:**
- Direct and manage project work
- Perform quality assurance
- Acquire and develop project team
- Manage stakeholder engagement
- Conduct procurement activities

**Monitoring Activities:**
- Track progress against baseline
- Identify and resolve issues
- Manage changes to scope, schedule, or budget
- Ensure deliverable quality

### 4. Project Monitoring and Controlling
This phase involves tracking, reviewing, and regulating progress:

**Key Processes:**
- Monitor project work and performance
- Perform integrated change control
- Validate and control scope
- Control schedule and costs
- Monitor risks and stakeholder engagement

**Performance Metrics:**
- Schedule Performance Index (SPI)
- Cost Performance Index (CPI)
- Earned Value Management (EVM)
- Quality metrics and defect rates

### 5. Project Closure
Formal closure ensures proper project completion:

**Closure Activities:**
- Finalize all project activities
- Hand over deliverables to operations
- Release project resources
- Document lessons learned
- Celebrate team achievements

## Project Management Methodologies

### Traditional/Waterfall Approach
- Sequential phases with defined gates
- Extensive upfront planning
- Formal change control processes
- Suitable for projects with stable requirements

### Agile Methodology
- Iterative and incremental approach
- Frequent customer collaboration
- Adaptive planning and continuous improvement
- Popular frameworks: Scrum, Kanban, SAFe

**Scrum Framework:**
- **Sprints**: 1-4 week development cycles
- **Sprint Planning**: Defining work for upcoming sprint
- **Daily Standups**: Brief team synchronization meetings
- **Sprint Reviews**: Demonstrating completed work to stakeholders
- **Retrospectives**: Team reflection and process improvement

### Lean Project Management
- Focus on value delivery and waste elimination
- Continuous improvement (Kaizen)
- Just-in-time planning
- Visual management with Kanban boards

### Hybrid Approaches
- Combine traditional and agile methods
- Adapt methodology to project characteristics
- Predictive planning with adaptive execution

## Essential Project Management Skills

### Leadership Skills
- Team motivation and inspiration
- Conflict resolution and negotiation
- Decision-making under uncertainty
- Change management and adaptation

### Technical Skills
- Project management software proficiency
- Data analysis and reporting
- Risk assessment techniques
- Quality management tools

### Communication Skills
- Stakeholder management
- Status reporting and presentations
- Meeting facilitation
- Cross-cultural communication

## Common Project Challenges

### Scope Creep
- Uncontrolled expansion of project scope
- Impact on timeline and budget
- Mitigation: Clear requirements, change control process

### Resource Constraints
- Limited availability of skilled team members
- Budget limitations and cost overruns
- Solutions: Resource leveling, outsourcing, training

### Stakeholder Management
- Conflicting stakeholder expectations
- Communication breakdowns
- Resistance to change
- Approach: Regular engagement, transparent communication

### Risk Management
- Unforeseen technical challenges
- External dependencies and suppliers
- Market or regulatory changes
- Strategy: Proactive identification, contingency planning

## Project Success Factors

### Critical Success Elements
1. **Clear Project Definition**: Well-defined objectives and scope
2. **Strong Leadership**: Committed project sponsor and capable PM
3. **Stakeholder Buy-in**: Support from all key stakeholders
4. **Realistic Planning**: Achievable timelines and budgets
5. **Effective Communication**: Regular, transparent information sharing
6. **Quality Focus**: Emphasis on deliverable quality throughout
7. **Risk Management**: Proactive identification and mitigation
8. **Team Competence**: Skilled and motivated team members

### Measuring Success
- **Traditional Metrics**: On time, on budget, meeting specifications
- **Modern Metrics**: Business value delivered, stakeholder satisfaction
- **Long-term Impact**: Organizational learning, capability building

## Tools and Software

### Project Management Software
- Microsoft Project: Comprehensive planning and tracking
- Asana: Team collaboration and task management
- Jira: Agile project management and issue tracking
- Trello: Simple Kanban-style project boards
- Monday.com: Visual project workflows

### Collaboration Tools
- Slack: Team communication and integration
- Microsoft Teams: Video conferencing and file sharing
- Confluence: Documentation and knowledge sharing
- Google Workspace: Real-time document collaboration

## Career Development

### Project Management Certifications
- **PMP (Project Management Professional)**: Global standard certification
- **PRINCE2**: Structured project management methodology
- **Agile/Scrum Certifications**: CSM, PSM, SAFe certifications
- **Industry-Specific**: AIPM, APM, CompTIA Project+

### Career Progression
- Project Coordinator → Project Manager → Senior PM → Program Manager → Portfolio Manager
- Specialization opportunities in specific industries or methodologies
- Transition to executive roles: PMO Director, VP of Operations

Project management continues to evolve with technological advances and changing business needs. Successful project managers adapt their approaches while maintaining focus on delivering value to stakeholders and achieving project objectives.
"""

    # Document 3: Software Development Best Practices
    dev_guide = """# Software Development Best Practices and Methodologies

## Introduction to Software Development

Software development is the process of conceiving, specifying, designing, programming, documenting, testing, and bug fixing involved in creating and maintaining applications, frameworks, or other software components. Modern software development has evolved from simple programming to complex engineering disciplines involving multiple stakeholders and sophisticated processes.

## Software Development Lifecycle (SDLC)

### Planning and Requirements Analysis
- **Requirements Gathering**: Understanding stakeholder needs and business objectives
- **Feasibility Study**: Technical, operational, and economic viability assessment
- **Project Planning**: Timeline, resource allocation, and milestone definition
- **Technology Stack Selection**: Choosing appropriate programming languages, frameworks, and tools

### System Design and Architecture
- **High-Level Design**: System architecture, component interaction diagrams
- **Low-Level Design**: Detailed module specifications, data structures, algorithms
- **Database Design**: Entity-relationship diagrams, normalization, indexing strategies
- **API Design**: RESTful services, GraphQL, microservices architecture

### Implementation and Coding
- **Coding Standards**: Consistent formatting, naming conventions, documentation
- **Version Control**: Git workflows, branching strategies, code reviews
- **Development Environment**: IDE configuration, local development setup
- **Code Organization**: Modular design, separation of concerns, design patterns

### Testing and Quality Assurance
- **Unit Testing**: Individual component testing, test-driven development (TDD)
- **Integration Testing**: Component interaction testing, API testing
- **System Testing**: End-to-end functionality, performance, security testing
- **User Acceptance Testing**: Stakeholder validation, usability testing

### Deployment and Maintenance
- **Continuous Integration/Continuous Deployment (CI/CD)**: Automated build, test, and deployment pipelines
- **Environment Management**: Development, staging, and production environments
- **Monitoring and Logging**: Application performance monitoring, error tracking
- **Maintenance and Updates**: Bug fixes, feature enhancements, security patches

## Development Methodologies

### Agile Development
Agile emphasizes iterative development, customer collaboration, and adaptability:

**Core Principles:**
- Individuals and interactions over processes and tools
- Working software over comprehensive documentation
- Customer collaboration over contract negotiation
- Responding to change over following a plan

**Scrum Framework:**
- **Sprints**: 1-4 week development cycles
- **Sprint Planning**: Defining work for upcoming sprint
- **Daily Standups**: Brief team synchronization meetings
- **Sprint Reviews**: Demonstrating completed work to stakeholders
- **Retrospectives**: Team reflection and process improvement

**Kanban Method:**
- Visual workflow management with boards and cards
- Work-in-progress (WIP) limits to improve flow
- Continuous delivery without fixed iterations
- Focus on bottleneck identification and elimination

### DevOps Culture
DevOps bridges development and operations teams for faster, more reliable software delivery:

**Key Practices:**
- **Infrastructure as Code**: Version-controlled infrastructure provisioning
- **Automated Testing**: Continuous testing throughout the pipeline
- **Monitoring and Observability**: Real-time system health tracking
- **Collaboration**: Shared responsibility for entire application lifecycle

**Essential Tools:**
- **Version Control**: Git, GitLab, GitHub
- **CI/CD Platforms**: Jenkins, GitLab CI, GitHub Actions, Azure DevOps
- **Containerization**: Docker, Kubernetes, container orchestration
- **Cloud Platforms**: AWS, Azure, Google Cloud Platform
- **Monitoring**: Prometheus, Grafana, ELK Stack, New Relic

## Code Quality and Best Practices

### Clean Code Principles
- **Meaningful Names**: Use intention-revealing, searchable names
- **Small Functions**: Single responsibility, minimal parameters
- **Comments**: Explain why, not what; keep comments current
- **Formatting**: Consistent indentation, line length, organization
- **Error Handling**: Proper exception handling, meaningful error messages

### Design Patterns
- **Creational Patterns**: Singleton, Factory, Builder
- **Structural Patterns**: Adapter, Decorator, Facade
- **Behavioral Patterns**: Observer, Strategy, Command
- **Architectural Patterns**: MVC, MVP, MVVM, Microservices

### Code Review Best Practices
- **Regular Reviews**: All code changes reviewed before merging
- **Constructive Feedback**: Focus on code improvement, not personal criticism
- **Automated Checks**: Linting, security scanning, test coverage
- **Knowledge Sharing**: Distribute domain knowledge across team members

## Testing Strategies

### Test Pyramid
- **Unit Tests**: Fast, isolated tests for individual components (70%)
- **Integration Tests**: API and service interaction testing (20%)
- **End-to-End Tests**: Complete user workflow testing (10%)

### Testing Types
- **Functional Testing**: Verifying features work as specified
- **Performance Testing**: Load, stress, and scalability testing
- **Security Testing**: Vulnerability assessment, penetration testing
- **Accessibility Testing**: WCAG compliance, screen reader compatibility
- **Compatibility Testing**: Cross-browser, cross-platform validation

### Test-Driven Development (TDD)
1. **Write Test**: Create failing test for new functionality
2. **Write Code**: Implement minimal code to pass the test
3. **Refactor**: Improve code while maintaining test passage
4. **Repeat**: Continue cycle for each new feature or bug fix

## Modern Development Practices

### Microservices Architecture
- **Service Independence**: Loosely coupled, independently deployable services
- **Technology Diversity**: Different services can use different technology stacks
- **Scalability**: Scale individual services based on demand
- **Fault Isolation**: Service failures don't cascade to entire system

### API-First Development
- **Design First**: Define APIs before implementation
- **Documentation**: Comprehensive API documentation (OpenAPI/Swagger)
- **Versioning**: Backward-compatible API evolution
- **Testing**: Automated API testing and contract testing

### Progressive Web Applications (PWAs)
- **Service Workers**: Offline functionality and background sync
- **Responsive Design**: Mobile-first, adaptive layouts
- **App-like Experience**: Push notifications, home screen installation
- **Performance**: Fast loading, smooth interactions

## Security Best Practices

### Secure Coding Practices
- **Input Validation**: Sanitize and validate all user inputs
- **Authentication**: Strong password policies, multi-factor authentication
- **Authorization**: Role-based access control, least privilege principle
- **Data Protection**: Encryption at rest and in transit
- **SQL Injection Prevention**: Parameterized queries, ORM usage

### Security Testing
- **Static Analysis**: Code scanning for security vulnerabilities
- **Dynamic Analysis**: Runtime security testing
- **Dependency Scanning**: Third-party library vulnerability assessment
- **Penetration Testing**: Simulated attacks on applications

## Performance Optimization

### Frontend Optimization
- **Code Splitting**: Load only necessary JavaScript
- **Image Optimization**: Responsive images, modern formats (WebP)
- **Caching Strategies**: Browser caching, CDN usage
- **Minification**: Compress CSS, JavaScript, and HTML

### Backend Optimization
- **Database Optimization**: Query optimization, indexing, connection pooling
- **Caching**: Redis, Memcached for frequently accessed data
- **Load Balancing**: Distribute traffic across multiple servers
- **Asynchronous Processing**: Background jobs, message queues

## Emerging Trends

### Artificial Intelligence and Machine Learning
- **AI-Assisted Development**: Code completion, bug detection, automated testing
- **ML Integration**: Recommendation systems, predictive analytics
- **Natural Language Processing**: Chatbots, sentiment analysis
- **Computer Vision**: Image recognition, document processing

### Low-Code/No-Code Platforms
- **Rapid Prototyping**: Quick application development
- **Business User Empowerment**: Non-technical users building applications
- **Integration Challenges**: Connecting with existing systems
- **Customization Limitations**: Balancing ease-of-use with flexibility

### Blockchain and Web3
- **Decentralized Applications (DApps)**: Blockchain-based applications
- **Smart Contracts**: Self-executing contracts with predefined rules
- **Cryptocurrency Integration**: Payment systems, tokenization
- **Identity Management**: Decentralized identity verification

The software development landscape continues to evolve rapidly, with new tools, frameworks, and methodologies emerging regularly. Successful developers stay current with industry trends while maintaining focus on fundamental principles of quality, maintainability, and user value.
"""

    # Write documents to files
    docs = [
        ("ai_ml_guide.md", ai_guide),
        ("project_management_guide.md", pm_guide), 
        ("software_development_guide.md", dev_guide)
    ]
    
    file_paths = []
    for filename, content in docs:
        doc_path = data_dir / filename
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        file_paths.append(str(doc_path))
        print(f"📄 Created: {filename} ({len(content):,} chars)")
    
    return file_paths


async def test_user_questions(search_tool, agent):
    """Test the chat functionality with realistic user questions."""
    
    # Realistic user questions that test different aspects
    test_questions = [
        {
            "question": "What's the difference between supervised and unsupervised learning?",
            "expected_topics": ["supervised learning", "unsupervised learning", "labeled data"],
            "category": "AI/ML Concepts"
        },
        {
            "question": "How do I implement Scrum methodology in my project?",
            "expected_topics": ["scrum", "sprints", "daily standups", "retrospectives"],
            "category": "Project Management"
        },
        {
            "question": "What are the key principles of clean code?",
            "expected_topics": ["clean code", "meaningful names", "small functions"],
            "category": "Software Development"
        },
        {
            "question": "How should I handle project scope creep?",
            "expected_topics": ["scope creep", "change control", "requirements"],
            "category": "Project Management"
        },
        {
            "question": "What is test-driven development and how do I implement it?",
            "expected_topics": ["TDD", "test-driven development", "unit tests"],
            "category": "Software Development"
        },
        {
            "question": "Explain the transformer architecture in deep learning",
            "expected_topics": ["transformers", "neural networks", "NLP"],
            "category": "AI/ML Advanced"
        },
        {
            "question": "What are microservices and when should I use them?",
            "expected_topics": ["microservices", "architecture", "scalability"],
            "category": "Software Architecture"
        },
        {
            "question": "How do I measure project success beyond time and budget?",
            "expected_topics": ["project success", "metrics", "business value"],
            "category": "Project Management"
        }
    ]
    
    print("\n🎯 === TESTING CHAT FUNCTIONALITY ===")
    print(f"Testing {len(test_questions)} realistic user questions...")
    
    results = []
    
    for i, test_case in enumerate(test_questions, 1):
        question = test_case["question"]
        category = test_case["category"]
        expected_topics = test_case["expected_topics"]
        
        print(f"\n📝 Question {i}/{len(test_questions)} ({category}):")
        print(f"❓ User: {question}")
        
        # Search for relevant content
        search_result = await search_tool.execute(
            query=question,
            limit=3,
            similarity_threshold=0.6
        )
        
        found_chunks = search_result.get('results', [])
        print(f"🔍 Found {len(found_chunks)} relevant chunks")
        
        # Simulate agent response
        agent_input = {
            "request_type": "chat",
            "user_query": question,
            "search_results": found_chunks,
            "session_id": "interactive_demo"
        }
        
        try:
            agent_result = await agent.execute(agent_input)
            response = agent_result.get('response', 'No response generated')
            confidence = agent_result.get('confidence', 0.0)
            
            print(f"🤖 Agent: {response[:200]}...")
            print(f"📊 Confidence: {confidence:.2f}")
            
            # Analyze coverage of expected topics
            response_lower = response.lower()
            covered_topics = [topic for topic in expected_topics if topic.lower() in response_lower]
            coverage = len(covered_topics) / len(expected_topics)
            
            print(f"✅ Topic coverage: {coverage:.1%} ({len(covered_topics)}/{len(expected_topics)})")
            if covered_topics:
                print(f"🎯 Covered: {', '.join(covered_topics)}")
            
            results.append({
                "question": question,
                "category": category,
                "response_length": len(response),
                "confidence": confidence,
                "topic_coverage": coverage,
                "chunks_found": len(found_chunks)
            })
            
        except Exception as e:
            print(f"❌ Agent error: {e}")
            results.append({
                "question": question,
                "category": category,
                "error": str(e)
            })
        
        print("-" * 60)
    
    return results


async def analyze_test_results(results):
    """Analyze and summarize the test results."""
    
    print("\n📊 === TEST RESULTS ANALYSIS ===")
    
    successful_tests = [r for r in results if 'error' not in r]
    failed_tests = [r for r in results if 'error' in r]
    
    print(f"✅ Successful tests: {len(successful_tests)}/{len(results)}")
    print(f"❌ Failed tests: {len(failed_tests)}")
    
    if successful_tests:
        avg_confidence = sum(r['confidence'] for r in successful_tests) / len(successful_tests)
        avg_coverage = sum(r['topic_coverage'] for r in successful_tests) / len(successful_tests)
        avg_chunks = sum(r['chunks_found'] for r in successful_tests) / len(successful_tests)
        avg_response_length = sum(r['response_length'] for r in successful_tests) / len(successful_tests)
        
        print(f"\n📈 Performance Metrics:")
        print(f"   Average confidence: {avg_confidence:.2f}")
        print(f"   Average topic coverage: {avg_coverage:.1%}")
        print(f"   Average chunks found: {avg_chunks:.1f}")
        print(f"   Average response length: {avg_response_length:.0f} chars")
        
        # Category analysis
        categories = {}
        for result in successful_tests:
            cat = result['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        print(f"\n🏷️  Performance by Category:")
        for category, cat_results in categories.items():
            cat_confidence = sum(r['confidence'] for r in cat_results) / len(cat_results)
            cat_coverage = sum(r['topic_coverage'] for r in cat_results) / len(cat_results)
            print(f"   {category}: {cat_confidence:.2f} confidence, {cat_coverage:.1%} coverage")


async def run_interactive_demo():
    """Run the complete interactive demo with realistic documents and questions."""
    
    print("🎪 === INTERACTIVE DOCUMENTASSISTANT DEMO ===")
    print("Real documents + Prepared questions + Chat testing")
    print("=" * 70)
    
    try:
        # Initialize iceOS
        print("🔧 Initializing iceOS orchestrator...")
        from ice_orchestrator import initialize_orchestrator
        initialize_orchestrator()
        print("✅ iceOS services initialized!")
        
        # Register components
        await register_components()
        
        # Create realistic documents
        print("\n📚 Creating realistic document collection...")
        file_paths = await create_realistic_documents()
        print(f"✅ Created {len(file_paths)} comprehensive documents")
        
        # Process documents through workflow
        print(f"\n🔄 Processing documents through DAG orchestrator...")
        
        workflow = (WorkflowBuilder("DocumentAssistant Knowledge Base")
            .add_tool("parse_docs", "document_parser", file_paths=file_paths)
            .add_tool("chunk_docs", "intelligent_chunker", 
                     strategy="semantic", chunk_size=800, overlap_size=100)
            .add_tool("index_docs", "semantic_search", 
                     action="index", collection="demo_knowledge_base")
            .connect("parse_docs", "chunk_docs")
            .connect("chunk_docs", "index_docs")
            .build()
        )
        
        result = await workflow.execute()
        print("✅ Document processing complete!")
        
        # Create tools for testing
        search_tool = SemanticSearchTool()
        
        # Create agent for chat testing
        from ice_orchestrator.agent.memory import MemoryAgentConfig
        agent_config = MemoryAgentConfig(
            id="demo_chat_agent",
            package="use_cases.DocumentAssistant.agents.document_chat_agent",
            tools=[],
            enable_memory=True
        )
        chat_agent = DocumentChatAgent(config=agent_config)
        
        # Test with prepared questions
        test_results = await test_user_questions(search_tool, chat_agent)
        
        # Analyze results
        await analyze_test_results(test_results)
        
        print(f"\n🎉 === INTERACTIVE DEMO COMPLETE ===")
        print("✅ Realistic documents processed")
        print("✅ Multiple user questions tested")
        print("✅ RAG functionality demonstrated")
        print("✅ Agent responses analyzed")
        print("\n💡 This demonstrates a production-ready chat-in-a-box system!")
        
        return {"success": True, "questions_tested": len(test_results)}
        
    except Exception as e:
        print(f"\n❌ Interactive demo failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    asyncio.run(run_interactive_demo()) 