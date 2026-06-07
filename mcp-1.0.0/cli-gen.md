# Model Context Protocol (MCP) CLI Generator Conformance Table

This table tracks the completeness of language CLI generator integration with the Model Context Protocol (MCP). It is divided into three sections:
1. **Architectural Integration Layers**: Tracks the exposure of MCP across the CLI, SDK, and Server boundaries.
2. **Semantic & Conceptual Features**: Tracks protocol mechanics, transports, and behavioral requirements.
3. **Schema & Object Conformance**: An exhaustive property-by-property map derived directly from the official MCP JSON Schema (2024-11-05).

### Legend & Tracking Guide
*   **To**: Language -> MCP (Generating MCP Server payloads and handling requests from strongly typed code)
*   **From**: MCP -> Language (Generating MCP Client code, parsing responses, and invoking remote methods)
*   **Presence `[To, From]`**: The object/feature is successfully parsed, validated, utilized, or generated.
*   **Absence `[To, From]`**: The object/feature is currently unsupported, dropped, or falls back to generic/`any` types.
*   **Skipped `[To, From]`**: Intentionally ignored because it is irrelevant or unsupported by the Client architecture.
*   **Checkboxes**: Mark `[x]` as conformance is achieved.

## 1. Architectural Integration Layers

This section tracks how the Model Context Protocol is exposed across both the **Generated Artifacts** (the output SDKs/APIs) and the **Generator Tooling** itself (the bidirectional `cdd` compiler/engine).

### 1A. Target/Generated Artifacts
Implementing MCP across the generated output ensures maximum flexibility for the end-user's AI architectures:

*   **CLI Integration (Local Desktop via `stdio`)**: Enables local AI assistants (Claude Desktop, Cursor, Windsurf) to spawn the generated CLI as a subprocess and natively interact with the API locally.
*   **SDK Integration (Programmatic / In-Memory)**: Provides native adapters (e.g., `client.mcp.get_tools()`) so developers can seamlessly attach the generated SDK to frameworks like LangChain, LlamaIndex, or raw LLM clients without network overhead.
*   **Server Integration (Remote AI Gateway via `sse`)**: Generates an AI Gateway endpoint (e.g., `/mcp/sse`), allowing remote, multi-tenant AI agents and web clients to securely consume the API as LLM tools over HTTP.

| Generated Boundary | Presence `[To, From]` | Absence `[To, From]` | Skipped `[To, From]` | Notes / Implementation Strategy |
| :--- | :---: | :---: | :---: | :--- |
| **CLI Integration (Local Desktop)** | | | | |
| CLI `mcp` Subcommand | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Generates a command (e.g., `app mcp`) to start the server |
| `stdio` Transport Bindings | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Wires stdin/stdout to the generated CLI logic |
| **SDK Integration (Programmatic)** | | | | |
| Native MCP Tool Adapter | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | E.g., `client.mcp.get_tools()` mapping SDK methods |
| Native MCP Resource Adapter | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Exposes internal state/docs as MCP resources |
| LLM Execution Router | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Native execution via `client.mcp.execute_tool(name, args)` |
| **Server Integration (Remote / SSE)** | | | | |
| SSE Endpoint Generation | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Wires MCP endpoints (e.g. `/mcp/sse`, `/mcp/message`) |
| HTTP Request/Auth Bridging | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Passes standard API auth into the MCP context |
| Dynamic API-to-Tool Proxy | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Resolves incoming tool calls to backend route handlers |

### 1B. Generator/Tooling Artifacts (Meta-MCP)
Exposing the `cdd` bidirectional code generator itself to MCP allows AI models to natively orchestrate code generation, schema manipulation, and code-to-schema extraction.

*   **Generator CLI via `stdio`**: Allows local IDEs or AI agents to directly instruct the generator to scaffold, diff, or compile code across languages (e.g., Tool: `cdd_generate(lang="python")`).
*   **Generator SDK / Core**: Exposes the AST and schema parsing engine natively to MCP, allowing AI tools to dynamically query API specs, understand types, and invoke generator internals in memory.

