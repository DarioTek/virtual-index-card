"""FastAPI application: accounts, card CRUD, and a durable shuffled deck."""

import time
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Iterator

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from sqlite3 import Connection

from . import repository as repo
from .config import Settings, load_settings
from .db import connect, initialize
from .domain import ValidationError, clean_note, shuffled_cards, utc_now
from .security import hash_password, new_token, tokens_match, verify_password

PACKAGE_DIR = Path(__file__).resolve().parent
SESSION_COOKIE = "vic_session"
CSRF_COOKIE = "vic_csrf"
USERNAME_MAX = 30
PASSWORD_MIN = 8


class CardInput(BaseModel):
    front: str
    back: str

    model_config = ConfigDict(extra="forbid")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    initialize(settings.database_path)

    app = FastAPI(title="Virtual Index Cards", version="0.1.0")
    app.state.settings = settings
    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    def get_connection(request: Request) -> Iterator[Connection]:
        connection = connect(request.app.state.settings.database_path)
        try:
            yield connection
        finally:
            connection.close()

    def current_user(request: Request, connection: Connection) -> object | None:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return repo.get_session_user(connection, token, int(time.time()))

    def require_user(request: Request, connection: Annotated[Connection, Depends(get_connection)]) -> object:
        user = current_user(request, connection)
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return user

    def require_csrf(request: Request) -> None:
        if not tokens_match(
            request.cookies.get(CSRF_COOKIE), request.headers.get("X-CSRF-Token")
        ):
            raise HTTPException(status_code=403, detail="Invalid CSRF token.")

    def set_auth_cookies(
        response: Response, session_token: str, csrf_token: str
    ) -> None:
        common = {
            "max_age": settings.session_ttl_seconds,
            "samesite": "lax",
            "secure": settings.cookie_secure,
            "path": "/",
        }
        response.set_cookie(SESSION_COOKIE, session_token, httponly=True, **common)
        response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, **common)

    def clear_auth_cookies(response: Response) -> None:
        response.delete_cookie(SESSION_COOKIE, path="/")
        response.delete_cookie(CSRF_COOKIE, path="/")

    def start_session(
        connection: Connection, user_id: int, response: Response
    ) -> None:
        session_token = new_token()
        csrf_token = new_token()
        repo.delete_expired_sessions(connection, int(time.time()))
        repo.create_session(
            connection,
            session_token,
            user_id,
            int(time.time()) + settings.session_ttl_seconds,
            utc_now(),
        )
        set_auth_cookies(response, session_token, csrf_token)

    def validate_credentials(username: str, password: str) -> str | None:
        username = username.strip()
        if not (3 <= len(username) <= USERNAME_MAX):
            return f"Username must be between 3 and {USERNAME_MAX} characters."
        if not username.replace("_", "").replace("-", "").isalnum():
            return "Use only letters, numbers, underscores, or hyphens in usernames."
        if len(password) < PASSWORD_MIN:
            return f"Password must be at least {PASSWORD_MIN} characters."
        return None

    def validated_note_pair(payload: CardInput) -> tuple[str, str]:
        try:
            return clean_note(payload.front, "Front"), clean_note(payload.back, "Back")
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # --- Account pages ------------------------------------------------------

    @app.get("/register", response_class=HTMLResponse, tags=["accounts"])
    def register_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "register.html", {"error": None})

    @app.post("/register", tags=["accounts"])
    def register(
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        username = username.strip()
        error = validate_credentials(username, password)
        session_response: Response | None = None
        if error is None:
            salt, digest = hash_password(password)
            try:
                with connection:
                    user_id = repo.create_user(connection, username, salt, digest, utc_now())
                    session_response = RedirectResponse("/", status_code=303)
                    start_session(connection, user_id, session_response)
            except repo.UsernameTaken:
                error = "That username is already registered."
        if error is not None or session_response is None:
            return templates.TemplateResponse(
                request, "register.html", {"error": error}, status_code=400
            )
        return session_response

    @app.get("/login", response_class=HTMLResponse, tags=["accounts"])
    def login_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "login.html", {"error": None})

    @app.post("/login", tags=["accounts"])
    def login(
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        user = repo.get_user_by_username(connection, username.strip())
        if user is None or not verify_password(
            password, user["salt"], user["password_hash"]
        ):
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Invalid username or password."},
                status_code=401,
            )
        response = RedirectResponse("/", status_code=303)
        with connection:
            start_session(connection, int(user["id"]), response)
        return response

    @app.post("/logout", tags=["accounts"])
    def logout(
        request: Request,
        csrf_token: Annotated[str, Form()],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        if not tokens_match(request.cookies.get(CSRF_COOKIE), csrf_token):
            raise HTTPException(status_code=403, detail="Invalid CSRF token.")
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            with connection:
                repo.delete_session(connection, token)
        response = RedirectResponse("/login", status_code=303)
        clear_auth_cookies(response)
        return response

    # --- Deck page ----------------------------------------------------------

    @app.get("/", response_class=HTMLResponse, tags=["ui"])
    def deck_page(request: Request, connection: Annotated[Connection, Depends(get_connection)]) -> Response:
        user = current_user(request, connection)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(
            request,
            "deck.html",
            {
                "user": user,
                "cards": repo.list_cards(connection, int(user["id"])),
                "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            },
        )

    @app.get("/review", response_class=HTMLResponse, tags=["ui"])
    def review_page(
        request: Request,
        connection: Annotated[Connection, Depends(get_connection)],
        index: int = 0,
    ) -> Response:
        user = current_user(request, connection)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        cards = repo.list_cards(connection, int(user["id"]))
        total = len(cards)
        position = index % total if total else 0
        return templates.TemplateResponse(
            request,
            "review.html",
            {
                "user": user,
                "card": cards[position] if cards else None,
                "position": position,
                "total": total,
                "prev_index": (position - 1) % total if total else 0,
                "next_index": (position + 1) % total if total else 0,
                "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
            },
        )

    # --- Card API -----------------------------------------------------------

    @app.post("/api/cards", status_code=status.HTTP_201_CREATED, tags=["cards"])
    def create_card(
        request: Request,
        payload: CardInput,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> dict:
        require_csrf(request)
        front, back = validated_note_pair(payload)
        with connection:
            card = repo.create_card(connection, int(user["id"]), front, back, utc_now())
        return {"card": asdict(card)}

    @app.patch("/api/cards/{card_id}", tags=["cards"])
    def update_card(
        card_id: int,
        request: Request,
        payload: CardInput,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> dict:
        require_csrf(request)
        front, back = validated_note_pair(payload)
        with connection:
            card = repo.update_card(
                connection, int(user["id"]), card_id, front, back, utc_now()
            )
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found.")
        return {"card": asdict(card)}

    @app.delete("/api/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["cards"])
    def delete_card(
        card_id: int,
        request: Request,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> Response:
        require_csrf(request)
        with connection:
            removed = repo.delete_card(connection, int(user["id"]), card_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Card not found.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/deck/shuffle", tags=["deck"])
    def shuffle_deck(
        request: Request,
        user: Annotated[object, Depends(require_user)],
        connection: Annotated[Connection, Depends(get_connection)],
    ) -> dict:
        require_csrf(request)
        with connection:
            cards = repo.list_cards(connection, int(user["id"]))
            shuffled = shuffled_cards(cards)
            repo.replace_positions(connection, int(user["id"]), shuffled)
        return {"cards": [asdict(card) for card in shuffled]}

    return app


app = create_app()
