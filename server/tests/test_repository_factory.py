from app.repositories.factory import get_repository
from app.repositories.in_memory import InMemoryRepository


def test_repository_factory_defaults_to_memory():
    repo = get_repository()
    assert isinstance(repo, InMemoryRepository)