| Generator Boundary | Presence `[To, From]` | Absence `[To, From]` | Skipped `[To, From]` | Notes / Implementation Strategy |
| :--- | :---: | :---: | :---: | :--- |
| **Generator CLI (`stdio`)** | | | | |
| Code Scaffold / Generate Tools | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | AI can invoke standard generator CLI commands via MCP |
| Schema Inspection Tools | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | AI can query loaded OpenAPI/AsyncAPI schemas |
| Bidirectional Sync Tools | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | AI can trigger code-to-schema extraction natively |
| **Generator SDK / Core** | | | | |
| AST / Type Query Resources | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | AI can read internal AST structures as MCP resources |
| In-Memory Generation Router | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Native bindings to run the generator core directly via MCP |

## 2. Semantic & Conceptual Features

| MCP Feature / Behavior | Presence `[To, From]` | Absence `[To, From]` | Skipped `[To, From]` | Notes / Implementation Strategy |
| :--- | :---: | :---: | :---: | :--- |
| **Transports** | | | | |
| Standard I/O (stdio) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | stdin/stdout message passing |
| Server-Sent Events (sse) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | HTTP POST + SSE streams |
| Custom Transports | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Pluggable transport interface |
| **JSON-RPC 2.0 Mechanics** | | | | |
| Message Parsing & Serialization | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Request ID Mapping/Resolution | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Resolving async responses to requests |
| Error Code Mapping (Standard) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Codes like -32600, -32603 |
| Notification Handling | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Processing fire-and-forget messages |
| **Connection Lifecycle** | | | | |
| initialize Handshake Sequence | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Capability negotiation & version matching |
| initialized Acknowledgment | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Sent by client after successful initialization |
| Graceful Disconnect / Close | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Liveness (ping) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Periodic connection checks |
| Request Cancellation (cancelled)| `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Thread/Task abortion mechanics |
| **Behavioral & Security** | | | | |
| Pagination Cursor Management | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Handling nextCursor fetch loops |
| Progress Tracking (progress) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Emitting/handling progress events |
| Human-in-the-loop (Sampling) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Prompting user before LLM generation |
| Human-in-the-loop (Tools) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Security approvals/denials for tool calls |
| Root Boundary Enforcement | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Preventing traversal outside allowed directories |
| URI Protocol Handling | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | Resolving custom URI schemes |

## 3. Schema & Object Conformance

| Schema Definition / Property | Presence `[To, From]` | Absence `[To, From]` | Skipped `[To, From]` | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Annotated** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Annotated (`annotations`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Annotated (`annotations`) (`audience`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Annotated (`annotations`) (`priority`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **BlobResourceContents** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| BlobResourceContents (`blob`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| BlobResourceContents (`mimeType`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| BlobResourceContents (`uri`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **CallToolRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CallToolRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CallToolRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CallToolRequest (`params`) (`arguments`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CallToolRequest (`params`) (`name`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **CallToolResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CallToolResult (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| CallToolResult (`content`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CallToolResult (`isError`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **CancelledNotification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CancelledNotification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CancelledNotification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CancelledNotification (`params`) (`reason`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CancelledNotification (`params`) (`requestId`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ClientCapabilities** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ClientCapabilities (`experimental`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ClientCapabilities (`roots`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ClientCapabilities (`roots`) (`listChanged`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ClientCapabilities (`sampling`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ClientNotification** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ClientRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ClientResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **CompleteRequest** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteRequest (`method`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteRequest (`params`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteRequest (`params`) (`argument`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteRequest (`params`) (`argument`) (`name`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteRequest (`params`) (`argument`) (`value`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| CompleteRequest (`params`) (`ref`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **CompleteResult** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteResult (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteResult (`completion`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteResult (`completion`) (`hasMore`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteResult (`completion`) (`total`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CompleteResult (`completion`) (`values`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **CreateMessageRequest** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`method`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) (`includeContext`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) (`maxTokens`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) (`messages`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) (`metadata`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) (`modelPreferences`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) (`stopSequences`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) (`systemPrompt`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CreateMessageRequest (`params`) (`temperature`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| **CreateMessageResult** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CreateMessageResult (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| CreateMessageResult (`content`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| CreateMessageResult (`model`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| CreateMessageResult (`role`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| CreateMessageResult (`stopReason`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| **Cursor** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **EmbeddedResource** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| EmbeddedResource (`annotations`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| EmbeddedResource (`annotations`) (`audience`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| EmbeddedResource (`annotations`) (`priority`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| EmbeddedResource (`resource`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| EmbeddedResource (`type`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **EmptyResult** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **GetPromptRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| GetPromptRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| GetPromptRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| GetPromptRequest (`params`) (`arguments`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| GetPromptRequest (`params`) (`name`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **GetPromptResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| GetPromptResult (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| GetPromptResult (`description`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| GetPromptResult (`messages`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ImageContent** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ImageContent (`annotations`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ImageContent (`annotations`) (`audience`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ImageContent (`annotations`) (`priority`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ImageContent (`data`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ImageContent (`mimeType`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ImageContent (`type`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **Implementation** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Implementation (`name`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Implementation (`version`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **InitializeRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| InitializeRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| InitializeRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| InitializeRequest (`params`) (`capabilities`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| InitializeRequest (`params`) (`clientInfo`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| InitializeRequest (`params`) (`protocolVersion`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **InitializeResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| InitializeResult (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| InitializeResult (`capabilities`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| InitializeResult (`instructions`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| InitializeResult (`protocolVersion`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| InitializeResult (`serverInfo`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **InitializedNotification** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| InitializedNotification (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| InitializedNotification (`params`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| InitializedNotification (`params`) (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **JSONRPCError** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCError (`error`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCError (`error`) (`code`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCError (`error`) (`data`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| JSONRPCError (`error`) (`message`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCError (`id`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCError (`jsonrpc`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **JSONRPCMessage** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **JSONRPCNotification** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCNotification (`jsonrpc`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCNotification (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCNotification (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCNotification (`params`) (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **JSONRPCRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCRequest (`id`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCRequest (`jsonrpc`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCRequest (`params`) (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| JSONRPCRequest (`params`) (`_meta`) (`progressToken`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **JSONRPCResponse** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCResponse (`id`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCResponse (`jsonrpc`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| JSONRPCResponse (`result`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ListPromptsRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListPromptsRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListPromptsRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListPromptsRequest (`params`) (`cursor`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **ListPromptsResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListPromptsResult (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ListPromptsResult (`nextCursor`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ListPromptsResult (`prompts`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ListResourceTemplatesRequest** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourceTemplatesRequest (`method`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourceTemplatesRequest (`params`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourceTemplatesRequest (`params`) (`cursor`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ListResourceTemplatesResult** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourceTemplatesResult (`_meta`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourceTemplatesResult (`nextCursor`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourceTemplatesResult (`resourceTemplates`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ListResourcesRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourcesRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourcesRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourcesRequest (`params`) (`cursor`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **ListResourcesResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListResourcesResult (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ListResourcesResult (`nextCursor`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ListResourcesResult (`resources`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ListRootsRequest** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListRootsRequest (`method`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListRootsRequest (`params`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListRootsRequest (`params`) (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| ListRootsRequest (`params`) (`_meta`) (`progressToken`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| **ListRootsResult** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListRootsResult (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListRootsResult (`roots`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ListToolsRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListToolsRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListToolsRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListToolsRequest (`params`) (`cursor`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **ListToolsResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ListToolsResult (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ListToolsResult (`nextCursor`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ListToolsResult (`tools`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **LoggingLevel** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **LoggingMessageNotification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| LoggingMessageNotification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| LoggingMessageNotification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| LoggingMessageNotification (`params`) (`data`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| LoggingMessageNotification (`params`) (`level`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| LoggingMessageNotification (`params`) (`logger`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ModelHint** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ModelHint (`name`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ModelPreferences** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ModelPreferences (`costPriority`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ModelPreferences (`hints`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ModelPreferences (`intelligencePriority`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ModelPreferences (`speedPriority`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **Notification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Notification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Notification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Notification (`params`) (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **PaginatedRequest** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PaginatedRequest (`method`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PaginatedRequest (`params`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PaginatedRequest (`params`) (`cursor`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **PaginatedResult** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PaginatedResult (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[x]` | `[ ]` , `[ ]` | |
| PaginatedResult (`nextCursor`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **PingRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PingRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PingRequest (`params`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| PingRequest (`params`) (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| PingRequest (`params`) (`_meta`) (`progressToken`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **ProgressNotification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ProgressNotification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ProgressNotification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ProgressNotification (`params`) (`progressToken`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ProgressNotification (`params`) (`progress`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ProgressNotification (`params`) (`total`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ProgressToken** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **Prompt** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Prompt (`arguments`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| Prompt (`description`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| Prompt (`name`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **PromptArgument** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptArgument (`description`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptArgument (`name`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptArgument (`required`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **PromptListChangedNotification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptListChangedNotification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptListChangedNotification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptListChangedNotification (`params`) (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **PromptMessage** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptMessage (`content`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptMessage (`role`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **PromptReference** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptReference (`name`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| PromptReference (`type`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ReadResourceRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ReadResourceRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ReadResourceRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ReadResourceRequest (`params`) (`uri`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ReadResourceResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ReadResourceResult (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ReadResourceResult (`contents`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **Request** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Request (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Request (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Request (`params`) (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Request (`params`) (`_meta`) (`progressToken`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **RequestId** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **Resource** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Resource (`annotations`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Resource (`annotations`) (`audience`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Resource (`annotations`) (`priority`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Resource (`description`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Resource (`mimeType`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Resource (`name`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Resource (`size`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Resource (`uri`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ResourceContents** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceContents (`mimeType`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceContents (`uri`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ResourceListChangedNotification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceListChangedNotification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceListChangedNotification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceListChangedNotification (`params`) (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ResourceReference** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceReference (`type`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceReference (`uri`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ResourceTemplate** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceTemplate (`annotations`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceTemplate (`annotations`) (`audience`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceTemplate (`annotations`) (`priority`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceTemplate (`description`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceTemplate (`mimeType`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceTemplate (`name`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceTemplate (`uriTemplate`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ResourceUpdatedNotification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceUpdatedNotification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceUpdatedNotification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ResourceUpdatedNotification (`params`) (`uri`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **Result** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Result (`_meta`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **Role** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **Root** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Root (`name`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Root (`uri`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **RootsListChangedNotification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| RootsListChangedNotification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| RootsListChangedNotification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| RootsListChangedNotification (`params`) (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **SamplingMessage** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| SamplingMessage (`content`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| SamplingMessage (`role`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ServerCapabilities** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`experimental`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`logging`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`prompts`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`prompts`) (`listChanged`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`resources`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`resources`) (`listChanged`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`resources`) (`subscribe`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`tools`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ServerCapabilities (`tools`) (`listChanged`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **ServerNotification** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ServerRequest** | `[x]` , `[x]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **ServerResult** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **SetLevelRequest** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| SetLevelRequest (`method`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| SetLevelRequest (`params`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| SetLevelRequest (`params`) (`level`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| **SubscribeRequest** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| SubscribeRequest (`method`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| SubscribeRequest (`params`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| SubscribeRequest (`params`) (`uri`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **TextContent** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| TextContent (`annotations`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| TextContent (`annotations`) (`audience`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| TextContent (`annotations`) (`priority`) | `[ ]` , `[ ]` | `[x]` , `[x]` | `[ ]` , `[ ]` | |
| TextContent (`text`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| TextContent (`type`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **TextResourceContents** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| TextResourceContents (`mimeType`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| TextResourceContents (`text`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| TextResourceContents (`uri`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **Tool** | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Tool (`description`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Tool (`inputSchema`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Tool (`inputSchema`) (`properties`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Tool (`inputSchema`) (`required`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Tool (`inputSchema`) (`type`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| Tool (`name`) | `[x]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **ToolListChangedNotification** | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ToolListChangedNotification (`method`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ToolListChangedNotification (`params`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| ToolListChangedNotification (`params`) (`_meta`) | `[ ]` , `[ ]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| **UnsubscribeRequest** | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| UnsubscribeRequest (`method`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| UnsubscribeRequest (`params`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
| UnsubscribeRequest (`params`) (`uri`) | `[ ]` , `[x]` | `[ ]` , `[ ]` | `[ ]` , `[ ]` | |
