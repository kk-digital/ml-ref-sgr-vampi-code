import json
import logging
import os
import traceback
import uuid
from datetime import datetime
from typing import Type

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_deep_research.core.models import AgentStatesEnum, ResearchContext, TokenUsage
from sgr_deep_research.core.prompts import PromptLoader
from sgr_deep_research.core.stream import OpenAIStreamingGenerator
from sgr_deep_research.core.tools import (
    # Base
    BaseTool,
    ReasoningTool,
    system_agent_tools,
)
from sgr_deep_research.settings import get_config

config = get_config()


class BaseAgent:
    """Base class for agents."""

    name: str = "base_agent"

    def __init__(
        self,
        task: str,
        toolkit: list[Type[BaseTool]] | None = None,
        max_iterations: int = 20,
        max_clarifications: int = 3,
        tracking_token: str | None = None,
        working_directory: str = ".",
        llm_model: str | None = None,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
    ):
        self.id = f"{self.name}_{uuid.uuid4()}"
        self.logger = logging.getLogger(f"sgr_deep_research.agents.{self.id}")
        self.task = task
        self.toolkit = [*system_agent_tools, *(toolkit or [])]
        self.tracking_token = tracking_token

        self._context = ResearchContext(working_directory=working_directory)
        self.conversation = []
        self.log = []
        self.max_iterations = max_iterations
        self.max_clarifications = max_clarifications
        
        # Dynamic LLM configuration (for benchmarking different models)
        self.llm_model = llm_model or config.openai.model
        self.llm_base_url = llm_base_url or config.openai.base_url
        self.llm_api_key = llm_api_key or config.openai.api_key
        
        # Detect provider type from base URL for provider-specific handling
        self._provider_type = self._detect_provider_type()

        client_kwargs = {"base_url": self.llm_base_url, "api_key": self.llm_api_key}
        if config.openai.proxy.strip():
            client_kwargs["http_client"] = httpx.AsyncClient(proxy=config.openai.proxy)

        self.openai_client = AsyncOpenAI(**client_kwargs)
        self.streaming_generator = OpenAIStreamingGenerator(model=self.id)
        
        # Token usage tracking
        self.token_usage = TokenUsage()
    
    def _detect_provider_type(self) -> str:
        """Detect provider type from base URL for provider-specific handling."""
        base_url = self.llm_base_url.lower() if self.llm_base_url else ""
        if "cerebras" in base_url:
            return "cerebras"
        elif "openrouter" in base_url:
            return "openrouter"
        elif "anthropic" in base_url:
            return "anthropic"
        elif "openai" in base_url or "api.openai.com" in base_url:
            return "openai"
        else:
            return "unknown"
    
    def _get_stream_options(self) -> dict | None:
        """Get stream_options based on provider support.
        
        Some providers may not support stream_options parameter.
        Returns None for providers that don't support it.
        
        Note: Cerebras returns usage in final chunk by default but ignores stream_options.
        We handle this by capturing usage from chunks directly in the agent code.
        """
        # Providers known to support stream_options with include_usage
        # Note: Cerebras ignores stream_options but returns usage in final chunk anyway
        supported_providers = {"openrouter", "openai", "anthropic", "cerebras"}
        
        if self._provider_type in supported_providers:
            return {"include_usage": True}
        else:
            # For unknown providers, try anyway - worst case we get an error
            # that we can catch and retry without stream_options
            self.logger.debug(f"Provider '{self._provider_type}' - attempting stream_options")
            return {"include_usage": True}

    def _get_extra_body(self) -> dict:
        """Get extra body parameters for OpenAI requests (e.g., tracking token).
        
        By default, uses agent.id as tracking token for request tracing.
        Parameters are provider-specific - some providers reject unknown fields.
        """
        tracking_id = self.tracking_token or self.id
        
        # Provider-specific extra_body parameters
        if self._provider_type == "openrouter":
            return {
                "litellm_session_id": tracking_id,
                "usage": {"include": True},  # OpenRouter: request usage data including cost
            }
        elif self._provider_type == "cerebras":
            # Cerebras only supports specific extra_body params like disable_reasoning
            # It rejects unknown parameters with 422 error
            return {}
        else:
            # For other providers, try minimal params
            return {}

    async def provide_clarification(self, clarifications: str):
        """Receive clarification from external source (e.g. user input)"""
        self.conversation.append({"role": "user", "content": PromptLoader.get_clarification_template(clarifications)})
        self._context.clarifications_used += 1
        self._context.clarification_received.set()
        self._context.state = AgentStatesEnum.RESEARCHING
        self.logger.info(f"✅ Clarification received: {clarifications[:2000]}...")

    def _log_reasoning(self, result: ReasoningTool) -> None:
        next_step = result.remaining_steps[0] if result.remaining_steps else "Completing"
        self.logger.info(
            f"""
    ###############################################
    🤖 LLM RESPONSE DEBUG:
       🧠 Reasoning Steps: {result.reasoning_steps}
       📊 Current Situation: '{result.current_situation[:400]}...'
       📋 Plan Status: '{result.plan_status[:400]}...'
       🔍 Searches Done: {self._context.searches_used}
       🔍 Clarifications Done: {self._context.clarifications_used}
       ✅ Enough Data: {result.enough_data}
       📝 Remaining Steps: {result.remaining_steps}
       🏁 Task Completed: {result.task_completed}
       ➡️ Next Step: {next_step}
    ###############################################"""
        )
        self.log.append(
            {
                "step_number": self._context.iteration,
                "timestamp": datetime.now().isoformat(),
                "step_type": "reasoning",
                "agent_reasoning": result.model_dump(),
            }
        )

    def _log_tool_execution(self, tool: BaseTool, result: str):
        self.logger.info(
            f"""
###############################################
🛠️ TOOL EXECUTION DEBUG:
    🔧 Tool Name: {tool.tool_name}
    📋 Tool Model: {tool.model_dump_json(indent=2)}
    🔍 Result: '{result[:400]}...'
###############################################"""
        )
        self.log.append(
            {
                "step_number": self._context.iteration,
                "timestamp": datetime.now().isoformat(),
                "step_type": "tool_execution",
                "tool_name": tool.tool_name,
                "agent_tool_context": tool.model_dump(),
                "agent_tool_execution_result": result,
            }
        )

    def _save_agent_log(self):
        logs_dir = config.execution.logs_dir
        os.makedirs(logs_dir, exist_ok=True)
        filepath = os.path.join(logs_dir, f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{self.id}-log.json")
        agent_log = {
            "id": self.id,
            "model_config": config.openai.model_dump(exclude={"api_key", "proxy"}),
            "task": self.task,
            "toolkit": [tool.tool_name for tool in self.toolkit],
            "log": self.log,
        }

        json.dump(agent_log, open(filepath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    async def _prepare_context(self) -> list[dict]:
        """Prepare conversation context with system prompt."""
        return [
            {"role": "system", "content": PromptLoader.get_system_prompt(self.toolkit)},
            *self.conversation,
        ]

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for current agent state and progress."""
        raise NotImplementedError("_prepare_tools must be implemented by subclass")

    async def _reasoning_phase(self) -> ReasoningTool:
        """Call LLM to decide next action based on current context."""
        raise NotImplementedError("_reasoning_phase must be implemented by subclass")

    async def _select_action_phase(self, reasoning: ReasoningTool) -> BaseTool:
        """Select most suitable tool for the action decided in reasoning phase.

        Returns the tool suitable for the action.
        """
        raise NotImplementedError("_select_action_phase must be implemented by subclass")

    async def _action_phase(self, tool: BaseTool) -> str:
        """Call Tool for the action decided in select_action phase.

        Returns string or dumped json result of the tool execution.
        """
        raise NotImplementedError("_action_phase must be implemented by subclass")

    async def execute(
        self,
    ):
        self.logger.info(f"🚀 Starting for task: '{self.task}'")
        self.conversation.extend(
            [
                {
                    "role": "user",
                    "content": PromptLoader.get_initial_user_request(self.task),
                }
            ]
        )
        try:
            while self._context.state not in AgentStatesEnum.FINISH_STATES.value:
                self._context.iteration += 1
                self.logger.info(f"Step {self._context.iteration} started")

                reasoning = await self._reasoning_phase()
                self._context.current_step_reasoning = reasoning
                action_tool = await self._select_action_phase(reasoning)
                await self._action_phase(action_tool)

        except Exception as e:
            self.logger.error(f"❌ Agent execution error: {str(e)}")
            self._context.state = AgentStatesEnum.FAILED
            traceback.print_exc()
        finally:
            if self.streaming_generator is not None:
                usage_dict = self.token_usage.to_dict()
                self.logger.info(f"Final usage dict has {len(usage_dict.get('request_details', []))} request_details")
                self.streaming_generator.finish(usage=usage_dict)
            self._save_agent_log()
