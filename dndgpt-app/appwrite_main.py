"""Entrypoint selected in Appwrite Functions."""
if __package__:
    from .app.appwrite_entry import main
else:
    from app.appwrite_entry import main
