import json
import os
import sys

# Agregar el directorio raíz al PATH para poder importar la aplicación correctamente
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from fastapi.openapi.utils import get_openapi
    from app.main import app
except ImportError as e:
    print(f"Error al importar dependencias. ¿Está activado el entorno virtual? Detalles: {e}")
    sys.exit(1)

def main():
    print("Extracting OpenAPI schema from FastAPI...")
    
    # Generar el esquema OpenAPI
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    # 1. Guardar como openapi.json
    json_path = "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Schema saved to: {os.path.abspath(json_path)}")

    # 2. Generar Swagger UI auto-contenido
    swagger_path = "swagger_docs.html"
    swagger_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>{app.title} - Swagger UI</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #f7f9fc;
    }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = () => {{
      window.ui = SwaggerUIBundle({{
        spec: {json.dumps(openapi_schema, ensure_ascii=False)},
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        layout: "StandaloneLayout"
      }});
    }};
  </script>
</body>
</html>
"""
    with open(swagger_path, "w", encoding="utf-8") as f:
        f.write(swagger_html)
    print(f"  [OK] Standalone Swagger UI saved to: {os.path.abspath(swagger_path)}")

    # 3. Generar ReDoc auto-contenido (diseño alternativo muy limpio)
    redoc_path = "redoc_docs.html"
    redoc_html = f"""<!DOCTYPE html>
<html>
  <head>
    <title>{app.title} - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
      body {{
        margin: 0;
        padding: 0;
      }}
    </style>
  </head>
  <body>
    <div id="redoc-container"></div>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"> </script>
    <script>
      Redoc.init({json.dumps(openapi_schema, ensure_ascii=False)}, {{}}, document.getElementById('redoc-container'))
    </script>
  </body>
</html>
"""
    with open(redoc_path, "w", encoding="utf-8") as f:
        f.write(redoc_html)
    print(f"  [OK] Standalone ReDoc saved to: {os.path.abspath(redoc_path)}")

    print("\n[INFO] Ready! You can share the HTML files directly. They will open in any browser and load the interactive documentation without needing the backend running.")

if __name__ == "__main__":
    main()
