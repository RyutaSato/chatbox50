from uuid import uuid4

from fastapi import APIRouter, Request
from starlette.responses import FileResponse

staticfiles_router = APIRouter()


@staticfiles_router.get("/")
async def root(request: Request):
    token = request.cookies.get("token")
    file_response = FileResponse("index.html")
    if token is None:
        file_response.set_cookie("token", str(uuid4()))
    return file_response


@staticfiles_router.get("/main.js")
async def main_js():
    return FileResponse("main.js")


@staticfiles_router.get("/style.css")
async def style_css():
    return FileResponse("style.css")
