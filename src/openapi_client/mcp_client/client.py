"""Client abstractions for invoking remote MCP commands."""

import json
from typing import Dict, Any, List

from .models import (
    RequestId,
    CallToolRequest,
    CallToolRequestParams,
    InitializeRequest,
    InitializeRequestParams,
    ClientCapabilities,
    Implementation,
    SubscribeRequest,
    SubscribeRequestParams,
    ListPromptsRequest,
    ListResourceTemplatesRequest,
    GetPromptRequest,
    GetPromptRequestParams,
    ListResourcesRequest,
    ReadResourceRequest,
    ReadResourceRequestParams,
    ListToolsRequest,
    UnsubscribeRequest,
    UnsubscribeRequestParams,
    PaginatedRequest,
    PaginatedRequestParams,
    CreateMessageRequest,
    CreateMessageRequestParams,
    CompleteRequest,
    CompleteRequestParams,
    CompleteRequestParamsArgument,
    ListRootsRequest,
    SetLevelRequest,
    SetLevelRequestParams,
    PingRequest,
    Cursor,
    LoggingLevel,
    PromptReference,
    ResourceReference,
    InitializedNotification,
    InitializedNotificationParams,
    CancelledNotification,
    CancelledNotificationParams,
    ProgressNotification,
    ProgressNotificationParams,
    RootsListChangedNotification,
    LoggingMessageNotification,
    LoggingMessageNotificationParams,
    ResourceUpdatedNotification,
    ResourceUpdatedNotificationParams,
    ResourceListChangedNotification,
    ToolListChangedNotification,
    PromptListChangedNotification,
)


