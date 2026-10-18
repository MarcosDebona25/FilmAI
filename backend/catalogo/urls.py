from django.urls import path

from catalogo.views import (
    BrowseView,
    CreditsView,
    DiscoverView,
    GenresView,
    KeywordsView,
    MovieDetailView,
    NowPlayingView,
    ProvidersView,
    RecommendedView,
    SearchView,
    TrendingView,
    TVDetailView,
)

app_name = "catalogo"

urlpatterns = [
    path("trending/", TrendingView.as_view(), name="trending"),
    path("now-playing/", NowPlayingView.as_view(), name="now_playing"),
    path("discover/", DiscoverView.as_view(), name="discover"),
    path("recommended/", RecommendedView.as_view(), name="recommended"),
    path("search/", SearchView.as_view(), name="search"),
    path("browse/", BrowseView.as_view(), name="browse"),
    # Sin conversor `int:` a propósito: la validación de `id_tmdb` la hace
    # `_int_param` dentro de la vista, que devuelve 400 ante un valor no
    # entero. Con `<int:...>` la URL no matchearía y Django respondería 404,
    # incumpliendo la spec de C-03 (openspec/specs/tmdb-endpoints/spec.md).
    path("movie/<id_tmdb>/", MovieDetailView.as_view(), name="movie_detail"),
    path("tv/<id_tmdb>/", TVDetailView.as_view(), name="tv_detail"),
    path(
        "movie/<id_tmdb>/credits/",
        CreditsView.as_view(tipo="movie"),
        name="movie_credits",
    ),
    path("tv/<id_tmdb>/credits/", CreditsView.as_view(tipo="tv"), name="tv_credits"),
    path(
        "movie/<id_tmdb>/providers/",
        ProvidersView.as_view(tipo="movie"),
        name="movie_providers",
    ),
    path(
        "tv/<id_tmdb>/providers/",
        ProvidersView.as_view(tipo="tv"),
        name="tv_providers",
    ),
    path("genres/", GenresView.as_view(), name="genres"),
    path("keywords/", KeywordsView.as_view(), name="keywords"),
]
