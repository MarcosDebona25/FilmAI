from django.urls import path

from catalogo.views import (
    DiscoverView,
    KeywordsView,
    MovieDetailView,
    NowPlayingView,
    SearchView,
    TrendingView,
    TVDetailView,
)

app_name = "catalogo"

urlpatterns = [
    path("trending/", TrendingView.as_view(), name="trending"),
    path("now-playing/", NowPlayingView.as_view(), name="now_playing"),
    path("discover/", DiscoverView.as_view(), name="discover"),
    path("search/", SearchView.as_view(), name="search"),
    path("movie/<int:id_tmdb>/", MovieDetailView.as_view(), name="movie_detail"),
    path("tv/<id_tmdb>/", TVDetailView.as_view(), name="tv_detail"),
    path("keywords/", KeywordsView.as_view(), name="keywords"),
]
