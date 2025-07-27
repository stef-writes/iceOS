# WASM Security Best Practices for iceOS

## ✅ **CORRECTED STRATEGY: Selective WASM Sandboxing**

After implementing and testing WASM sandboxing across the platform, we've refined our strategy based on real-world requirements and production constraints.

## 🎯 **Current Implementation (Recommended)**

### **Direct Execution (No WASM)**
✅ Use for trusted system components:

- **Tool Nodes** (`@register_node("tool")`)
  - Need file I/O for document parsing, CSV reading
  - Require network access for API calls
  - Must import external libraries (PyPDF2, requests, etc.)
  
- **Agent Nodes** (`@register_node("agent")`)
  - Need full Python capabilities for reasoning
  - Access to memory systems and context
  - Integration with LLM services
  
- **LLM Nodes** (`@register_node("llm")`)
  - Require network access for OpenAI/Anthropic APIs
  - Need complex response processing
  - Real-time streaming capabilities

### **WASM Sandboxing** 🔒
✅ Use for untrusted user content:

- **Code Nodes** (`@register_node("code")`)
  - Arbitrary user Python code
  - Unknown security risk
  - Resource limits essential

## 🚫 **Why Universal WASM Failed**

Our initial "WASM on ALL nodes" strategy caused cascading failures:

```
❌ Document Parser → Can't read files → Pipeline fails
❌ API Tools → Network blocked → Integration fails  
❌ LLM Nodes → No API access → AI functionality broken
❌ Agents → Can't import libraries → Logic fails
```

### **Failure Examples from Production:**

1. **DocumentAssistant Demo**: Document parsing failed because WASM couldn't access filesystem
2. **Marketplace Demo**: API calls blocked by WASM network restrictions
3. **Intelligent Chunker**: Couldn't import required NLP libraries
4. **Semantic Search**: Vector database connections failed

## 🎯 **Decision Matrix: WASM vs Direct**

| Node Type | Execution Mode | Reasoning |
|-----------|---------------|-----------|
| `tool` | **Direct** | Needs file I/O, network, libraries |
| `agent` | **Direct** | Trusted system component |
| `llm` | **Direct** | API access required |
| `code` | **WASM** | Untrusted user code |
| `condition` | **WASM** | Often contains user expressions |
| `loop` | **Direct** | System control flow |
| `parallel` | **Direct** | Orchestration logic |
| `workflow` | **Direct** | Container node |

## 🏗️ **Implementation Guidelines**

### **For Tool Developers**
```python
# ✅ Tools get direct execution automatically
@register_node("tool")
async def my_tool_executor(workflow, cfg, ctx):
    tool = registry.get_instance(NodeType.TOOL, cfg.tool_name)
    # Direct execution - full system access
    result = await tool.execute(inputs)
    return NodeExecutionResult(success=True, output=result)
```

### **For User Code**
```python
# 🔒 User code gets WASM sandboxing
@register_node("code") 
async def code_executor(workflow, cfg, ctx):
    # WASM sandbox with resource limits
    return await execute_node_with_wasm(
        node_type="code",
        code=cfg.code,
        context=ctx,
        allowed_imports=cfg.imports
    )
```

## 🔐 **Security Boundaries**

```
┌─────────────────────────────────────────┐
│               iceOS Platform             │
├─────────────────────────────────────────┤
│  🟢 TRUSTED (Direct Execution)          │
│  • System tools and agents              │
│  • LLM integrations                     │
│  • Core orchestration logic            │
├─────────────────────────────────────────┤
│  🔒 UNTRUSTED (WASM Sandboxed)         │
│  • User-provided code                  │
│  • Dynamic expressions                 │
│  • Third-party scripts                 │
└─────────────────────────────────────────┘
```

## 📊 **Performance Impact**

| Execution Mode | Startup Time | Runtime Overhead | Memory Usage |
|---------------|--------------|------------------|--------------|
| Direct | ~5ms | Negligible | Normal |
| WASM | ~50-200ms | 10-30% | +32MB base |

**Recommendation**: Use WASM only when security risk justifies the overhead.

## 🛠️ **Configuration Examples**

### **Secure Code Node**
```yaml
nodes:
  - id: user_script
    type: code
    code: |
      # User provided Python code
      result = process_data(inputs['data'])
      return {"processed": result}
    imports: ["json", "math"]  # Restricted imports
```

### **Tool Node (Direct)**
```yaml
nodes:
  - id: document_parser
    type: tool
    tool_name: document_parser
    tool_args:
      file_paths: ["doc1.pdf", "doc2.docx"]
    # Automatically gets direct execution
```

## 🎉 **Benefits of Selective Strategy**

✅ **Security**: Untrusted code still sandboxed  
✅ **Performance**: No unnecessary overhead for trusted components  
✅ **Compatibility**: Tools can use full Python ecosystem  
✅ **Reliability**: Network and I/O operations work correctly  
✅ **Developer Experience**: Natural tool development without restrictions

## 🚀 **Future Enhancements**

1. **Runtime Security Analysis**: Detect high-risk code automatically
2. **Graduated Sandboxing**: Different WASM configs based on trust level
3. **Capability-Based Security**: Fine-grained permission system
4. **Plugin Sandboxing**: Optional WASM for third-party components

---

> **Key Takeaway**: Security through selective sandboxing, not blanket restrictions. The right tool for the right job! 🎯 