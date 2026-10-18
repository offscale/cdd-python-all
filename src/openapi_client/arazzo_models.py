"""Arazzo 1.1.0 Specification Pydantic models."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openapi_client.models import Reference, Schema

SourceType = Literal["openapi", "asyncapi", "arazzo"]
ParameterIn = Literal["path", "query", "querystring", "header", "cookie"]
SuccessActionType = Literal["end", "goto"]
FailureActionType = Literal["end", "retry", "goto"]
StepAction = Literal["send", "receive"]
CriterionTypeEnum = Literal["simple", "regex", "jsonpath", "xpath"]
SelectorDialect = Literal["jsonpath", "xpath", "jsonpointer"]

_SOURCE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


class ArazzoBase(BaseModel):
    """Base model for Arazzo 1.1.0 specification objects allowing `^x-` extensions."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class ArazzoInfo(ArazzoBase):
    """Arazzo Info Object providing metadata about the Arazzo workflow description."""

    title: str
    summary: str | None = None
    description: str | None = None
    version: str


class SourceDescription(ArazzoBase):
    """Arazzo Source Description Object linking to an external API or workflow specification."""

    name: str
    url: str
    type: SourceType | None = None

    @model_validator(mode="after")
    def validate_source_name(self) -> SourceDescription:
        r"""Validate that the source description name conforms to `^[A-Za-z0-9_\-]+$`.

        Returns:
            The validated SourceDescription instance.
        """
        if not _SOURCE_NAME_RE.match(self.name):
            raise ValueError(
                f"Invalid SourceDescription name {self.name!r}; must match ^[A-Za-z0-9_-]+$"
            )
        return self


class ReusableObject(ArazzoBase):
    """Arazzo Reusable Object referencing a shared object in the `$components` registry."""

    reference: str
    value: Any | None = None


class ExpressionTypeObject(ArazzoBase):
    """Arazzo Expression Type Object specifying a selector dialect and version."""

    type: SelectorDialect
    version: str


class CriterionObject(ArazzoBase):
    """Arazzo Criterion Object defining a condition and evaluation context for step assertions."""

    context: str | None = None
    condition: str
    type: CriterionTypeEnum | ExpressionTypeObject | None = "simple"


class SelectorObject(ArazzoBase):
    """Arazzo Selector Object for structured extraction of dynamic values from runtime context."""

    context: str
    selector: str
    type: SelectorDialect | ExpressionTypeObject | None = None


class ArazzoParameter(ArazzoBase):
    """Arazzo Parameter Object binding a parameter name, location, and dynamic/constant value."""

    name: str
    in_: ParameterIn | None = Field(default=None, alias="in")
    value: Any


class PayloadReplacement(ArazzoBase):
    """Arazzo Payload Replacement Object describing an in-place modification to a request payload."""

    target: str
    targetSelectorType: SelectorDialect | ExpressionTypeObject | None = None
    value: Any


class ArazzoRequestBody(ArazzoBase):
    """Arazzo Request Body Object representing a request payload and dynamic replacements."""

    contentType: str | None = None
    payload: Any | None = None
    replacements: list[PayloadReplacement] | None = None


class SuccessAction(ArazzoBase):
    """Arazzo Success Action Object specifying flow transitions (`end` or `goto`) on step success."""

    name: str
    type: SuccessActionType
    workflowId: str | None = None
    stepId: str | None = None
    parameters: list[ArazzoParameter | ReusableObject] | None = None
    criteria: list[CriterionObject] | None = None

    @model_validator(mode="after")
    def validate_target_exclusivity(self) -> SuccessAction:
        """Validate that `workflowId` and `stepId` are mutually exclusive.

        Returns:
            The validated SuccessAction instance.
        """
        if self.workflowId is not None and self.stepId is not None:
            raise ValueError(
                "SuccessAction cannot specify both 'workflowId' and 'stepId'"
            )
        return self


class FailureAction(ArazzoBase):
    """Arazzo Failure Action Object specifying recovery (`end`, `retry`, `goto`) on step failure."""

    name: str
    type: FailureActionType
    workflowId: str | None = None
    stepId: str | None = None
    parameters: list[ArazzoParameter | ReusableObject] | None = None
    retryAfter: float | int | None = None
    retryLimit: int | None = None
    criteria: list[CriterionObject] | None = None

    @model_validator(mode="after")
    def validate_failure_constraints(self) -> FailureAction:
        """Validate `workflowId`/`stepId` exclusivity and non-negative retry bounds.

        Returns:
            The validated FailureAction instance.
        """
        if self.workflowId is not None and self.stepId is not None:
            raise ValueError(
                "FailureAction cannot specify both 'workflowId' and 'stepId'"
            )
        if self.retryAfter is not None and self.retryAfter < 0:
            raise ValueError("FailureAction 'retryAfter' must be non-negative")
        if self.retryLimit is not None and self.retryLimit < 0:
            raise ValueError("FailureAction 'retryLimit' must be non-negative")
        return self


