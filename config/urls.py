from django.contrib import admin
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    # Health check
    path('health/', lambda request: HttpResponse("Success!"), name='health'),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API v1 Endpoints
    path('api/v1/auth/', include('apps.accounts.urls', namespace='auth')),
    path('api/v1/system/', include('apps.core.urls', namespace='core')),
    path('api/v1/search/', include('apps.search.urls', namespace='search')),
    path('api/v1/catalog/', include('apps.catalog.urls', namespace='catalog')),
    path('api/v1/portfolio/', include('apps.portfolio.urls', namespace='portfolio')),

    # Django Admin
    path("admin/", admin.site.urls),
]
    


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    
    
# if you wish to test the PWA on dev, uncomment the following lines,
# so that django serves static files.
# remember to built the frontend manually and run collectstatic as well.
# if not settings.DEBUG:
#     from django.views.static import serve
#     urlpatterns += [
#         re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT})
#     ]