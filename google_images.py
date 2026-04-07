"""
Google Lens reverse-image search.

Opens Google Lens in the browser. The user is expected to paste the image
from their clipboard once the page loads (Ctrl+V / Cmd+V).
"""

import webbrowser


def open_google_lens(image_path: str = ""):
    """Open Google Lens — paste the image from clipboard once the page loads."""
    webbrowser.open("https://lens.google.com")
