"""Load MovieLens small CSVs and enrich each movie with OMDb metadata."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

OMDB_URL = "https://www.omdbapi.com/"
UNKNOWN_GENRES = {"(no genres listed)", ""}


class OmdbServiceError(RuntimeError):
    """A non-movie-not-found API error that should pause lookups for this run."""


def parse_year(title: str) -> int | None:
    match = re.search(r"\((\d{4})\)\s*$", title)
    if not match:
        return None
    year = int(match.group(1))
    return year if 1870 <= year <= datetime.now().year + 5 else None


def clean_title(title: str) -> str:
    return re.sub(r"\s*\(\d{4}\)\s*$", "", title).strip()


def parse_box_office(value: str | None) -> int | None:
    if not value or value.strip() in {"", "N/A"}:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fetch_omdb(session: requests.Session, title: str, year: int | None,
               api_key: str, retries: int = 3) -> dict[str, Any] | None:
    """Lookup title/year; return None only for a definitive movie-not-found result."""
    params: dict[str, str] = {"apikey": api_key, "t": clean_title(title)}
    if year:
        params["y"] = str(year)
    for attempt in range(retries):
        try:
            response = session.get(OMDB_URL, params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()
            if payload.get("Response") == "True":
                return payload
            error = str(payload.get("Error", "Unknown OMDb error"))
            if error.casefold() == "movie not found!":
                return None
            raise OmdbServiceError(error)
        except OmdbServiceError:
            raise
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries - 1:
                # requests exceptions may include the full URL, including the API key.
                response = getattr(exc, "response", None)
                detail = f"HTTP {response.status_code}" if response is not None else type(exc).__name__
                raise OmdbServiceError(f"lookup failed for {title!r}: {detail}") from exc
            else:
                time.sleep(2 ** attempt)
    raise OmdbServiceError(f"lookup failed for {title!r}")


def load(args: argparse.Namespace) -> None:
    movies_path, ratings_path = Path(args.data_dir) / "movies.csv", Path(args.data_dir) / "ratings.csv"
    if not movies_path.is_file() or not ratings_path.is_file():
        raise FileNotFoundError(f"Expected movies.csv and ratings.csv under {args.data_dir}")
    api_key = args.omdb_api_key or os.getenv("OMDB_API_KEY")
    if not api_key and not args.skip_omdb:
        raise ValueError("Set OMDB_API_KEY, pass --omdb-api-key, or use --skip-omdb")

    movies = read_csv(movies_path)
    ratings = read_csv(ratings_path)
    db_path = Path(args.database)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(Path(args.schema).read_text(encoding="utf-8-sig"))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with requests.Session() as session, conn:
            api_paused = False
            for index, row in enumerate(movies, 1):
                movie_id = int(row["movieId"])
                title = row["title"].strip()
                year = parse_year(title)
                genres = [g.strip() for g in row.get("genres", "").split("|")
                          if g.strip() not in UNKNOWN_GENRES]
                cached = conn.execute(
                    "SELECT status, response_json FROM omdb_cache WHERE movie_id=?", (movie_id,)
                ).fetchone()
                did_lookup = False
                if cached:
                    details = json.loads(cached[1]) if cached[0] == "found" else None
                else:
                    details = None
                    if api_key and not args.skip_omdb and not api_paused:
                        did_lookup = True
                        try:
                            details = fetch_omdb(session, title, year, api_key)
                        except OmdbServiceError as exc:
                            # A quota/key/service error should not burn one request per remaining movie.
                            print(f"Pausing OMDb lookups after error for {title!r}: {exc}", file=sys.stderr)
                            api_paused = True
                imdb_id = (details or {}).get("imdbID")
                release_year = year
                if details and details.get("Year", "N/A")[:4].isdigit():
                    release_year = int(details["Year"][:4])
                director = (details or {}).get("Director")
                if director in {None, "", "N/A"}:
                    director = None
                plot = (details or {}).get("Plot")
                if plot in {None, "", "N/A"}:
                    plot = None
                box_office = parse_box_office((details or {}).get("BoxOffice"))
                decade = (release_year // 10) * 10 if release_year else None
                conn.execute("""INSERT INTO movies
                    (movie_id,title,release_year,decade,imdb_id,director,plot,box_office_usd,omdb_response,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(movie_id) DO UPDATE SET title=excluded.title,
                    release_year=excluded.release_year, decade=excluded.decade,
                    imdb_id=excluded.imdb_id, director=excluded.director, plot=excluded.plot,
                    box_office_usd=excluded.box_office_usd, omdb_response=excluded.omdb_response,
                    updated_at=excluded.updated_at""",
                    (movie_id, title, release_year, decade, imdb_id, director, plot, box_office,
                     json.dumps(details, ensure_ascii=False) if details else None, now))
                if not cached and did_lookup and not api_paused:
                    conn.execute("""INSERT INTO omdb_cache(movie_id,status,response_json,fetched_at)
                        VALUES (?,?,?,?) ON CONFLICT(movie_id) DO NOTHING""",
                        (movie_id, "found" if details else "not_found",
                         json.dumps(details, ensure_ascii=False) if details else None, now))
                # Rebuild genre links for this movie so changed CSV input is reflected.
                conn.execute("DELETE FROM movie_genres WHERE movie_id=?", (movie_id,))
                for genre in genres:
                    conn.execute("INSERT INTO genres(name) VALUES (?) ON CONFLICT(name) DO NOTHING", (genre,))
                    genre_id = conn.execute("SELECT genre_id FROM genres WHERE name=?", (genre,)).fetchone()[0]
                    conn.execute("INSERT INTO movie_genres(movie_id,genre_id) VALUES (?,?)", (movie_id, genre_id))
                if did_lookup and args.delay and index < len(movies) and not api_paused:
                    time.sleep(args.delay)
            for row in ratings:
                try:
                    user_id, movie_id = int(row["userId"]), int(row["movieId"])
                    rating = float(row["rating"])
                    stamp = datetime.fromtimestamp(int(row["timestamp"]), tz=timezone.utc).isoformat(timespec="seconds")
                    if not 0 <= rating <= 5:
                        raise ValueError("rating outside 0..5")
                except (KeyError, ValueError, OverflowError) as exc:
                    print(f"Skipping invalid rating row {row}: {exc}", file=sys.stderr)
                    continue
                # Dataset ratings have a unique user/movie/timestamp identity.
                conn.execute("""INSERT INTO ratings(user_id,movie_id,rating,rated_at) VALUES (?,?,?,?)
                    ON CONFLICT(user_id,movie_id,rated_at) DO UPDATE SET rating=excluded.rating""",
                    (user_id, movie_id, rating, stamp))
        print(f"Loaded {len(movies)} movies and {len(ratings)} rating rows into {db_path}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", help="Directory containing movies.csv and ratings.csv")
    parser.add_argument("--database", default="movie_data.db", help="SQLite database path")
    parser.add_argument("--schema", default=str(Path(__file__).with_name("schema.sql")))
    parser.add_argument("--omdb-api-key", help="Prefer setting OMDB_API_KEY instead")
    parser.add_argument("--skip-omdb", action="store_true", help="Load MovieLens data without external enrichment")
    parser.add_argument("--delay", type=float, default=0.2, help="Seconds between OMDb requests")
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay must be non-negative")
    try:
        load(args)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
