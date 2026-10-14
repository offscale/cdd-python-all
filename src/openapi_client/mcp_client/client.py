"""Client abstractions for invoking remote MCP commands."""

from __future__ import annotations

import json
from typing import Any

from .models import (
    CallToolRequest,
    CallToolRequestParams,
    CancelledNotification,
    CancelledNotificationParams,
    ClientCapabilities,
    CompleteRequest,
    CompleteRequestParams,
    CompleteRequestParamsArgument,
    CreateMessageRequest,
    CreateMessageRequestParams,
    Cursor,
    GetPromptRequest,
    GetPromptRequestParams,
    Implementation,
    InitializedNotification,
    InitializedNotificationParams,
    InitializeRequest,
    InitializeRequestParams,
    ListPromptsRequest,
    ListResourcesRequest,
    ListResourceTemplatesRequest,
    ListRootsRequest,
    ListToolsRequest,
    LoggingLevel,
    LoggingMessageNotification,
    LoggingMessageNotificationParams,
    PaginatedRequest,
    PaginatedRequestParams,
    PingRequest,
    ProgressNotification,
    ProgressNotificationParams,
    ProgressToken,
    PromptListChangedNotification,
    PromptReference,
    ReadResourceRequest,
    ReadResourceRequestParams,
    RequestId,
    ResourceListChangedNotification,
    ResourceReference,
    ResourceUpdatedNotification,
    ResourceUpdatedNotificationParams,
    RootsListChangedNotification,
    SamplingMessage,
    SetLevelRequest,
    SetLevelRequestParams,
    SubscribeRequest,
    SubscribeRequestParams,
    ToolListChangedNotification,
    UnsubscribeRequest,
    UnsubscribeRequestParams,
)


