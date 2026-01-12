from fastapi import Form, Request
from passlib.context import CryptContext
from sqlalchemy import select

from .. import app, render
from ..db import AsyncSessionLocal
from ..db.models import User

crypto = CryptContext(schemes=["argon2"], deprecated="auto")


@app.get("/auth/login")
async def login_get(request: Request):
    return render("partial/login.html", request)


@app.post("/auth/login")
async def login(request: Request, username: str = Form(""), password: str = Form("")):
    async with AsyncSessionLocal() as session:
        user: User = await session.scalar(select(User).where(User.name == username))

    if user is None:
        return False

    if not crypto.verify(password, user.hash):
        return False

    request.session["user_id"] = user.id
    return True


@app.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return "Y"


@app.get("/auth/register")
async def register(request: Request):
    return "N"


@app.get("/debug/adam")
async def create_adam():
    async with AsyncSessionLocal() as session:
        adam = User(name="adam", hash=crypto.hash("password"))
        session.add(adam)
        await session.commit()
