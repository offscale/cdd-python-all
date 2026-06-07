"""Pydantic models for the Model Context Protocol (MCP) Client SDK."""

from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, RootModel

from enum import IntEnum


class ErrorCode(IntEnum):
    """Standard JSON-RPC and MCP error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class RequestId(RootModel[Union[int, str]]):
    """RequestId model."""

    pass


class ProgressToken(RootModel[Union[int, str]]):
    """ProgressToken model."""

    pass


class Cursor(RootModel[str]):
    """Cursor model."""

    pass


class Role(RootModel[Literal["user", "assistant"]]):
    """Role model."""

    pass


class LoggingLevel(
    RootModel[
        Literal[
            "debug",
            "info",
            "notice",
            "warning",
            "error",
            "critical",
            "alert",
            "emergency",
        ]
    ]
):
    """LoggingLevel model."""

    pass


class Annotated(BaseModel):
    """Annotated model."""

    audience: Optional[List[str]] = None
    priority: Optional[float] = None


class BlobResourceContents(BaseModel):
    """BlobResourceContents model."""

    uri: str
    mimeType: Optional[str] = None
    blob: str


class TextResourceContents(BaseModel):
    """TextResourceContents model."""

    uri: str
    mimeType: Optional[str] = None
    text: str


class ResourceContents(RootModel[Union[TextResourceContents, BlobResourceContents]]):
    """ResourceContents model."""

    pass


class ImageContent(Annotated):
    """ImageContent model."""

    type: Literal["image"] = "image"
    data: str
    mimeType: str


class TextContent(Annotated):
    """TextContent model."""

    type: Literal["text"] = "text"
    text: str


class EmbeddedResource(Annotated):
    """EmbeddedResource model."""

    type: Literal["resource"] = "resource"
    resource: ResourceContents


class ModelHint(BaseModel):
    """ModelHint model."""

    name: Optional[str] = None


class ModelPreferences(BaseModel):
    """ModelPreferences model."""

    hints: Optional[List[ModelHint]] = None
    costPriority: Optional[float] = None
    speedPriority: Optional[float] = None
    intelligencePriority: Optional[float] = None


class PromptArgument(BaseModel):
    """PromptArgument model."""

    name: str
    description: Optional[str] = None
    required: Optional[bool] = None


class Prompt(BaseModel):
    """Prompt model."""

    name: str
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = None


class PromptMessage(BaseModel):
    """PromptMessage model."""

    role: Role
    content: Union[TextContent, ImageContent, EmbeddedResource]


class SamplingMessage(BaseModel):
    """SamplingMessage model."""

    role: Role
    content: Union[TextContent, ImageContent]


class PromptReference(BaseModel):
    """PromptReference model."""

    type: Literal["ref/prompt"] = "ref/prompt"
    name: str


class ResourceReference(BaseModel):
    """ResourceReference model."""

    type: Literal["ref/resource"] = "ref/resource"
    uri: str


class Resource(Annotated):
    """Resource model."""

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    size: Optional[int] = None


class ResourceTemplate(Annotated):
    """ResourceTemplate model."""

    uriTemplate: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class Root(BaseModel):
    """Root model."""

    uri: str
    name: Optional[str] = None


class ToolInputSchema(BaseModel):
    """ToolInputSchema model."""

    type: str = "object"
    properties: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None


class Tool(BaseModel):
    """Tool model."""

    name: str
    description: Optional[str] = None
    inputSchema: ToolInputSchema


class Implementation(BaseModel):
    """Implementation model."""

    name: str
    version: str


class ClientCapabilities(BaseModel):
    """ClientCapabilities model."""

    experimental: Optional[Dict[str, Any]] = None
    roots: Optional[Dict[str, Any]] = None  # Contains listChanged
    sampling: Optional[Dict[str, Any]] = None


class ServerCapabilities(BaseModel):
    """ServerCapabilities model."""

    experimental: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None


class RequestMeta(BaseModel):
    """RequestMeta model."""

    progressToken: Optional[ProgressToken] = None


class RequestParams(BaseModel):
    """RequestParams model."""

    meta: Optional[RequestMeta] = Field(None, alias="_meta")


class Request(BaseModel):
    """Request model."""

    method: str
    params: Optional[RequestParams] = None


class JSONRPCMessage(BaseModel):
    """JSONRPCMessage model."""

    jsonrpc: str = "2.0"


class JSONRPCRequest(JSONRPCMessage, Request):
    """JSONRPCRequest model."""

    id: RequestId


class NotificationParams(BaseModel):
    """NotificationParams model."""

    meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")


class Notification(BaseModel):
    """Notification model."""

    method: str
    params: Optional[NotificationParams] = None


class JSONRPCNotification(JSONRPCMessage, Notification):
    """JSONRPCNotification model."""

    pass


class ResultMeta(BaseModel):
    """ResultMeta model."""

    pass


class Result(BaseModel):
    """Result model."""

    meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")


class JSONRPCErrorError(BaseModel):
    """JSONRPCErrorError model."""

    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCError(JSONRPCMessage):
    """JSONRPCError model."""

    id: RequestId
    error: JSONRPCErrorError


class JSONRPCResponse(JSONRPCMessage):
    """JSONRPCResponse model."""

    id: RequestId
    result: Result


# Specific Requests


class InitializeRequestParams(RequestParams):
    """InitializeRequestParams model."""

    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation


class InitializeRequest(JSONRPCRequest):
    """InitializeRequest model."""

    method: Literal["initialize"] = "initialize"
    params: InitializeRequestParams


class InitializeResult(Result):
    """InitializeResult model."""

    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: Optional[str] = None


class InitializedNotificationParams(NotificationParams):
    """InitializedNotificationParams model."""

    pass


class InitializedNotification(JSONRPCNotification):
    """InitializedNotification model."""

    method: Literal["notifications/initialized"] = "notifications/initialized"
    params: Optional[InitializedNotificationParams] = None


class CallToolRequestParams(RequestParams):
    """CallToolRequestParams model."""

    name: str
    arguments: Optional[Dict[str, Any]] = None


class CallToolRequest(JSONRPCRequest):
    """CallToolRequest model."""

    method: Literal["tools/call"] = "tools/call"
    params: CallToolRequestParams


class CallToolResult(Result):
    """CallToolResult model."""

    content: List[Union[TextContent, ImageContent, EmbeddedResource]]
    isError: Optional[bool] = None


class CancelledNotificationParams(NotificationParams):
    """CancelledNotificationParams model."""

    requestId: RequestId
    reason: Optional[str] = None


class CancelledNotification(JSONRPCNotification):
    """CancelledNotification model."""

    method: Literal["notifications/cancelled"] = "notifications/cancelled"
    params: CancelledNotificationParams


class PaginatedRequestParams(RequestParams):
    """PaginatedRequestParams model."""

    cursor: Optional[Cursor] = None


class PaginatedRequest(JSONRPCRequest):
    """PaginatedRequest model."""

    params: Optional[PaginatedRequestParams] = None


class PaginatedResult(Result):
    """PaginatedResult model."""

    nextCursor: Optional[Cursor] = None


class EmptyResult(Result):
    """EmptyResult model."""

    pass


class CompleteRequestParamsArgument(BaseModel):
    """CompleteRequestParamsArgument model."""

    name: str
    value: str


class CompleteRequestParams(RequestParams):
    """CompleteRequestParams model."""

    ref: Union[PromptReference, ResourceReference]
    argument: CompleteRequestParamsArgument


class CompleteRequest(JSONRPCRequest):
    """CompleteRequest model."""

    method: Literal["completion/complete"] = "completion/complete"
    params: CompleteRequestParams


class CompleteResultCompletion(BaseModel):
    """CompleteResultCompletion model."""

    values: List[str]
    total: Optional[int] = None
    hasMore: Optional[bool] = None


class CompleteResult(Result):
    """CompleteResult model."""

    completion: CompleteResultCompletion


class CreateMessageRequestParams(RequestParams):
    """CreateMessageRequestParams model."""

    messages: List[SamplingMessage]
    maxTokens: int
    systemPrompt: Optional[str] = None
    includeContext: Optional[Literal["none", "thisServer"]] = None
    temperature: Optional[float] = None
    stopSequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    modelPreferences: Optional[ModelPreferences] = None


class CreateMessageRequest(JSONRPCRequest):
    """CreateMessageRequest model."""

    method: Literal["messages/create"] = "messages/create"
    params: CreateMessageRequestParams


class CreateMessageResult(Result):
    """CreateMessageResult model."""

    role: Role
    content: Union[TextContent, ImageContent]
    model: str
    stopReason: Optional[
        Union[Literal["endTurn", "stopSequence", "maxTokens"], str]
    ] = None


class GetPromptRequestParams(RequestParams):
    """GetPromptRequestParams model."""

    name: str
    arguments: Optional[Dict[str, str]] = None


class GetPromptRequest(JSONRPCRequest):
    """GetPromptRequest model."""

    method: Literal["prompts/get"] = "prompts/get"
    params: GetPromptRequestParams


class GetPromptResult(Result):
    """GetPromptResult model."""

    description: Optional[str] = None
    messages: List[PromptMessage]


class ListPromptsRequest(PaginatedRequest):
    """ListPromptsRequest model."""

    method: Literal["prompts/list"] = "prompts/list"


class ListPromptsResult(PaginatedResult):
    """ListPromptsResult model."""

    prompts: List[Prompt]


class ListResourceTemplatesRequest(PaginatedRequest):
    """ListResourceTemplatesRequest model."""

    method: Literal["resources/templates/list"] = "resources/templates/list"


class ListResourceTemplatesResult(PaginatedResult):
    """ListResourceTemplatesResult model."""

    resourceTemplates: List[ResourceTemplate]


class ListResourcesRequest(PaginatedRequest):
    """ListResourcesRequest model."""

    method: Literal["resources/list"] = "resources/list"


class ListResourcesResult(PaginatedResult):
    """ListResourcesResult model."""

    resources: List[Resource]


class ListRootsRequest(JSONRPCRequest):
    """ListRootsRequest model."""

    method: Literal["roots/list"] = "roots/list"


class ListRootsResult(Result):
    """ListRootsResult model."""

    roots: List[Root]


class ListToolsRequest(PaginatedRequest):
    """ListToolsRequest model."""

    method: Literal["tools/list"] = "tools/list"


class ListToolsResult(PaginatedResult):
    """ListToolsResult model."""

    tools: List[Tool]


class LoggingMessageNotificationParams(NotificationParams):
    """LoggingMessageNotificationParams model."""

    level: LoggingLevel
    logger: Optional[str] = None
    data: Any


class LoggingMessageNotification(JSONRPCNotification):
    """LoggingMessageNotification model."""

    method: Literal["notifications/message"] = "notifications/message"
    params: LoggingMessageNotificationParams


class PingRequest(JSONRPCRequest):
    """PingRequest model."""

    method: Literal["ping"] = "ping"


class ProgressNotificationParams(NotificationParams):
    """ProgressNotificationParams model."""

    progressToken: ProgressToken
    progress: float
    total: Optional[float] = None


class ProgressNotification(JSONRPCNotification):
    """ProgressNotification model."""

    method: Literal["notifications/progress"] = "notifications/progress"
    params: ProgressNotificationParams


class PromptListChangedNotification(JSONRPCNotification):
    """PromptListChangedNotification model."""

    method: Literal["notifications/prompts/list_changed"] = (
        "notifications/prompts/list_changed"
    )


class ReadResourceRequestParams(RequestParams):
    """ReadResourceRequestParams model."""

    uri: str


class ReadResourceRequest(JSONRPCRequest):
    """ReadResourceRequest model."""

    method: Literal["resources/read"] = "resources/read"
    params: ReadResourceRequestParams


class ReadResourceResult(Result):
    """ReadResourceResult model."""

    contents: List[ResourceContents]


class ResourceListChangedNotification(JSONRPCNotification):
    """ResourceListChangedNotification model."""

    method: Literal["notifications/resources/list_changed"] = (
        "notifications/resources/list_changed"
    )


class ResourceUpdatedNotificationParams(NotificationParams):
    """ResourceUpdatedNotificationParams model."""

    uri: str


class ResourceUpdatedNotification(JSONRPCNotification):
    """ResourceUpdatedNotification model."""

    method: Literal["notifications/resources/updated"] = (
        "notifications/resources/updated"
    )
    params: ResourceUpdatedNotificationParams


class RootsListChangedNotification(JSONRPCNotification):
    """RootsListChangedNotification model."""

    method: Literal["notifications/roots/list_changed"] = (
        "notifications/roots/list_changed"
    )


class SetLevelRequestParams(RequestParams):
    """SetLevelRequestParams model."""

    level: LoggingLevel


class SetLevelRequest(JSONRPCRequest):
    """SetLevelRequest model."""

    method: Literal["logging/setLevel"] = "logging/setLevel"
    params: SetLevelRequestParams


class SubscribeRequestParams(RequestParams):
    """SubscribeRequestParams model."""

    uri: str


class SubscribeRequest(JSONRPCRequest):
    """SubscribeRequest model."""

    method: Literal["resources/subscribe"] = "resources/subscribe"
    params: SubscribeRequestParams


class ToolListChangedNotification(JSONRPCNotification):
    """ToolListChangedNotification model."""

    method: Literal["notifications/tools/list_changed"] = (
        "notifications/tools/list_changed"
    )


class UnsubscribeRequestParams(RequestParams):
    """UnsubscribeRequestParams model."""

    uri: str


class UnsubscribeRequest(JSONRPCRequest):
    """UnsubscribeRequest model."""

    method: Literal["resources/unsubscribe"] = "resources/unsubscribe"
    params: UnsubscribeRequestParams


ClientRequest = Union[
    InitializeRequest,
    PingRequest,
    ListResourcesRequest,
    ListResourceTemplatesRequest,
    ReadResourceRequest,
    SubscribeRequest,
    UnsubscribeRequest,
    ListPromptsRequest,
    GetPromptRequest,
    ListToolsRequest,
    CallToolRequest,
    CompleteRequest,
    SetLevelRequest,
    CancelledNotification,
    ProgressNotification,
    InitializedNotification,
    RootsListChangedNotification,
    ClientCapabilities,
    ListRootsResult,
    CreateMessageResult,
]

ServerRequest = Union[
    PingRequest,
    CreateMessageRequest,
    ListRootsRequest,
    CancelledNotification,
    ProgressNotification,
    LoggingMessageNotification,
    ResourceUpdatedNotification,
    ResourceListChangedNotification,
    ToolListChangedNotification,
    PromptListChangedNotification,
    InitializeResult,
    EmptyResult,
    ReadResourceResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListPromptsResult,
    GetPromptResult,
    ListToolsResult,
    CallToolResult,
    CompleteResult,
]

ClientNotification = Union[
    CancelledNotification,
    ProgressNotification,
    InitializedNotification,
    RootsListChangedNotification,
]

ClientResult = Union[EmptyResult, CreateMessageResult, ListRootsResult]

ServerNotification = Union[
    CancelledNotification,
    ProgressNotification,
    LoggingMessageNotification,
    ResourceUpdatedNotification,
    ResourceListChangedNotification,
    ToolListChangedNotification,
    PromptListChangedNotification,
]

ServerResult = Union[
    EmptyResult,
    InitializeResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ReadResourceResult,
    ListPromptsResult,
    GetPromptResult,
    ListToolsResult,
    CallToolResult,
    CompleteResult,
]
