"""Hist Neo4j driver — singleton connection management + session helpers."""

from neo4j import GraphDatabase, basic_auth
import hist.config as config


import logging

# Suppress DBMS missing label/property schema notifications on empty database
logging.getLogger("neo4j").setLevel(logging.ERROR)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

class HistDriver:
    """Lazy-connect, reusable Neo4j driver targeting the Neo4j database."""

    _driver = None
    _cached_auth = None

    @classmethod
    def get_driver(cls):
        current_auth = (config.HIST_NEO4J_URI, config.HIST_NEO4J_USER, config.HIST_NEO4J_PASSWORD)
        if cls._driver is None or cls._cached_auth != current_auth:
            if cls._driver:
                try:
                    cls._driver.close()
                except Exception:
                    pass
            auth = basic_auth(config.HIST_NEO4J_USER, config.HIST_NEO4J_PASSWORD)
            
            # Pass notification filtering if supported by installed driver version
            driver_kwargs = {"auth": auth}
            try:
                from neo4j.api import NotificationSeverity
                driver_kwargs["notifications_min_severity"] = NotificationSeverity.OFF
            except (ImportError, AttributeError):
                pass

            cls._driver = GraphDatabase.driver(config.HIST_NEO4J_URI, **driver_kwargs)
            cls._cached_auth = current_auth
        return cls._driver

    @classmethod
    def get_session(cls):
        """Return a session on the target database, falling back to default session if needed."""
        driver = cls.get_driver()
        try:
            return driver.session(database=config.HIST_DB_NAME)
        except Exception:
            return driver.session()

    @classmethod
    def close_all(cls):
        if cls._driver:
            try:
                cls._driver.close()
            except Exception:
                pass
            cls._driver = None
            cls._cached_auth = None


def run_cypher(query, params=None):
    """Execute a Cypher statement and return list of dicts. Returns [] on connection error."""
    try:
        session = HistDriver.get_session()
        result = session.run(query, params or {})
        records = [dict(r) for r in result]
        session.close()
        return records
    except Exception as ex:
        # Reset driver cache on authentication or connection failures
        if "Unauthorized" in str(ex) or "AuthenticationRateLimit" in str(ex):
            HistDriver.close_all()
        print(f"[HIST Neo4j Warning] Database query failed: {ex}")
        return []


def run_cypher_single(query, params=None):
    """Execute a Cypher statement and return single record as dict. Returns {} on connection error."""
    try:
        session = HistDriver.get_session()
        result = session.run(query, params or {})
        record = dict(result.single()) if result else {}
        session.close()
        return record
    except Exception as ex:
        if "Unauthorized" in str(ex) or "AuthenticationRateLimit" in str(ex):
            HistDriver.close_all()
        print(f"[HIST Neo4j Warning] Single database query failed: {ex}")
        return {}
