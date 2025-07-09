"""Custom document loader for PostgreSQL bulletin board data."""

from typing import Iterator, Optional

import psycopg2
from langchain_core.document_loaders.base import BaseLoader
from langchain_core.documents import Document

from app.core.config import settings


class PostgresResLoader(BaseLoader):
    """Load bulletin board posts from PostgreSQL database."""

    def __init__(
        self,
        connection_string: Optional[str] = None,
        query: Optional[str] = None,
        start_no: Optional[int] = None,
        end_no: Optional[int] = None,
    ):
        """Initialize the loader.

        Args:
            connection_string: PostgreSQL connection string
            query: Custom SQL query to fetch data
            start_no: Starting post number (inclusive)
            end_no: Ending post number (inclusive)
        """
        self.connection_string = connection_string or settings.database_url

        if query:
            self.query = query
        else:
            # Default query to fetch all posts
            base_query = """
                SELECT no, name_and_trip, datetime, id, main_text
                FROM public.res
            """

            conditions = []
            if start_no is not None:
                conditions.append(f"no >= {start_no}")
            if end_no is not None:
                conditions.append(f"no <= {end_no}")

            if conditions:
                self.query = f"{base_query} WHERE {' AND '.join(conditions)}"
            else:
                self.query = base_query

            self.query += " ORDER BY no ASC"

    def lazy_load(self) -> Iterator[Document]:
        """Lazily load documents from the database."""
        connection = None
        cursor = None

        try:
            connection = psycopg2.connect(self.connection_string)
            cursor = connection.cursor()

            cursor.execute(self.query)

            for row in cursor:
                no, name_and_trip, datetime_val, post_id, main_text = row

                # Create document with metadata
                metadata = {
                    "no": no,
                    "id": post_id,
                    "datetime": datetime_val.isoformat() if datetime_val else "",
                    "name_and_trip": name_and_trip,
                    "source": f"res_no_{no}",
                }

                # Use main_text as the content
                document = Document(
                    page_content=main_text,
                    metadata=metadata,
                )

                yield document

        except Exception as e:
            raise Exception(f"Error loading documents from PostgreSQL: {e}")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def load(self) -> list[Document]:
        """Load all documents at once."""
        return list(self.lazy_load())