class MCPClient:
    """A generic abstraction for making MCP JSON-RPC requests."""

    def __init__(self) -> None:
        """Initialize the client state."""
        self._request_id: int = 0
        self._pending_requests: dict[int, str] = {}
        self._resolved_responses: dict[int, dict[str, Any]] = {}

    def _next_id(self) -> int:
        """Get the next internal request ID.

        Returns:
            The incremented integer request ID.
        """
        self._request_id += 1
        return self._request_id

    def track_request(self, req: dict[str, Any]) -> None:
        """Track a request by its ID for later resolution.

        Args:
            req: The JSON-RPC request dictionary containing `id` and `method`.
        """
        req_id = req.get("id")
        if req_id is not None:
            self._pending_requests[req_id] = req.get("method", "unknown")

    def resolve_response(self, response: dict[str, Any]) -> None:
        """Resolve a response to a pending request using its ID.

        Args:
            response: The incoming JSON-RPC response dictionary.
        """
        req_id = response.get("id")
        if req_id is not None and req_id in self._pending_requests:
            self._resolved_responses[req_id] = response
            del self._pending_requests[req_id]

    def build_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Build a JSON-RPC 2.0 request dictionary.

        Args:
            method: The JSON-RPC method name.
            params: The parameters dictionary.

        Returns:
            The constructed JSON-RPC 2.0 request dictionary.
        """
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._next_id(),
        }

    def parse_response(self, payload: str) -> dict[str, Any]:
        """Parse an incoming JSON-RPC 2.0 response.

        Args:
            payload: Raw JSON string response.

        Returns:
            The decoded JSON dictionary.
        """
        data: dict[str, Any] = json.loads(payload)
        return data

    def build_call_tool_request(
        self, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a CallToolRequest payload.

        Args:
            name: The tool name to call.
            arguments: Tool arguments dictionary.

        Returns:
            The serialized CallToolRequest dictionary.
        """
        req = CallToolRequest(
            id=RequestId(self._next_id()),
            params=CallToolRequestParams(name=name, arguments=arguments),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_initialize_request(self) -> dict[str, Any]:
        """Build an InitializeRequest payload.

        Returns:
            The serialized InitializeRequest dictionary.
        """
        req = InitializeRequest(
            id=RequestId(self._next_id()),
            params=InitializeRequestParams(
                protocolVersion="2024-11-05",
                capabilities=ClientCapabilities(),
                clientInfo=Implementation(name="cdd-client", version="1.0.0"),
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_notification(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Build a generic ClientNotification payload.

        Args:
            method: The notification method name.
            params: Notification parameters dictionary.

        Returns:
            The constructed JSON-RPC 2.0 notification dictionary.
        """
        return {"jsonrpc": "2.0", "method": method, "params": params}

    def build_initialized_notification(self) -> dict[str, Any]:
        """Build an InitializedNotification payload.

        Returns:
            The serialized InitializedNotification dictionary.
        """
        req = InitializedNotification(
            method="notifications/initialized", params=InitializedNotificationParams()
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_cancelled_notification(
        self, request_id: int, reason: str | None = None
    ) -> dict[str, Any]:
        """Build a CancelledNotification payload.

        Args:
            request_id: The ID of the request to cancel.
            reason: Optional cancellation reason.

        Returns:
            The serialized CancelledNotification dictionary.
        """
        req = CancelledNotification(
            method="notifications/cancelled",
            params=CancelledNotificationParams(
                requestId=RequestId(request_id), reason=reason
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_progress_notification(
        self, progress_token: str, progress: float, total: float | None = None
    ) -> dict[str, Any]:
        """Build a ProgressNotification payload.

        Args:
            progress_token: The progress token identifier.
            progress: Current progress value.
            total: Optional total progress target.

        Returns:
            The serialized ProgressNotification dictionary.
        """
        req = ProgressNotification(
            method="notifications/progress",
            params=ProgressNotificationParams(
                progressToken=ProgressToken(progress_token),
                progress=progress,
                total=total,
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_roots_list_changed_notification(self) -> dict[str, Any]:
        """Build a RootsListChangedNotification payload.

        Returns:
            The serialized RootsListChangedNotification dictionary.
        """
        req = RootsListChangedNotification(method="notifications/roots/list_changed")
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_logging_message_notification(
        self, level: str, logger: str, data: Any
    ) -> dict[str, Any]:
        """Build a LoggingMessageNotification payload.

        Args:
            level: Logging severity level.
            logger: Logger name.
            data: Log message data payload.

        Returns:
            The serialized LoggingMessageNotification dictionary.
        """
        req = LoggingMessageNotification(
            method="notifications/message",
            params=LoggingMessageNotificationParams(
                level=LoggingLevel(level), logger=logger, data=data
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_resource_updated_notification(self, uri: str) -> dict[str, Any]:
        """Build a ResourceUpdatedNotification payload.

        Args:
            uri: The updated resource URI.

        Returns:
            The serialized ResourceUpdatedNotification dictionary.
        """
        req = ResourceUpdatedNotification(
            method="notifications/resources/updated",
            params=ResourceUpdatedNotificationParams(uri=uri),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_resource_list_changed_notification(self) -> dict[str, Any]:
        """Build a ResourceListChangedNotification payload.

        Returns:
            The serialized ResourceListChangedNotification dictionary.
        """
        req = ResourceListChangedNotification(
            method="notifications/resources/list_changed"
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_tool_list_changed_notification(self) -> dict[str, Any]:
        """Build a ToolListChangedNotification payload.

        Returns:
            The serialized ToolListChangedNotification dictionary.
        """
        req = ToolListChangedNotification(method="notifications/tools/list_changed")
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_prompt_list_changed_notification(self) -> dict[str, Any]:
        """Build a PromptListChangedNotification payload.

        Returns:
            The serialized PromptListChangedNotification dictionary.
        """
        req = PromptListChangedNotification(method="notifications/prompts/list_changed")
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_subscribe_request(self, uri: str) -> dict[str, Any]:
        """Build a SubscribeRequest payload.

        Args:
            uri: The resource URI to subscribe to.

        Returns:
            The serialized SubscribeRequest dictionary.
        """
        req = SubscribeRequest(
            id=RequestId(self._next_id()), params=SubscribeRequestParams(uri=uri)
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_list_prompts_request(self, cursor: str | None = None) -> dict[str, Any]:
        """Build a ListPromptsRequest payload.

        Args:
            cursor: Optional pagination cursor.

        Returns:
            The serialized ListPromptsRequest dictionary.
        """
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = ListPromptsRequest(id=RequestId(self._next_id()), params=params)
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_get_prompt_request(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Build a GetPromptRequest payload.

        Args:
            name: Prompt name.
            arguments: Optional prompt arguments mapping.

        Returns:
            The serialized GetPromptRequest dictionary.
        """
        req = GetPromptRequest(
            id=RequestId(self._next_id()),
            params=GetPromptRequestParams(name=name, arguments=arguments),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_list_resource_templates_request(
        self, cursor: str | None = None
    ) -> dict[str, Any]:
        """Build a ListResourceTemplatesRequest payload.

        Args:
            cursor: Optional pagination cursor.

        Returns:
            The serialized ListResourceTemplatesRequest dictionary.
        """
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = ListResourceTemplatesRequest(id=RequestId(self._next_id()), params=params)
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_list_resources_request(self, cursor: str | None = None) -> dict[str, Any]:
        """Build a ListResourcesRequest payload.

        Args:
            cursor: Optional pagination cursor.

        Returns:
            The serialized ListResourcesRequest dictionary.
        """
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = ListResourcesRequest(id=RequestId(self._next_id()), params=params)
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_read_resource_request(self, uri: str) -> dict[str, Any]:
        """Build a ReadResourceRequest payload.

        Args:
            uri: Resource URI to read.

        Returns:
            The serialized ReadResourceRequest dictionary.
        """
        req = ReadResourceRequest(
            id=RequestId(self._next_id()), params=ReadResourceRequestParams(uri=uri)
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_list_tools_request(self, cursor: str | None = None) -> dict[str, Any]:
        """Build a ListToolsRequest payload.

        Args:
            cursor: Optional pagination cursor.

        Returns:
            The serialized ListToolsRequest dictionary.
        """
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = ListToolsRequest(id=RequestId(self._next_id()), params=params)
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_unsubscribe_request(self, uri: str) -> dict[str, Any]:
        """Build an UnsubscribeRequest payload.

        Args:
            uri: Resource URI to unsubscribe from.

        Returns:
            The serialized UnsubscribeRequest dictionary.
        """
        req = UnsubscribeRequest(
            id=RequestId(self._next_id()), params=UnsubscribeRequestParams(uri=uri)
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_paginated_request(
        self, method: str, cursor: str | None = None
    ) -> dict[str, Any]:
        """Build a generic PaginatedRequest.

        Args:
            method: The JSON-RPC method name.
            cursor: Optional pagination cursor.

        Returns:
            The serialized PaginatedRequest dictionary.
        """
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = PaginatedRequest(
            method=method, id=RequestId(self._next_id()), params=params
        )
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_create_message_request(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """Build a CreateMessageRequest payload.

        Args:
            messages: List of sampling message dictionaries.
            system_prompt: Optional system prompt string.
            max_tokens: Maximum tokens to sample.

        Returns:
            The serialized CreateMessageRequest dictionary.
        """
        parsed_messages = [SamplingMessage.model_validate(m) for m in messages]
        req = CreateMessageRequest(
            id=RequestId(self._next_id()),
            params=CreateMessageRequestParams(
                messages=parsed_messages,
                maxTokens=max_tokens,
                systemPrompt=system_prompt,
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_complete_request(
        self, ref: dict[str, Any], argument: dict[str, str]
    ) -> dict[str, Any]:
        """Build a CompleteRequest payload.

        Args:
            ref: Reference dictionary (`ref/prompt` or `ref/resource`).
            argument: Argument name and value mapping.

        Returns:
            The serialized CompleteRequest dictionary.
        """
        r_type = ref.get("type", "")
        ref_obj: PromptReference | ResourceReference
        if r_type == "ref/prompt":
            ref_obj = PromptReference.model_validate(ref)
        else:
            ref_obj = ResourceReference.model_validate(ref)
        req = CompleteRequest(
            id=RequestId(self._next_id()),
            params=CompleteRequestParams(
                ref=ref_obj,
                argument=CompleteRequestParamsArgument.model_validate(argument),
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_list_roots_request(self) -> dict[str, Any]:
        """Build a ListRootsRequest payload.

        Returns:
            The serialized ListRootsRequest dictionary.
        """
        req = ListRootsRequest(id=RequestId(self._next_id()))
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_set_level_request(self, level: str) -> dict[str, Any]:
        """Build a SetLevelRequest payload.

        Args:
            level: Logging level name.

        Returns:
            The serialized SetLevelRequest dictionary.
        """
        req = SetLevelRequest(
            id=RequestId(self._next_id()),
            params=SetLevelRequestParams(level=LoggingLevel(level)),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_ping_request(self) -> dict[str, Any]:
        """Build a PingRequest payload.

        Returns:
            The serialized PingRequest dictionary.
        """
        req = PingRequest(id=RequestId(self._next_id()))
        return req.model_dump(exclude_none=True, by_alias=True)

    def parse_create_message_result(self, payload: str) -> dict[str, Any]:
        """Parse a CreateMessageResult payload.

        Args:
            payload: Raw JSON response string.

        Returns:
            The result payload dictionary.
        """
        return self.parse_client_result(payload)

    def parse_paginated_result(self, payload: str) -> tuple[dict[str, Any], str | None]:
        """Parse a generic PaginatedResult returning `(result, nextCursor)`.

        Args:
            payload: Raw JSON response string.

        Returns:
            A tuple of `(result_dict, next_cursor)`.
        """
        result = self.parse_client_result(payload)
        return result, result.get("nextCursor")

    def parse_client_result(self, payload: str) -> dict[str, Any]:
        """Parse a ClientResult or JSONRPCResponse, raising if an error occurred.

        Args:
            payload: Raw JSON response string.

        Returns:
            The `result` dictionary from the JSON-RPC response.

        Raises:
            RuntimeError: If the JSON-RPC response contains an `error` object.
        """
        data = self.parse_response(payload)

        if "error" in data:
            error_data = data["error"]
            code = error_data.get("code")
            msg = error_data.get("message", "Unknown error")
            raise RuntimeError(f"MCP JSON-RPC Error {code}: {msg}")

        res: dict[str, Any] = data.get("result", {})
        return res
