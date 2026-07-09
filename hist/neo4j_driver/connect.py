"""Hist Neo4j driver — singleton connection management + session helpers."""

from neo4j import GraphDatabase, basic_auth
from hist.config import HIST_NEO4J_URI, HIST_NEO4J_USER, HIST_NEO4J_PASSWORD, HIST_DB_NAME


class HistDriver:
    """Lazy-connect, reusable Neo4j driver targeting the 'hist' DB."""

    _driver = None

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            auth = basic_auth(HIST_NEO4J_USER, HIST_NEO4J_PASSWORD)
            cls._driver = GraphDatabase.driver(HIST_NEO4J_URI, auth=auth)
        return cls._driver

    @classmethod
    def get_session(cls):
        """Return a session on the 'hist' database."""
        driver = cls.get_driver()
        return driver.session(database=HIST_DB_NAME)

    @classmethod
    def close_all(cls):
        if cls._driver:
            cls._driver.close()
            cls._driver = None


def run_cypher(query, params=None):
    """Execute a Cypher statement and return list of dicts."""
    session = HistDriver.get_session()
    result = session.run(query, params or {})
    records = [dict(r) for r in result]
    session.close()
    return records


def run_cypher_single(query, params=None):
    """Execute a Cypher statement and return single record as dict."""
    session = HistDriver.get_session()
    result = session.run(query, params or {})
    record = dict(result.single())
    session.close()
    return record
