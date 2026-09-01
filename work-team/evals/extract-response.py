#!/usr/bin/env python3
"""Extract a terminal response after verifying a real worker dispatch."""

import json
import sys


def main() -> int:
    harness, transcript = sys.argv[1:]
    responses = []
    dispatched = False
    claude_agent_calls = set()
    claude_agents = {}
    with open(transcript) as lines:
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return 3
            if harness == "claude" and event.get("type") == "result":
                responses.append(event.get("result"))
            if harness == "claude":
                message = event.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            if (
                                block.get("type") == "tool_use"
                                and block.get("name") == "Agent"
                                and isinstance(block.get("id"), str)
                                and block["id"]
                            ):
                                claude_agent_calls.add(block["id"])
                            if (
                                block.get("type") == "tool_result"
                                and block.get("tool_use_id") in claude_agent_calls
                            ):
                                result = event.get("tool_use_result", {})
                                if (
                                    isinstance(result, dict)
                                    and isinstance(result.get("agentId"), str)
                                    and result["agentId"]
                                ):
                                    if result.get("status") == "completed":
                                        dispatched = True
                                    elif result.get("status") == "async_launched":
                                        claude_agents[block["tool_use_id"]] = result[
                                            "agentId"
                                        ]
                dispatched |= (
                    event.get("type") == "system"
                    and event.get("subtype") == "task_notification"
                    and event.get("status") == "completed"
                    and event.get("tool_use_id") in claude_agents
                    and event.get("task_id")
                    == claude_agents.get(event.get("tool_use_id"))
                )
            elif harness == "codex":
                item = event.get("item", {})
                if (
                    event.get("type") == "item.completed"
                    and item.get("type") == "agent_message"
                ):
                    responses.append(item.get("text"))
                receiver_ids = item.get("receiver_thread_ids", [])
                dispatched |= (
                    event.get("type") == "item.completed"
                    and item.get("type") == "collab_tool_call"
                    and item.get("tool") == "spawn_agent"
                    and item.get("status") == "completed"
                    and isinstance(receiver_ids, list)
                    and any(
                        isinstance(value, str) and value for value in receiver_ids
                    )
                )
    response = next(
        (
            value
            for value in reversed(responses)
            if isinstance(value, str) and value.strip()
        ),
        None,
    )
    if response is None:
        return 1
    if not dispatched:
        return 2
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
