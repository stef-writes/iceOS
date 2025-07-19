flowchart TD
    A[Trigger: Surplus Inventory Identified] --> B[LLM Orchestrator]
    B --> C1[Skill Node: Image Processing]
    B --> C2[Skill Node: Description Generation]
    B --> C3[Skill Node: Pricing Optimization]
    B --> C4[Skill Node: FAQ Handler]

    subgraph Tools
        T1[(Inventory System)]
        T2[Facebook Marketplace API]
        T3[CRM Database]
        T4[Analytics Dashboard]
    end

    C1 --> D1[Tool: Image Enhancer\n e.g., DALL-E/Imagen]
    C2 --> D2[Tool: LLM Description Generator\n e.g., GPT-4]
    C3 --> D3[Tool: Pricing Algorithm\n Historical Data + Competitor Scan]
    C4 --> D4[Tool: Chatbot Gateway\n e.g., ManyChat]

    D1 --> E[Compiled Listing Draft]
    D2 --> E
    D3 --> E
    E --> F[Human Approval Interface]
    F -->|Reject| B
    F -->|Approve| G[Automated Publishing\n via Marketplace API]

    G --> H[Real-Time Sync\n Inventory System]
    H --> T1

    I[Customer Inquiry] --> C4
    C4 -->|Simple Query| J[Auto-Response\n e.g., Availability, Price]
    C4 -->|Complex Query| K[Human Escalation\n + CRM Logging]
    J --> T3
    K --> T3

    T1 --> L[Analytics Engine]
    T2 --> L
    T3 --> L
    L --> M[AI Optimization Loop]
    M -->|Feedback| B[LLM Orchestrator]