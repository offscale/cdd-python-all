"""Pydantic models for the Model Context Protocol (MCP) Client SDK."""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, RootModel


class ErrorCode(IntEnum):
    """Standard JSON-RPC and MCP error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class RequestId(RootModel[Union[int, str]]):
    """RequestId model."""


class ProgressToken(RootModel[Union[int, str]]):
    """ProgressToken model."""


class Cursor(RootModel[str]):
    """Cursor model."""


class Role(RootModel[Literal["user", "assistant"]]):
    """Role model."""


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


class Annotated(BaseModel):
    """Annotated model."""

    audience: list[str] | None = None
    priority: float | None = None


class BlobResourceContents(BaseModel):
    """BlobResourceContents model."""

    uri: str
    mimeType: str | None = None
    blob: str


class TextResourceContents(BaseModel):
    """TextResourceContents model."""

    uri: str
    mimeType: str | None = None
    text: str


class ResourceContents(RootModel[Union[TextResourceContents, BlobResourceContents]]):
    """ResourceContents model."""


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

    name: str | None = None


class ModelPreferences(BaseModel):
    """ModelPreferences model."""

    hints: list[ModelHint] | None = None
    costPriority: float | None = None
    speedPriority: float | None = None
    intelligencePriority: float | None = None


class PromptArgument(BaseModel):
    """PromptArgument model."""

    name: str
    description: str | None = None
    required: bool | None = None


class Prompt(BaseModel):
    """Prompt model."""

    name: str
    description: str | None = None
    arguments: list[PromptArgument] | None = None


class PromptMessage(BaseModel):
    """PromptMessage model."""

    role: Role
    content: TextContent | ImageContent | EmbeddedResource


class SamplingMessage(BaseModel):
    """SamplingMessage model."""

    role: Role
    content: TextContent | ImageContent


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
    description: str | None = None
    mimeType: str | None = None
    size: int | None = None


class ResourceTemplate(Annotated):
    """ResourceTemplate model."""

    uriTemplate: str
    name: str
    description: str | None = None
    mimeType: str | None = None


class Root(BaseModel):
    """Root model."""

    uri: str
    name: str | None = None


class ToolInputSchema(BaseModel):
    """ToolInputSchema model."""

    type: str = "object"
    properties: dict[str, Any] | None = None
    required: list[str] | None = None


class Tool(BaseModel):
    """Tool model."""

    name: str
    description: str | None = None
    inputSchema: ToolInputSchema


class Implementation(BaseModel):
    """Implementation model."""

    name: str
    version: str


class ClientCapabilities(BaseModel):
    """ClientCapabilities model."""

    experimental: dict[str, Any] | None = None
    roots: dict[str, Any] | None = None
    sampling: dict[str, Any] | None = None


class ServerCapabilities(BaseModel):
    """ServerCapabilities model."""

    experimental: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None


class RequestMeta(BaseModel):
    """RequestMeta model."""

    progressToken: ProgressToken | None = None


class RequestParams(BaseModel):
    """RequestParams model."""

    meta: RequestMeta | None = Field(None, alias="_meta")


class Request(BaseModel):
    """Request model."""

    method: str
    params: RequestParams | None = None


class JSONRPCMessage(BaseModel):
    """JSONRPCMessage model."""

    jsonrpc: str = "2.0"


class JSONRPCRequest(JSONRPCMessage, Request):
    """JSONRPCRequest model."""

    id: RequestId


class NotificationParams(BaseModel):
    """NotificationParams model."""

    meta: dict[str, Any] | None = Field(None, alias="_meta")


class Notification(BaseModel):
    """Notification model."""

    method: str
    params: NotificationParams | None = None


class JSONRPCNotification(JSONRPCMessage, Notification):
    """JSONRPCNotification model."""


class ResultMeta(BaseModel):
    """ResultMeta model."""


class Result(BaseModel):
    """Result model."""

    meta: dict[str, Any] | None = Field(None, alias="_meta")


class JSONRPCErrorError(BaseModel):
    """JSONRPCErrorError model."""

    code: int
    message: str
    data: Any | None = None


class JSONRPCError(JSONRPCMessage):
    """JSONRPCError model."""

    id: RequestId
    error: JSONRPCErrorError


class JSONRPCResponse(JSONRPCMessage):
    """JSONRPCResponse model."""

    id: RequestId
    result: Result


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
    instructions: str | None = None


class InitializedNotificationParams(NotificationParams):
    """InitializedNotificationParams model."""


class InitializedNotification(JSONRPCNotification):
    """InitializedNotification model."""

    method: Literal["notifications/initialized"] = "notifications/initialized"
    params: InitializedNotificationParams | None = None


class CallToolRequestParams(RequestParams):
    """CallToolRequestParams model."""

    name: str
    arguments: dict[str, Any] | None = None


class CallToolRequest(JSONRPCRequest):
    """CallToolRequest model."""

    method: Literal["tools/call"] = "tools/call"
    params: CallToolRequestParams


class CallToolResult(Result):
    """CallToolResult model."""

    content: list[TextContent | ImageContent | EmbeddedResource]
    isError: bool | None = None


class CancelledNotificationParams(NotificationParams):
    """CancelledNotificationParams model."""

    requestId: RequestId
    reason: str | None = None


class CancelledNotification(JSONRPCNotification):
    """CancelledNotification model."""

    method: Literal["notifications/cancelled"] = "notifications/cancelled"
    params: CancelledNotificationParams


class PaginatedRequestParams(RequestParams):
    """PaginatedRequestParams model."""

    cursor: Cursor | None = None


class PaginatedRequest(JSONRPCRequest):
    """PaginatedRequest model."""

    params: PaginatedRequestParams | None = None


class PaginatedResult(Result):
    """PaginatedResult model."""

    nextCursor: Cursor | None = None


class EmptyResult(Result):
    """EmptyResult model."""


class CompleteRequestParamsArgument(BaseModel):
    """CompleteRequestParamsArgument model."""

    name: str
    value: str


class CompleteRequestParams(RequestParams):
    """CompleteRequestParams model."""

    ref: PromptReference | ResourceReference
    argument: CompleteRequestParamsArgument


class CompleteRequest(JSONRPCRequest):
    """CompleteRequest model."""

    method: Literal["completion/complete"] = "completion/complete"
    params: CompleteRequestParams


class CompleteResultCompletion(BaseModel):
    """CompleteResultCompletion model."""

    values: list[str]
    total: int | None = None
    hasMore: bool | None = None


class CompleteResult(Result):
    """CompleteResult model."""

    completion: CompleteResultCompletion


class CreateMessageRequestParams(RequestParams):
    """CreateMessageRequestParams model."""

    messages: list[SamplingMessage]
    maxTokens: int
    systemPrompt: str | None = None
    includeContext: Literal["none", "thisServer"] | None = None
    temperature: float | None = None
    stopSequences: list[str] | None = None
    metadata: dict[str, Any] | None = None
    modelPreferences: ModelPreferences | None = None


class CreateMessageRequest(JSONRPCRequest):
    """CreateMessageRequest model."""

    method: Literal["messages/create"] = "messages/create"
    params: CreateMessageRequestParams


class CreateMessageResult(Result):
    """CreateMessageResult model."""

    role: Role
    content: TextContent | ImageContent
    model: str
    stopReason: Literal["endTurn", "stopSequence", "maxTokens"] | str | None = None


class GetPromptRequestParams(RequestParams):
    """GetPromptRequestParams model."""

    name: str
    arguments: dict[str, str] | None = None


class GetPromptRequest(JSONRPCRequest):
    """GetPromptRequest model."""

    method: Literal["prompts/get"] = "prompts/get"
    params: GetPromptRequestParams


class GetPromptResult(Result):
    """GetPromptResult model."""

    description: str | None = None
    messages: list[PromptMessage]


class ListPromptsRequest(PaginatedRequest):
    """ListPromptsRequest model."""

    method: Literal["prompts/list"] = "prompts/list"


class ListPromptsResult(PaginatedResult):
    """ListPromptsResult model."""

    prompts: list[Prompt]


class ListResourceTemplatesRequest(PaginatedRequest):
    """ListResourceTemplatesRequest model."""

    method: Literal["resources/templates/list"] = "resources/templates/list"


class ListResourceTemplatesResult(PaginatedResult):
    """ListResourceTemplatesResult model."""

    resourceTemplates: list[ResourceTemplate]


class ListResourcesRequest(PaginatedRequest):
    """ListResourcesRequest model."""

    method: Literal["resources/list"] = "resources/list"


class ListResourcesResult(PaginatedResult):
    """ListResourcesResult model."""

    resources: list[Resource]


class ListRootsRequest(JSONRPCRequest):
    """ListRootsRequest model."""

    method: Literal["roots/list"] = "roots/list"


class ListRootsResult(Result):
    """ListRootsResult model."""

    roots: list[Root]


class ListToolsRequest(PaginatedRequest):
    """ListToolsRequest model."""

    method: Literal["tools/list"] = "tools/list"


class ListToolsResult(PaginatedResult):
    """ListToolsResult model."""

    tools: list[Tool]


class LoggingMessageNotificationParams(NotificationParams):
    """LoggingMessageNotificationParams model."""

    level: LoggingLevel
    logger: str | None = None
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
    total: float | None = None


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

    contents: list[ResourceContents]


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
