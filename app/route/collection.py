from fastapi import Request

from .. import app, render


@app.get("/collection")
def index(request: Request):
    return render("page/collection.html", request)
