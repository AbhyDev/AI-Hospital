from fastapi import APIRouter, HTTPException
from uuid import uuid4
from typing import Optional, List

from .AI_hospital import myapp
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from sse_starlette.sse import EventSourceResponse
import json

router = APIRouter()


# ---------------------------
# Helpers
# ---------------------------
ASK_NODES = {
	"GP_AskUser",
	"Ophthal_AskUser",
	"Pedia_AskUser",
	"Ortho_AskUser",
	"Dermat_AskUser",
	"ENT_AskUser",
	"Gynec_AskUser",
	"Psych_AskUser",
	"IntMed_AskUser",
	"Patho_AskUser",
	"Radio_AskUser",
}


def _make_config(thread_id: str):
	return {"configurable": {"thread_id": thread_id}}


def _initial_inputs(user_text: str):
	# Initialize all streams to keep graph happy
	base_human = HumanMessage(content=user_text)
	return {"messages": [base_human],
    "specialist_messages": [base_human],
    "patho_messages": [HumanMessage(content="Generate some test based on status of Pathology status")],
    "radio_messages": [HumanMessage(content="Generate some report based on status of Radiology status")],
    "patho_QnA": [],
    "radio_QnA": [],
    "next_agent": [],
    "agent_order": [],
    "current_report": [],}

def _extract_ask_question(state_values: dict) -> Optional[str]:
	"""Find the ask_user tool call and return its 'question' argument.
	We look across the possible message streams in order of likelihood."""
	for key in ("messages", "specialist_messages", "patho_messages", "radio_messages"):
		msgs: List = state_values.get(key) or []
		if not msgs:
			continue
		last = msgs[-1]
		if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
			for tc in last.tool_calls:
				if tc.get("name") == "ask_user":
					args = tc.get("args") or {}
					return args.get("question")
	return None


def _inject_user_reply_as_tool_message(state_values: dict, user_reply: str):
	"""Create a ToolMessage for the pending ask_user call.
	We find the last AIMessage with ask_user and mirror its tool_call_id."""
	for key in ("messages", "specialist_messages", "patho_messages", "radio_messages"):
		msgs: List = state_values.get(key) or []
		if not msgs:
			continue
		last = msgs[-1]
		if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
			for tc in last.tool_calls:
				if tc.get("name") == "ask_user":
					tool_call_id = tc.get("id")
					# Return mapping of which stream to append to, and the ToolMessage
					return key, ToolMessage(content=user_reply, tool_call_id=tool_call_id)
	return None, None


def _last_assistant_text(state_values: dict) -> Optional[str]:
	# Prefer specialist/helper streams over GP routing text to avoid repeating selections (e.g., "Orthopedist")
	for key in ("specialist_messages", "patho_messages", "radio_messages", "messages"):
		msgs: List = state_values.get(key) or []
		if not msgs:
			continue
		last = msgs[-1]
		if hasattr(last, "content") and isinstance(last.content, str):
			text = last.content.strip()
			# Suppress bare routing tokens (single-word specialist selections)
			if key == "messages" and text.lower() in {
				"pediatrician", "pediatrics", "ophthalmologist", "orthopedist", "dermatologist",
				"ent", "gynecologist", "psychiatrist", "internal medicine"
			}:
				continue
			return text
	return None


def _speaker_for_key(stream_key: str) -> str:
    if stream_key == "messages":
        return "GP"
    if stream_key == "specialist_messages":
        return "Specialist"
    if stream_key == "patho_messages":
        return "Pathologist"
    if stream_key == "radio_messages":
        return "Radiologist"
    return "Assistant"


def _chunk_to_payload(chunk: dict) -> Optional[dict]:
	# chunk is a partial state update from LangGraph stream
	# Prefer specialist/helper streams over GP routing text
	for key in ("specialist_messages", "patho_messages", "radio_messages", "messages"):
		msgs: List = chunk.get(key) or []
		if not msgs:
			continue
		last = msgs[-1]
		if isinstance(last, AIMessage) and isinstance(last.content, str):
			text = last.content.strip()
			if key == "messages" and text.lower() in {
				"pediatrician", "pediatrics", "ophthalmologist", "orthopedist", "dermatologist",
				"ent", "gynecologist", "psychiatrist", "internal medicine"
			}:
				continue
			return {"content": text, "speaker": _speaker_for_key(key)}
	return None


# ---------------------------
# Endpoints
# ---------------------------
@router.get("/graph/start/stream")
async def start_graph_stream(message: str):
	thread_id = str(uuid4())
	config = _make_config(thread_id)
	inputs = _initial_inputs(message)

	async def event_gen():
		# Announce thread
		yield {"event": "thread", "data": json.dumps({"thread_id": thread_id})}
		async for chunk in myapp.astream(inputs, config, stream_mode="values"):
			payload = _chunk_to_payload(chunk)
			if payload:
				yield {"event": "message", "data": json.dumps({"thread_id": thread_id, **payload})}
		# After stream ends, check if awaiting user or finished
		state = myapp.get_state(config)
		next_nodes = set(state.next or [])
		if next_nodes & ASK_NODES:
			yield {"event": "ask_user", "data": json.dumps({"thread_id": thread_id})}
		else:
			final = _last_assistant_text(state.values or {})
			yield {"event": "final", "data": json.dumps({"thread_id": thread_id, "message": final})}

	return EventSourceResponse(event_gen())

@router.get("/graph/resume/stream")
async def resume_graph_stream(thread_id: str, user_reply: str):
	config = _make_config(thread_id)
	state = myapp.get_state(config)
	if state is None:
		raise HTTPException(status_code=404, detail="Thread not found or expired")

	# Prepare ToolMessage and update state
	stream_key, tool_msg = _inject_user_reply_as_tool_message(state.values or {}, user_reply)
	if not tool_msg:
		raise HTTPException(status_code=400, detail="No pending ask_user call to answer")
	current_stream: List = state.values.get(stream_key, [])
	updated_stream = current_stream + [tool_msg]
	myapp.update_state(config, {stream_key: updated_stream})

	async def event_gen():
		async for chunk in myapp.astream(None, config, stream_mode="values"):
			payload = _chunk_to_payload(chunk)
			if payload:
				yield {"event": "message", "data": json.dumps({"thread_id": thread_id, **payload})}
		state2 = myapp.get_state(config)
		next_nodes = set(state2.next or [])
		if next_nodes & ASK_NODES:
			question = _extract_ask_question(state2.values or {})
			yield {"event": "ask_user", "data": json.dumps({"thread_id": thread_id, "question": question})}
		else:
			final = _last_assistant_text(state2.values or {})
			yield {"event": "final", "data": json.dumps({"thread_id": thread_id, "message": final})}

	return EventSourceResponse(event_gen())