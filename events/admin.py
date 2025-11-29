from django.contrib import admin
from .models import Event, Reservation


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """
    Event modeli için admin arayüzü.
    """
    list_display = ['name', 'capacity', 'start_time', 'end_time', 'is_active', 'created_at']
    list_filter = ['is_active', 'start_time', 'created_at']
    search_fields = ['name', 'description']
    date_hierarchy = 'start_time'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Reservation modeli için admin arayüzü.
    """
    list_display = ['id', 'user', 'event', 'status', 'quantity', 'expires_at', 'created_at']
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['user__username', 'event__name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']

