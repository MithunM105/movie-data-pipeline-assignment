PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS movies (
    movie_id INTEGER PRIMARY KEY, -- MovieLens identifier
    title TEXT NOT NULL,
    release_year INTEGER,
    decade INTEGER,
    imdb_id TEXT,
    director TEXT,
    plot TEXT,
    box_office_usd INTEGER,
    omdb_response TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS genres (
    genre_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

CREATE TABLE IF NOT EXISTS ratings (
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    rating REAL NOT NULL CHECK (rating >= 0 AND rating <= 5),
    rated_at TEXT NOT NULL, -- ISO-8601 UTC timestamp
    PRIMARY KEY (user_id, movie_id, rated_at)
);

-- Persistent cache lets OMDb enrichment resume across runs and daily quotas.
CREATE TABLE IF NOT EXISTS omdb_cache (
    movie_id INTEGER PRIMARY KEY REFERENCES movies(movie_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('found', 'not_found')),
    response_json TEXT,
    fetched_at TEXT NOT NULL,
    CHECK ((status = 'found' AND response_json IS NOT NULL) OR
           (status = 'not_found' AND response_json IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_ratings_movie ON ratings(movie_id);
CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(release_year);
CREATE INDEX IF NOT EXISTS idx_movies_director ON movies(director);
