"""Shared test config: allow the app to boot with the dev default key."""

import os

# The app now fails closed on the default orchestrator key; tests opt in to the
# local-dev escape hatch so importing app.main works.
os.environ.setdefault("ALLOW_DEFAULT_KEY", "1")
os.environ.setdefault("ENVIRONMENT", "dev")
