import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import ast
import requests
import re
import os

# =========================
# TMDB API KEY
# =========================
TMDB_API_KEY = "2e7efd7f9a1f88891a233b7982c5f17b"


class MovieRecommender:

    # =========================
    # INIT
    # =========================
    def __init__(self):

        self.poster_cache = {}

        path = os.path.join(
            os.path.dirname(__file__),
            "tmdb_5000_movies.csv"
        )

        if not os.path.exists(path):

            print("CSV file not found")
            self.df = None
            return

        # LOAD DATASET
        self.df = pd.read_csv(path)

        self.df = self.df[
            [
                'title',
                'overview',
                'genres',
                'keywords',
                'vote_average',
                'popularity',
                'release_date'
            ]
        ].fillna('')

        # PARSE GENRES
        self.df['genres_list'] = self.df[
            'genres'
        ].apply(self.parse_names)

        # PARSE KEYWORDS
        self.df['keywords_list'] = self.df[
            'keywords'
        ].apply(self.parse_names)

        # CREATE TAGS
        self.df['tags'] = (
            self.df['overview'] + ' ' +
            self.df['genres_list'].apply(
                lambda x: ' '.join(x)
            ) + ' ' +
            self.df['keywords_list'].apply(
                lambda x: ' '.join(x)
            )
        )

        # TF-IDF
        tfidf = TfidfVectorizer(
            stop_words='english'
        )

        vectors = tfidf.fit_transform(
            self.df['tags']
        )

        # COSINE SIMILARITY
        self.similarity = cosine_similarity(
            vectors
        )

        print(f"{len(self.df)} Movies Loaded")

    # =========================
    # PARSE JSON
    # =========================
    def parse_names(self, text):

        try:

            data = ast.literal_eval(text)

            return [
                item['name']
                for item in data
            ]

        except:

            return []

    # =========================
    # GET POSTER
    # =========================
    def get_poster(self, movie_name):

        # CACHE
        if movie_name in self.poster_cache:
            return self.poster_cache[movie_name]

        try:

            url = (
                f"https://api.themoviedb.org/3/search/movie"
                f"?api_key={TMDB_API_KEY}"
                f"&query={requests.utils.quote(movie_name)}"
            )

            response = requests.get(url)

            data = response.json()

            results = data.get("results", [])

            for movie in results:

                if movie.get("poster_path"):

                    poster = (
                        "https://image.tmdb.org/t/p/w500"
                        + movie["poster_path"]
                    )

                    self.poster_cache[movie_name] = poster

                    return poster

        except:
            pass

        fallback = (
            "https://via.placeholder.com/300x450"
            "?text=No+Poster"
        )

        self.poster_cache[movie_name] = fallback

        return fallback

    # =========================
    # LIVE API SEARCH
    # =========================
    def api_search(self, query):

        try:

            url = (
                f"https://api.themoviedb.org/3/search/movie"
                f"?api_key={TMDB_API_KEY}"
                f"&query={requests.utils.quote(query)}"
            )

            response = requests.get(url)

            data = response.json()

            results = []

            for movie in data.get("results", [])[:12]:

                poster = ""

                if movie.get("poster_path"):

                    poster = (
                        "https://image.tmdb.org/t/p/w500"
                        + movie["poster_path"]
                    )

                results.append({

                    "title": movie.get("title", ""),

                    "overview": movie.get(
                        "overview",
                        ""
                    ),

                    "genres_list": [],

                    "vote_average": movie.get(
                        "vote_average",
                        0
                    ),

                    "popularity": movie.get(
                        "popularity",
                        0
                    ),

                    "release_date": movie.get(
                        "release_date",
                        ""
                    ),

                    "poster_url": poster,

                    "match_type": "api"
                })

            return results

        except:

            return []

    # =========================
    # MAIN SEARCH
    # =========================
    def search(self, query, top_n=12):

        if self.df is None:
            return [], "Dataset not loaded"

        query = query.lower().strip()

        clean_titles = (
            self.df['title']
            .fillna('')
            .str.lower()
            .apply(
                lambda x: re.sub(
                    r'[^a-z0-9]',
                    '',
                    x
                )
            )
        )

        clean_query = re.sub(
            r'[^a-z0-9]',
            '',
            query
        )

        # =====================
        # EXACT MOVIE MATCH
        # =====================
        exact_match = (
            clean_titles == clean_query
        )

        if exact_match.any():

            idx = exact_match[
                exact_match
            ].index[0]

            sim_scores = list(
                enumerate(
                    self.similarity[idx]
                )
            )

            sim_scores = sorted(
                sim_scores,
                key=lambda x: x[1],
                reverse=True
            )

            sim_scores = sim_scores[
                1:top_n + 1
            ]

            movie_indices = [
                i[0]
                for i in sim_scores
            ]

            results = self.df.iloc[
                movie_indices
            ].copy()

            results = results.sort_values(
                by=[
                    'popularity',
                    'vote_average'
                ],
                ascending=False
            )

            results['poster_url'] = results[
                'title'
            ].apply(self.get_poster)

            results['match_type'] = (
                "recommendation"
            )

            return (
                results[
                    [
                        'title',
                        'overview',
                        'genres_list',
                        'vote_average',
                        'popularity',
                        'release_date',
                        'poster_url',
                        'match_type'
                    ]
                ].to_dict(
                    orient='records'
                ),
                None
            )

        # =====================
        # TITLE SEARCH
        # =====================
        matched = self.df[
            clean_titles.str.contains(
                clean_query,
                na=False
            )
        ].copy()

        if not matched.empty:

            matched = matched.sort_values(
                by=[
                    'popularity',
                    'vote_average'
                ],
                ascending=False
            )

            matched['poster_url'] = matched[
                'title'
            ].apply(self.get_poster)

            matched['match_type'] = "search"

            return (
                matched.head(top_n)[
                    [
                        'title',
                        'overview',
                        'genres_list',
                        'vote_average',
                        'popularity',
                        'release_date',
                        'poster_url',
                        'match_type'
                    ]
                ].to_dict(
                    orient='records'
                ),
                None
            )

        # =====================
        # TMDB API SEARCH
        # =====================
        api_results = self.api_search(
            query
        )

        if api_results:
            return api_results, None

        return [], "No movie found"


# =========================
# START
# =========================
recommender = MovieRecommender()