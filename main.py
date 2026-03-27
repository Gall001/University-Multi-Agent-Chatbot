import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agents import ADVISOR, TEACHERS
from engine import route_question, stream_teacher_response

app = FastAPI(title="Greenfield University Chatbot")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def advisor_page(request: Request):
    return templates.TemplateResponse(
        request,
        "advisor.html",
        {
            "advisor": ADVISOR,
            "teachers": list(TEACHERS.values()),
        },
    )


@app.post("/ask")
async def ask_advisor(question: str = Form(...)):
    teacher_id = route_question(question)

    # Redirect to teacher page, passing question as a query parameter
    from urllib.parse import quote
    encoded_question = quote(question)
    return RedirectResponse(
        url=f"/teacher/{teacher_id}?question={encoded_question}",
        status_code=303,
    )


@app.get("/teacher/{teacher_id}", response_class=HTMLResponse)
async def teacher_page(request: Request, teacher_id: str, question: str = ""):
    if teacher_id not in TEACHERS:
        return RedirectResponse(url="/")

    teacher = TEACHERS[teacher_id]
    other_teachers = [t for tid, t in TEACHERS.items() if tid != teacher_id]

    return templates.TemplateResponse(
        request,
        "teacher.html",
        {
            "teacher": teacher,
            "question": question,
            "advisor": ADVISOR,
            "other_teachers": other_teachers,
            "all_teachers": list(TEACHERS.values()),
        },
    )


@app.get("/stream/{teacher_id}")
async def stream_answer(teacher_id: str, question: str = ""):
    if teacher_id not in TEACHERS or not question:
        return HTMLResponse("Invalid request", status_code=400)

    def event_generator():
        try:
            for chunk in stream_teacher_response(teacher_id, question):
                safe_chunk = chunk.replace("\n", "\\n")
                yield f"data: {safe_chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR: {str(e)}]\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/teachers")
async def get_teachers():
    """JSON endpoint listing all teachers (useful for debugging)."""
    return [
        {
            "id": t.id,
            "name": t.name,
            "subject": t.subject,
            "emoji": t.emoji,
        }
        for t in TEACHERS.values()
    ]