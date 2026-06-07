"""Tests for MCP Client models."""

from src.openapi_client.mcp_client.models import (
    RequestId,
    ProgressToken,
    Cursor,
    Role,
    LoggingLevel,
    Annotated,
    BlobResourceContents,
    TextResourceContents,
    ResourceContents,
    ImageContent,
    TextContent,
    EmbeddedResource,
    ModelHint,
    ModelPreferences,
    PromptArgument,
    Prompt,
    PromptMessage,
    SamplingMessage,
    PromptReference,
    ResourceReference,
    Resource,
    ResourceTemplate,
    Root,
    ToolInputSchema,
    Tool,
    Implementation,
    ClientCapabilities,
    ServerCapabilities,
    RequestMeta,
    RequestParams,
    Request,
    JSONRPCMessage,
    JSONRPCRequest,
    NotificationParams,
    Notification,
    JSONRPCNotification,
    ResultMeta,
    Result,
    JSONRPCErrorError,
    JSONRPCError,
    JSONRPCResponse,
    InitializeRequestParams,
    InitializeRequest,
    InitializeResult,
    InitializedNotificationParams,
    InitializedNotification,
    CallToolRequestParams,
    CallToolRequest,
    CallToolResult,
    CancelledNotificationParams,
    CancelledNotification,
    PaginatedRequestParams,
    PaginatedRequest,
    PaginatedResult,
    EmptyResult,
    CompleteRequestParamsArgument,
    CompleteRequestParams,
    CompleteRequest,
    CompleteResultCompletion,
    CompleteResult,
    CreateMessageRequestParams,
    CreateMessageRequest,
    CreateMessageResult,
    GetPromptRequestParams,
    GetPromptRequest,
    GetPromptResult,
    ListPromptsRequest,
    ListPromptsResult,
    ListResourceTemplatesRequest,
    ListResourceTemplatesResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListRootsRequest,
    ListRootsResult,
    ListToolsRequest,
    ListToolsResult,
    LoggingMessageNotificationParams,
    LoggingMessageNotification,
    PingRequest,
    ProgressNotificationParams,
    ProgressNotification,
    PromptListChangedNotification,
    ReadResourceRequestParams,
    ReadResourceRequest,
    ReadResourceResult,
    ResourceListChangedNotification,
    ResourceUpdatedNotificationParams,
    ResourceUpdatedNotification,
    RootsListChangedNotification,
    SetLevelRequestParams,
    SetLevelRequest,
    SubscribeRequestParams,
    SubscribeRequest,
    ToolListChangedNotification,
    UnsubscribeRequestParams,
    UnsubscribeRequest,
    ErrorCode,
)


