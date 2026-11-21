import csv
import io
import math
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException

from pinpoint.cli import coverage
from pinpoint.config import FIRMS, ROOT
from pinpoint.store import Store


def csv_cell(value):
    text = str(value or "")
    return (
        "'" + text
        if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n"))
        else text
    )


def time_label(value):
    if not value:
        return "Not yet observed"
    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .strftime("%d %b %Y, %H:%M UTC")
        )
    except ValueError:
        return value


def create_app(store=None, load_seed=True):
    @asynccontextmanager
    async def lifespan(app):
        if app.state.store is None:
            app.state.store = Store(os.getenv("PINPOINT_DB", ROOT / "data/pinpoint.sqlite"))
        if load_seed:
            app.state.store.seed(ROOT / "data/seed.json")
        yield

    app = FastAPI(
        title="Pinpoint partner intelligence", lifespan=lifespan, docs_url=None, redoc_url=None
    )
    app.state.store = store
    app.mount("/static", StaticFiles(directory=ROOT / "pinpoint/static"), name="static")
    templates = Jinja2Templates(directory=ROOT / "pinpoint/templates")
    templates.env.filters["time_label"] = time_label
    templates.env.globals["firms"] = FIRMS

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    def render(request, name, context=None, status=200):
        db = app.state.store
        firms_coverage = coverage(db)
        context = dict(
            context or {},
            firm_coverage=firms_coverage,
            captured=sum(f["captured"] for f in firms_coverage),
            represented=sum(f["captured"] > 0 for f in firms_coverage),
            route=request.url.path,
        )
        return templates.TemplateResponse(
            request=request, name=name, context=context, status_code=status
        )

    @app.exception_handler(HTTPException)
    async def not_found(request, exc):
        return render(
            request,
            "error.html",
            {
                "title": "Page not found",
                "message": "This profile or page is unavailable. Return to the directory to continue your research.",
            },
            exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                {
                    "detail": "Invalid filters or pagination. Page must be positive; page size is at most 2,000."
                },
                status_code=422,
            )
        return render(
            request,
            "error.html",
            {
                "title": "Check the filters",
                "message": "Use a positive page number and valid filter values, then try again.",
            },
            422,
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "profiles": app.state.store.search()["total"]}

    @app.get("/", response_class=HTMLResponse)
    def directory(
        request: Request,
        q: str = Query("", max_length=200),
        firm: str = "",
        office: str = "",
        practice: str = "",
        page: int = Query(1, ge=1),
    ):
        db = app.state.store
        filters = dict(q=q.strip(), firm=firm, office=office, practice=practice)
        result = db.search(**filters, page=page)
        pages = max(1, math.ceil(result["total"] / 25))
        page = min(page, pages)
        result = db.search(**filters, page=page)
        all_people = db.search(page_size=100000)["items"]
        return render(
            request,
            "directory.html",
            dict(
                title="Partner directory",
                result=result,
                filters=filters,
                page=page,
                pages=pages,
                offices=sorted({o for p in all_people for o in p.get("offices", [])}),
                practices=sorted({o for p in all_people for o in p.get("practices", [])}),
                previous="/?" + urlencode(dict(filters, page=page - 1)),
                next="/?" + urlencode(dict(filters, page=page + 1)),
                export_url="/export.csv?" + urlencode(filters),
                return_url="/?" + urlencode(dict(filters, page=page)),
            ),
        )

    @app.get("/partners/{key}", response_class=HTMLResponse)
    def partner(request: Request, key: str, back: str = "/"):
        person = app.state.store.get(key)
        if not person:
            raise HTTPException(404)
        # Only allow the directory route to be used as a return destination.
        safe_back = back if back == "/" or back.startswith("/?") else "/"
        return render(
            request, "profile.html", dict(title=person["name"], person=person, back=safe_back)
        )

    @app.get("/coverage", response_class=HTMLResponse)
    def coverage_page(request: Request):
        return render(
            request,
            "coverage.html",
            dict(title="Coverage & refreshes", runs=app.state.store.runs()),
        )

    @app.get("/changes", response_class=HTMLResponse)
    def changes(request: Request, firm: str = ""):
        return render(
            request,
            "changes.html",
            dict(title="Observed changes", events=app.state.store.events(firm), selected_firm=firm),
        )

    @app.get("/api/profiles")
    def profiles(
        q: str = Query("", max_length=200),
        firm: str = "",
        office: str = "",
        practice: str = "",
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=2000),
    ):
        return app.state.store.search(q.strip(), firm, office, practice, page, page_size)

    @app.get("/api/coverage")
    def coverage_api():
        return coverage(app.state.store)

    @app.get("/export.csv")
    def export(
        q: str = Query("", max_length=200), firm: str = "", office: str = "", practice: str = ""
    ):
        people = app.state.store.search(q.strip(), firm, office, practice, page_size=2000)["items"]
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "name",
                "firm",
                "title",
                "practices",
                "offices",
                "source_url",
                "last_observed_utc",
                "office_evidence_status",
                "office_observed_utc",
                "coverage",
            ]
        )
        for p in people:
            writer.writerow(
                [
                    csv_cell(v)
                    for v in [
                        p["name"],
                        FIRMS[p["firm_id"]]["name"],
                        p["title"],
                        "; ".join(p["practices"]),
                        "; ".join(p["offices"]),
                        p["source_url"],
                        p["last_seen"],
                        p.get("office_status", "unknown"),
                        p.get("office_observed_at", ""),
                        "Partial; global coverage unverified",
                    ]
                ]
            )
        return Response(
            output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="pinpoint-partners.csv"'},
        )

    return app


app = create_app()
