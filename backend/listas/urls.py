from django.urls import path

from .views import ListaDetailView, ListaItemDetailView, ListaItemsView, ListasView

app_name = "listas"

urlpatterns = [
    path("", ListasView.as_view(), name="listas"),
    path("<int:lista_id>/", ListaDetailView.as_view(), name="lista_detail"),
    path("<int:lista_id>/items/", ListaItemsView.as_view(), name="lista_items"),
    path(
        "<int:lista_id>/items/<int:item_id>/",
        ListaItemDetailView.as_view(),
        name="lista_item_detail",
    ),
]
