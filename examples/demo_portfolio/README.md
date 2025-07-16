# Demo Portfolio Overview

This directory hosts a curated set of end-to-end demos that incrementally showcase iceOS features.  Each demo builds on the components of the previous ones so new developers can follow a straight learning path and the codebase avoids duplication.

| Dev Step | Demo Folder | Primary New Surface Area |
|---------:|-------------|---------------------------|
| 1 | `knowledge_base_builder` | Multi-source ingestion & vector store |
| 2 | `chat_in_a_box` | Retrieval-augmented answering + deployment |
| 3 | `workflow_automator` | OAuth SaaS integrations + condition executor |
| 4 | `youtube_looper` | Multi-modal (TTS, image) & event triggers |
| 5 | `content_beast_publisher` | Branching, scheduler, multi-channel publishing |
| 6 | `research_assistant_mcp` | External MCP model path + dynamic selection |
| 7 | `dynamic_form_builder` | Code-generation & build pipeline tools |
| 8 | `desktop_automation_agent` | Local system control via `ComputerTool` |
| 9 | `zoom_meeting_summarizer` | Live streaming ingestion & rolling summarisation |

## Reuse Philosophy
- **Tools first** – standalone, idempotent, typed.  Demos import rather than re-implement.
- **Nodes next** – small, single-responsibility units used by many chains.
- **Chains last** – TOML wiring that glues tools/nodes together for a scenario.

Read each demo’s README for an explicit list of reusable artifacts it introduces. 

---

## Incremental Component Map
The table below shows the **new** building blocks introduced at each development step.  If a demo re-uses a component from an earlier step it is **not** listed again.

| Step | Demo | New Tools | New Nodes / Models | New Agents / Executors | Notes |
|-----:|------|-----------|--------------------|------------------------|-------|
| 0 | composition_layer | ChainExecutorTool, CompositeAgent | — | — | Enables micro-chain execution and bundling |
| 1 | knowledge_base_builder | FetcherTool, VectorStoreWriterTool, KBRegistryTool | TextExtractorNode, ChunkerNode, PIIScrubValidator | — | Establishes KB ingestion + vector store infrastructure |
| 2 | chat_in_a_box | ChatUIDeploymentTool | FormIntakeNode, PromptBuilderNode | ChatbotDeploymentAgent | Leverages RetrievalNode & ValidatorNode from Step 1 |
| 3 | workflow_automator | GmailWatchTool, DriveMoveTool, SlackPosterTool | EmailParserNode | — | Adds OAuth SaaS tools; re-uses ConditionExecutor & WebhookTool |
| 4 | youtube_looper | TTSVoiceTool, ThumbnailImageTool, YouTubeUploadTool, YouTubeCommentListener | ScriptGeneratorNode, CommentSummariserNode | — | Introduces multi-modal media handling |
| 5 | content_beast_publisher | TwitterPostTool, LinkedInPostTool, InstagramPostTool, MetricListenerTool | ChannelAdapterNode, PostingSchedulerNode | — | Re-uses YouTubeShortsTool (Step 4) & ContentSegmenterNode |
| 6 | research_assistant_mcp | MCPInferenceTool | PlannerNode | — | Demonstrates external model path & dynamic selection |
| 7 | dynamic_form_builder | BundlerTool, HostingTool, QRCodeTool | FormSpec (model), SpecInterpreterNode, ComponentGeneratorNode, StylingNode | — | Shows asset code-gen & build pipeline |
| 8 | desktop_automation_agent | AuditLoggerTool | DesktopControllerNode | — | Uses existing ComputerTool & SchedulerNode |
| 9 | zoom_meeting_summarizer | ZoomListenerTool | SpeakerMapperNode, ChunkBufferNode | — | Streams live transcripts; re-uses summarisation & delivery utilities |

Use this map to prioritise implementation: finish all items in a row before moving to the next step to ensure downstream demos compile without stubs. 