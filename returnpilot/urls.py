from pathlib import Path
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse, FileResponse
from django.conf import settings


def serve_spa(request):
    dist_index = settings.BASE_DIR / "frontend" / "dist" / "index.html"
    if dist_index.exists():
        return FileResponse(open(dist_index, "rb"), content_type="text/html")
    return HttpResponse(
        """
        <!DOCTYPE html>
        <html>
          <head>
            <title>ReturnPilot Platform</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <style>
              body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #020617; color: #f8fafc; padding: 40px; }
              a { color: #818cf8; text-decoration: none; }
              a:hover { text-decoration: underline; }
              .card { background: #0f172a; padding: 24px; border-radius: 12px; border: 1px solid #1e293b; max-width: 600px; margin-top: 20px; }
            </style>
          </head>
          <body>
            <h1>ReturnPilot Platform</h1>
            <p>AI-powered eCommerce returns management platform with MCP server and LangGraph ReAct agent.</p>
            <div class="card">
              <h3>Service Endpoints</h3>
              <ul>
                <li><a href="/api/">REST API Root (/api/)</a></li>
                <li><a href="/admin/">Django Admin Portal (/admin/)</a></li>
                <li><a href="/api/analytics/">Returns Analytics API (/api/analytics/)</a></li>
              </ul>
              <p style="font-size: 13px; color: #94a3b8; margin-top: 16px;">
                To run the frontend dev server: <code>cd frontend && npm run dev</code> (http://localhost:5173).
              </p>
            </div>
          </body>
        </html>
        """
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    re_path(r"^(?!admin|api|static).*$", serve_spa),
]