class StepObject(ArazzoBase):
    """Arazzo Step Object representing a single operation, channel, or sub-workflow call."""

    stepId: str
    description: str | None = None
    operationId: str | None = None
    operationPath: str | None = None
    channelPath: str | None = None
    workflowId: str | None = None
    parameters: list[ArazzoParameter | ReusableObject] | None = None
    requestBody: ArazzoRequestBody | None = None
    successCriteria: list[CriterionObject] | None = None
    onSuccess: list[SuccessAction | ReusableObject] | None = None
    onFailure: list[FailureAction | ReusableObject] | None = None
    outputs: dict[str, str | SelectorObject] | None = None
    timeout: int | None = None
    correlationId: str | None = None
    action: StepAction | None = None
    dependsOn: list[str] | None = None

    @model_validator(mode="after")
    def validate_step_target(self) -> StepObject:
        """Validate that at most one target (`operationId`, `operationPath`, `channelPath`, `workflowId`) is set.

        Returns:
            The validated StepObject instance.
        """
        targets = [
            t
            for t in (
                self.operationId,
                self.operationPath,
                self.channelPath,
                self.workflowId,
            )
            if t is not None
        ]
        if len(targets) > 1:
            raise ValueError(
                "StepObject fields 'operationId', 'operationPath', 'channelPath', and 'workflowId' are mutually exclusive"
            )
        return self


class WorkflowObject(ArazzoBase):
    """Arazzo Workflow Object defining inputs, steps, actions, and outputs for a multi-step workflow."""

    workflowId: str
    summary: str | None = None
    description: str | None = None
    inputs: Schema | Reference | dict[str, Any] | None = None
    dependsOn: list[str] | None = None
    steps: list[StepObject]
    successActions: list[SuccessAction | ReusableObject] | None = None
    failureActions: list[FailureAction | ReusableObject] | None = None
    outputs: dict[str, str | SelectorObject] | None = None
    parameters: list[ArazzoParameter | ReusableObject] | None = None

    @model_validator(mode="after")
    def validate_unique_steps(self) -> WorkflowObject:
        """Validate that `stepId` values within a workflow are unique.

        Returns:
            The validated WorkflowObject instance.
        """
        seen: set[str] = set()
        for step in self.steps:
            if step.stepId in seen:
                raise ValueError(
                    f"Duplicate stepId {step.stepId!r} in workflow {self.workflowId!r}"
                )
            seen.add(step.stepId)
        return self


class ArazzoComponents(ArazzoBase):
    """Arazzo Components Object holding reusable inputs, parameters, successActions, and failureActions."""

    inputs: dict[str, Schema | Reference | dict[str, Any]] | None = None
    parameters: dict[str, ArazzoParameter] | None = None
    successActions: dict[str, SuccessAction] | None = None
    failureActions: dict[str, FailureAction] | None = None


class Arazzo(ArazzoBase):
    """Root Arazzo 1.1.0 Specification Object."""

    arazzo: str = "1.1.0"
    self_: str | None = Field(default=None, alias="$self")
    info: ArazzoInfo
    sourceDescriptions: list[SourceDescription]
    workflows: list[WorkflowObject]
    components: ArazzoComponents | None = None

    @model_validator(mode="after")
    def validate_arazzo_document(self) -> Arazzo:
        """Validate Arazzo version compatibility (`1.0.x` or `1.1.x`) and unique `workflowId`s.

        Returns:
            The validated Arazzo specification instance.
        """
        if not (self.arazzo.startswith("1.0.") or self.arazzo.startswith("1.1.")):
            raise ValueError(
                f"Unsupported Arazzo specification version {self.arazzo!r}; expected 1.0.x or 1.1.x"
            )
        seen_workflows: set[str] = set()
        for wf in self.workflows:
            if wf.workflowId in seen_workflows:
                raise ValueError(
                    f"Duplicate workflowId {wf.workflowId!r} in Arazzo spec"
                )
            seen_workflows.add(wf.workflowId)
        return self
