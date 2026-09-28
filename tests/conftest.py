import pytest

# imports dentro das fixtures: os testes unitários não podem carregar o SQLAlchemy


@pytest.fixture
def in_memory_db():
    from sqlalchemy import create_engine

    from rocketicket.adapters import orm

    engine = create_engine("sqlite://")
    orm.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(in_memory_db):
    from sqlalchemy.orm import clear_mappers, sessionmaker

    from rocketicket.adapters import orm

    orm.start_mappers()
    sessao = sessionmaker(bind=in_memory_db)()
    yield sessao
    sessao.close()
    clear_mappers()
