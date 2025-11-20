"""
Core URLs.
"""

from django.urls import path

from .views import SystemConfigurationView

app_name = 'core'

urlpatterns = [
    # System Configuration
    path('config/', SystemConfigurationView.as_view(), name='system_config'),
]
