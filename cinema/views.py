from operator import ior
from functools import reduce

from django.db.models import Q, F
from rest_framework import viewsets, pagination

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order

from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer,
    MovieSerializer,
    MovieSessionSerializer,
    MovieSessionListSerializer,
    MovieDetailSerializer,
    MovieSessionDetailSerializer,
    MovieListSerializer,
    OrderSerializer,
    OrderCreateSerializer,
)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class CinemaHallViewSet(viewsets.ModelViewSet):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

    def get_queryset(self):
        queryset = self.queryset

        actors = self.request.GET.get("actors")
        genres = self.request.GET.get("genres")
        title = self.request.GET.get("title")

        if actors:
            queryset = queryset.filter(
                reduce(
                    ior,
                    [
                        Q(
                            actors__first_name=first_name,
                            actors__last_name=last_name,
                        )
                        for first_name, last_name in map(
                            str.split, actors.split(",")
                        )
                    ],
                )
            )
        if genres:
            queryset = queryset.filter(genres__name__in=genres.split(","))
        if title:
            queryset = queryset.filter(title__contains=title)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer

        if self.action == "retrieve":
            return MovieDetailSerializer

        return MovieSerializer


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = MovieSession.objects.all()
    serializer_class = MovieSessionSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return MovieSessionListSerializer

        if self.action == "retrieve":
            return MovieSessionDetailSerializer

        return MovieSessionSerializer

    def get_queryset(self):
        queryset = self.queryset.select_related("movie", "cinema_hall")

        if self.action == "retrieve":
            queryset = queryset.annotate(
                tickets_available=F("cinema_hall__rows")
                * F("cinema_hall__seats_in_row")
                - queryset.first().tickets.count()
            )

        date = self.request.GET.get("date")
        movie_id = self.request.GET.get("movie")

        if date:
            queryset = queryset.filter(show_time__date=date)
        if movie_id:
            queryset = queryset.filter(movie_id=int(movie_id))

        return queryset


class OrderPagination(pagination.PageNumberPagination):
    page_size = 10


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        queryset = self.queryset.prefetch_related(
            "tickets__movie_session__movie",
            "tickets__movie_session__cinema_hall",
        )
        if not self.request.user.is_authenticated:
            return queryset.none()

        queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