def test_models_instantiation():
    """Test test_models_instantiation."""
    req = RequestId("123")
    assert req.root == "123"

    pt = ProgressToken(1)
    assert pt.root == 1

    cursor = Cursor("cur")
    assert cursor.root == "cur"

    role = Role("user")
    assert role.root == "user"

    level = LoggingLevel("debug")
    assert level.root == "debug"

    annotated = Annotated(audience=["public"], priority=0.5)
    assert annotated.audience == ["public"]

    blob = BlobResourceContents(uri="file://foo", blob="base64")
    assert blob.uri == "file://foo"

    text_res = TextResourceContents(uri="file://bar", text="hello")
    assert text_res.text == "hello"

    res_contents = ResourceContents(text_res)
    assert res_contents.root == text_res

    img = ImageContent(data="base64", mimeType="image/png")
    assert img.type == "image"

    text = TextContent(text="hello")
    assert text.type == "text"

    emb = EmbeddedResource(resource=text_res)
    assert emb.type == "resource"

    hint = ModelHint(name="claude-3")
    assert hint.name == "claude-3"

    prefs = ModelPreferences(hints=[hint], costPriority=1.0)
    assert prefs.costPriority == 1.0

    arg = PromptArgument(name="test", description="desc", required=True)
    prompt = Prompt(name="p", arguments=[arg])
    assert prompt.name == "p"

    msg = PromptMessage(role=Role("user"), content=text)
    assert msg.role.root == "user"

    smsg = SamplingMessage(role=Role("assistant"), content=img)
    assert smsg.content.type == "image"

    pref = PromptReference(name="p")
    assert pref.type == "ref/prompt"

    rref = ResourceReference(uri="schema://p")
    assert rref.type == "ref/resource"

    res = Resource(uri="file://", name="f")
    assert res.name == "f"

    rest = ResourceTemplate(uriTemplate="file://{p}", name="f")
    assert rest.name == "f"

    root = Root(uri="file://")
    assert root.uri == "file://"

    tool_input = ToolInputSchema()
    tool = Tool(name="t", inputSchema=tool_input)
    assert tool.name == "t"

    impl = Implementation(name="i", version="1")
    assert impl.name == "i"

    ccaps = ClientCapabilities()
    scaps = ServerCapabilities()
    assert ccaps.experimental is None
    assert scaps.logging is None

    rmeta = RequestMeta(progressToken=ProgressToken(1))
    rparams = RequestParams(_meta=rmeta)
    assert rparams.meta.progressToken.root == 1

    req_base = Request(method="m", params=rparams)
    assert req_base.method == "m"

    jmsg = JSONRPCMessage()
    assert jmsg.jsonrpc == "2.0"

    jreq = JSONRPCRequest(method="m", id=RequestId(1))
    assert jreq.id.root == 1

    nparams = NotificationParams(_meta={"test": True})
    n_base = Notification(method="n", params=nparams)
    assert n_base.method == "n"

    jnotif = JSONRPCNotification(method="n")
    assert jnotif.jsonrpc == "2.0"

    _ = ResultMeta()
    result = Result(_meta={"test": True})
    assert result.meta == {"test": True}

    err_err = JSONRPCErrorError(code=1, message="e")
    jerr = JSONRPCError(id=RequestId(1), error=err_err)
    assert jerr.error.code == 1

    jres = JSONRPCResponse(id=RequestId(1), result=result)
    assert jres.id.root == 1

    init_params = InitializeRequestParams(
        protocolVersion="1.0", capabilities=ccaps, clientInfo=impl
    )
    init_req = InitializeRequest(params=init_params, id=RequestId(1))
    assert init_req.method == "initialize"

    init_res = InitializeResult(
        protocolVersion="1.0", capabilities=scaps, serverInfo=impl
    )
    assert init_res.protocolVersion == "1.0"

    initd_params = InitializedNotificationParams()
    initd_notif = InitializedNotification(params=initd_params)
    assert initd_notif.method == "notifications/initialized"

    ct_params = CallToolRequestParams(name="t", arguments={"a": 1})
    ct_req = CallToolRequest(params=ct_params, id=RequestId(1))
    assert ct_req.method == "tools/call"

    ct_res = CallToolResult(content=[text])
    assert ct_res.content[0] == text

    canc_params = CancelledNotificationParams(requestId=RequestId(1))
    canc_notif = CancelledNotification(params=canc_params)
    assert canc_notif.method == "notifications/cancelled"

    pag_params = PaginatedRequestParams(cursor=Cursor("c"))
    pag_req = PaginatedRequest(method="test", params=pag_params, id=RequestId(1))
    assert pag_req.params.cursor.root == "c"

    pag_res = PaginatedResult(nextCursor=Cursor("n"))
    assert pag_res.nextCursor.root == "n"

    emp_res = EmptyResult()
    assert emp_res.meta is None

    comp_arg = CompleteRequestParamsArgument(name="a", value="v")
    comp_params = CompleteRequestParams(ref=pref, argument=comp_arg)
    comp_req = CompleteRequest(params=comp_params, id=RequestId(1))
    assert comp_req.method == "completion/complete"

    comp_compl = CompleteResultCompletion(values=["v"])
    comp_res = CompleteResult(completion=comp_compl)
    assert comp_res.completion.values == ["v"]

    cm_params = CreateMessageRequestParams(messages=[smsg], maxTokens=100)
    cm_req = CreateMessageRequest(params=cm_params, id=RequestId(1))
    assert cm_req.method == "messages/create"

    cm_res = CreateMessageResult(role=Role("user"), content=text, model="m")
    assert cm_res.role.root == "user"

    gp_params = GetPromptRequestParams(name="n")
    gp_req = GetPromptRequest(params=gp_params, id=RequestId(1))
    assert gp_req.method == "prompts/get"

    gp_res = GetPromptResult(messages=[msg])
    assert gp_res.messages[0] == msg

    lp_req = ListPromptsRequest(id=RequestId(1))
    assert lp_req.method == "prompts/list"

    lp_res = ListPromptsResult(prompts=[prompt])
    assert lp_res.prompts[0] == prompt

    lrt_req = ListResourceTemplatesRequest(id=RequestId(1))
    assert lrt_req.method == "resources/templates/list"

    lrt_res = ListResourceTemplatesResult(resourceTemplates=[rest])
    assert lrt_res.resourceTemplates[0] == rest

    lr_req = ListResourcesRequest(id=RequestId(1))
    assert lr_req.method == "resources/list"

    lr_res = ListResourcesResult(resources=[res])
    assert lr_res.resources[0] == res

    lroot_req = ListRootsRequest(id=RequestId(1))
    assert lroot_req.method == "roots/list"

    lroot_res = ListRootsResult(roots=[root])
    assert lroot_res.roots[0] == root

    lt_req = ListToolsRequest(id=RequestId(1))
    assert lt_req.method == "tools/list"

    lt_res = ListToolsResult(tools=[tool])
    assert lt_res.tools[0] == tool

    lmn_params = LoggingMessageNotificationParams(level=LoggingLevel("info"), data="d")
    lmn_notif = LoggingMessageNotification(params=lmn_params)
    assert lmn_notif.method == "notifications/message"

    ping_req = PingRequest(id=RequestId(1))
    assert ping_req.method == "ping"

    pn_params = ProgressNotificationParams(progressToken=ProgressToken(1), progress=0.5)
    pn_notif = ProgressNotification(params=pn_params)
    assert pn_notif.method == "notifications/progress"

    plcn_notif = PromptListChangedNotification()
    assert plcn_notif.method == "notifications/prompts/list_changed"

    rr_params = ReadResourceRequestParams(uri="u")
    rr_req = ReadResourceRequest(params=rr_params, id=RequestId(1))
    assert rr_req.method == "resources/read"

    rr_res = ReadResourceResult(contents=[res_contents])
    assert rr_res.contents[0] == res_contents

    rlcn_notif = ResourceListChangedNotification()
    assert rlcn_notif.method == "notifications/resources/list_changed"

    run_params = ResourceUpdatedNotificationParams(uri="u")
    run_notif = ResourceUpdatedNotification(params=run_params)
    assert run_notif.method == "notifications/resources/updated"

    roots_lcn_notif = RootsListChangedNotification()
    assert roots_lcn_notif.method == "notifications/roots/list_changed"

    sl_params = SetLevelRequestParams(level=LoggingLevel("debug"))
    sl_req = SetLevelRequest(params=sl_params, id=RequestId(1))
    assert sl_req.method == "logging/setLevel"

    sub_params = SubscribeRequestParams(uri="u")
    sub_req = SubscribeRequest(params=sub_params, id=RequestId(1))
    assert sub_req.method == "resources/subscribe"

    tlcn_notif = ToolListChangedNotification()
    assert tlcn_notif.method == "notifications/tools/list_changed"

    unsub_params = UnsubscribeRequestParams(uri="u")
    unsub_req = UnsubscribeRequest(params=unsub_params, id=RequestId(1))
    assert unsub_req.method == "resources/unsubscribe"


def test_error_code_enum():
    """Test test_error_code_enum."""
    assert ErrorCode.PARSE_ERROR == -32700
    assert ErrorCode.INVALID_REQUEST == -32600
    assert ErrorCode.METHOD_NOT_FOUND == -32601
    assert ErrorCode.INVALID_PARAMS == -32602
    assert ErrorCode.INTERNAL_ERROR == -32603
