"""Server entry point for legacy-fixture — delegates to the application factory."""
from legacy_fixture.application.app import start_server

if __name__ == "__main__":
    start_server()
