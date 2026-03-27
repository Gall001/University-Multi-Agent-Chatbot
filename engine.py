from typing import Generator
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from agents import ADVISOR, TEACHERS, TeacherAgent

MODEL = "llama3.2"
VALID_TEACHER_IDS = set(TEACHERS.keys())


def _build_teacher_list() -> str:
    lines = []
    for tid, teacher in TEACHERS.items():
        lines.append(f"- ID: {tid} | {teacher.name} | Subject: {teacher.subject} | Expertise: {teacher.specialty}")
    return "\n".join(lines)


def route_question(question: str) -> str:
    llm = ChatOllama(model=MODEL, temperature=0)  

    teacher_list = _build_teacher_list()
    prompt = ADVISOR.system_prompt_template.format(
        teacher_list=teacher_list,
        question=question,
    )

    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)

    # Clean and validate the response
    chosen_id = response.content.strip().lower().replace(".", "").replace(",", "")

    if chosen_id in VALID_TEACHER_IDS:
        return chosen_id

    # Fallback: scan the response for any valid ID
    for tid in VALID_TEACHER_IDS:
        if tid in chosen_id:
            return tid

    # Last resort: default to first teacher
    return list(TEACHERS.keys())[0]


def stream_teacher_response(teacher_id: str, question: str) -> Generator[str, None, None]:
    teacher: TeacherAgent = TEACHERS[teacher_id]
    llm = ChatOllama(model=MODEL, temperature=0.7)  

    messages = [
        SystemMessage(content=teacher.system_prompt),
        HumanMessage(content=f"Student question: {question}"),
    ]

    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content