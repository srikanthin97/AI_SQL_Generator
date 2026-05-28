import os
from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
import logging

# Configure logger
logger = logging.getLogger("ai_sql_generator.database")
logging.basicConfig(level=logging.INFO)

class SQLiteConfig(BaseModel):
    db_path: str = Field(..., description="Path to SQLite database file or ':memory:'")

class PostgreSQLConfig(BaseModel):
    host: str = Field("localhost", description="Database host address")
    port: int = Field(5432, description="Database port number")
    user: str = Field(..., description="Database user username")
    password: str = Field(..., description="Database user password")
    database: str = Field(..., description="Database name")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

class DatabaseConnectionManager:
    """Manages secure connections and session states for SQLite and PostgreSQL databases."""
    
    def __init__(self, config: Union[SQLiteConfig, PostgreSQLConfig]):
        self.config = config
        self._engine: Optional[Engine] = None
        self._SessionLocal: Optional[sessionmaker] = None

    @property
    def connection_url(self) -> str:
        """Generates the appropriate connection URL based on configuration type."""
        if isinstance(self.config, SQLiteConfig):
            # For SQLite, ensure 3 slashes for relative path, 4 slashes for absolute path
            path = self.config.db_path
            if path == ":memory:":
                return "sqlite:///:memory:"
            # Standardize path
            return f"sqlite:///{path}"
        elif isinstance(self.config, PostgreSQLConfig):
            return f"postgresql://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"
        else:
            raise TypeError("Unsupported database configuration type")

    def connect(self) -> Engine:
        """Initializes and returns the SQLAlchemy Engine, or returns the existing one."""
        if self._engine is not None:
            return self._engine
        
        url = self.connection_url
        try:
            # For SQLite, enable foreign key constraint support and avoid multi-threading locking issues
            if isinstance(self.config, SQLiteConfig):
                self._engine = create_engine(
                    url, 
                    connect_args={"check_same_thread": False} if url != "sqlite:///:memory:" else {}
                )
                
                # Register event to enforce SQLite foreign keys
                from sqlalchemy import event
                @event.listens_for(self._engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
            else:
                # PostgreSQL engine setup with pool settings
                self._engine = create_engine(
                    url,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    pool_size=5,
                    max_overflow=10
                )
            
            self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
            logger.info("Successfully created database engine.")
            return self._engine
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise ConnectionError(f"Could not connect to database: {e}")

    def test_connection(self) -> bool:
        """Executes a simple query ('SELECT 1') to validate active connection status."""
        engine = self.connect()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                if result == 1:
                    logger.info("Connection test passed.")
                    return True
                return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_session(self) -> Session:
        """Yields a database session, ensuring it is properly closed after use."""
        if self._SessionLocal is None:
            self.connect()
        session = self._SessionLocal()
        try:
            return session
        except Exception as e:
            session.close()
            raise e

    def close(self) -> None:
        """Disposes of the database engine connection pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._SessionLocal = None
            logger.info("Database connection closed.")