class MCPClient:
    """A generic abstraction for making MCP JSON-RPC requests."""

    def __init__(self):
        """Initialize the client state."""
        self._request_id = 0
        self._pending_requests: Dict[int, str] = {}
        self._resolved_responses: Dict[int, Dict[str, Any]] = {}

    def _next_id(self) -> int:
        """Get the next internal request id."""
        self._request_id += 1
        return self._request_id

    def track_request(self, req: Dict[str, Any]) -> None:
        """Track a request by its ID for later resolution."""
        req_id = req.get("id")
        if req_id is not None:
            self._pending_requests[req_id] = req.get("method", "unknown")

    def resolve_response(self, response: Dict[str, Any]) -> None:
        """Resolve a response to a pending request using its ID."""
        req_id = response.get("id")
        if req_id is not None and req_id in self._pending_requests:
            self._resolved_responses[req_id] = response
            del self._pending_requests[req_id]

    def build_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a JSON-RPC 2.0 request dictionary."""
        # Generic fallback
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._next_id(),
        }

    def parse_response(self, payload: str) -> Dict[str, Any]:
        """Parse an incoming JSON-RPC 2.0 response."""
        data = json.loads(payload)
        return data

    def build_call_tool_request(
        self, name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build a CallToolRequest payload."""
        req = CallToolRequest(
            id=RequestId(self._next_id()),
            params=CallToolRequestParams(name=name, arguments=arguments),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_initialize_request(self) -> Dict[str, Any]:
        """Build an InitializeRequest payload."""
        req = InitializeRequest(
            id=RequestId(self._next_id()),
            params=InitializeRequestParams(
                protocolVersion="2024-11-05",
                capabilities=ClientCapabilities(),
                clientInfo=Implementation(name="cdd-client", version="1.0.0"),
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_notification(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a generic ClientNotification payload."""
        return {"jsonrpc": "2.0", "method": method, "params": params}

    def build_initialized_notification(self) -> Dict[str, Any]:
        """Build an InitializedNotification payload."""
        req = InitializedNotification(
            method="notifications/initialized", params=InitializedNotificationParams()
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_cancelled_notification(
        self, request_id: int, reason: str = None
    ) -> Dict[str, Any]:
        """Build a CancelledNotification payload."""
        req = CancelledNotification(
            method="notifications/cancelled",
            params=CancelledNotificationParams(
                requestId=RequestId(request_id), reason=reason
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_progress_notification(
        self, progress_token: str, progress: float, total: float = None
    ) -> Dict[str, Any]:
        """Build a ProgressNotification payload."""
        req = ProgressNotification(
            method="notifications/progress",
            params=ProgressNotificationParams(
                progressToken=progress_token, progress=progress, total=total
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_roots_list_changed_notification(self) -> Dict[str, Any]:
        """Build a RootsListChangedNotification payload."""
        req = RootsListChangedNotification(method="notifications/roots/list_changed")
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_logging_message_notification(
        self, level: str, logger: str, data: Any
    ) -> Dict[str, Any]:
        """Build a LoggingMessageNotification payload."""
        req = LoggingMessageNotification(
            method="notifications/message",
            params=LoggingMessageNotificationParams(
                level=LoggingLevel(level), logger=logger, data=data
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_resource_updated_notification(self, uri: str) -> Dict[str, Any]:
        """Build a ResourceUpdatedNotification payload."""
        req = ResourceUpdatedNotification(
            method="notifications/resources/updated",
            params=ResourceUpdatedNotificationParams(uri=uri),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_resource_list_changed_notification(self) -> Dict[str, Any]:
        """Build a ResourceListChangedNotification payload."""
        req = ResourceListChangedNotification(
            method="notifications/resources/list_changed"
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_tool_list_changed_notification(self) -> Dict[str, Any]:
        """Build a ToolListChangedNotification payload."""
        req = ToolListChangedNotification(method="notifications/tools/list_changed")
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_prompt_list_changed_notification(self) -> Dict[str, Any]:
        """Build a PromptListChangedNotification payload."""
        req = PromptListChangedNotification(method="notifications/prompts/list_changed")
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_subscribe_request(self, uri: str) -> Dict[str, Any]:
        """Build a SubscribeRequest payload."""
        req = SubscribeRequest(
            id=RequestId(self._next_id()), params=SubscribeRequestParams(uri=uri)
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_list_prompts_request(self, cursor: str = None) -> Dict[str, Any]:
        """Build a ListPromptsRequest payload."""
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = ListPromptsRequest(id=RequestId(self._next_id()), params=params)
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_get_prompt_request(
        self, name: str, arguments: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Build a GetPromptRequest payload."""
        req = GetPromptRequest(
            id=RequestId(self._next_id()),
            params=GetPromptRequestParams(name=name, arguments=arguments),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_list_resource_templates_request(
        self, cursor: str = None
    ) -> Dict[str, Any]:
        """Build a ListResourceTemplatesRequest payload."""
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = ListResourceTemplatesRequest(id=RequestId(self._next_id()), params=params)
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_list_resources_request(self, cursor: str = None) -> Dict[str, Any]:
        """Build a ListResourcesRequest payload."""
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = ListResourcesRequest(id=RequestId(self._next_id()), params=params)
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_read_resource_request(self, uri: str) -> Dict[str, Any]:
        """Build a ReadResourceRequest payload."""
        req = ReadResourceRequest(
            id=RequestId(self._next_id()), params=ReadResourceRequestParams(uri=uri)
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_list_tools_request(self, cursor: str = None) -> Dict[str, Any]:
        """Build a ListToolsRequest payload."""
        params = PaginatedRequestParams()
        if cursor is not None:
            params.cursor = Cursor(cursor)
        req = ListToolsRequest(id=RequestId(self._next_id()), params=params)
        out = req.model_dump(exclude_none=True, by_alias=True)
        if cursor is None and "params" in out and not out["params"]:
            del out["params"]
        return out

    def build_unsubscribe_request(self, uri: str) -> Dict[str, Any]:
        """Build an UnsubscribeRequest payload."""
        req = UnsubscribeRequest(
            id=RequestId(self._next_id()), params=UnsubscribeRequestParams(uri=uri)
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_paginated_request(
        self, method: str, cursor: str = None
    ) -> Dict[str, Any]:
        """Build a generic PaginatedRequest."""
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
        messages: List[Dict[str, Any]],
        system_prompt: str = None,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Build a CreateMessageRequest payload."""
        req = CreateMessageRequest(
            id=RequestId(self._next_id()),
            params=CreateMessageRequestParams(
                messages=messages,  # type: ignore
                maxTokens=max_tokens,
                systemPrompt=system_prompt,
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_complete_request(
        self, ref: Dict[str, Any], argument: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build a CompleteRequest payload."""
        r_type = ref.get("type", "")
        if r_type == "ref/prompt":
            ref_obj = PromptReference(**ref)  # type: ignore
        else:
            ref_obj = ResourceReference(**ref)  # type: ignore
        req = CompleteRequest(
            id=RequestId(self._next_id()),
            params=CompleteRequestParams(
                ref=ref_obj, argument=CompleteRequestParamsArgument(**argument)
            ),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_list_roots_request(self) -> Dict[str, Any]:
        """Build a ListRootsRequest payload."""
        req = ListRootsRequest(id=RequestId(self._next_id()))
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_set_level_request(self, level: str) -> Dict[str, Any]:
        """Build a SetLevelRequest payload."""
        req = SetLevelRequest(
            id=RequestId(self._next_id()),
            params=SetLevelRequestParams(level=LoggingLevel(level)),
        )
        return req.model_dump(exclude_none=True, by_alias=True)

    def build_ping_request(self) -> Dict[str, Any]:
        """Build a PingRequest payload."""
        req = PingRequest(id=RequestId(self._next_id()))
        return req.model_dump(exclude_none=True, by_alias=True)

    def parse_create_message_result(self, payload: str) -> Dict[str, Any]:
        """Parse a CreateMessageResult payload."""
        return self.parse_client_result(payload)

    def parse_paginated_result(self, payload: str) -> tuple[Dict[str, Any], str]:
        """Parse a generic PaginatedResult returning (result, nextCursor)."""
        result = self.parse_client_result(payload)
        return result, result.get("nextCursor")

    def parse_client_result(self, payload: str) -> Dict[str, Any]:
        """Parse a ClientResult or JSONRPCResponse, raising if an error occurred."""
        data = self.parse_response(payload)

        if "error" in data:
            error_data = data["error"]
            code = error_data.get("code")
            msg = error_data.get("message", "Unknown error")
            raise RuntimeError(f"MCP JSON-RPC Error {code}: {msg}")

        return data.get("result", {})
