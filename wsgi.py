from app import create_app
from app.features.claude.main_core import open_with_cairn

app = create_app()
open_with_cairn(app)
