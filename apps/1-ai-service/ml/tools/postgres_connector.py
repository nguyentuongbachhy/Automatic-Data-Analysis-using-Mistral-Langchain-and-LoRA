"""
PostgreSQL integration for LangChain and data analysis
"""
import logging
import json
from typing import Dict, List, Any, Optional, Union, Tuple

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class PostgreSQLConnector:
    """
    PostgreSQL connector for data analysis
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize connector
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string or "postgresql://ecommerce:ecommerce@localhost:5432/datasense"
        
        # Test connection
        try:
            self._test_connection()
            logger.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL database: {str(e)}", exc_info=True)
            raise
    
    def _test_connection(self):
        """Test database connection"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.close()
        except Exception as e:
            raise Exception(f"Failed to connect to PostgreSQL database: {str(e)}")
        finally:
            if conn is not None:
                conn.close()
    
    def execute_query(self, query: str, params: List = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Execute SQL query
        
        Args:
            query: SQL query
            params: Query parameters (optional)

        Returns:
            Tuple[List[Dict[str, Any]], List[str]]: Query results and column names
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get column names
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch results
            results = cursor.fetchall()
            
            # Convert to list of dicts
            result_list = [dict(row) for row in results]
            
            cursor.close()
            
            return result_list, column_names
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}", exc_info=True)
            raise
        finally:
            if conn is not None:
                conn.close()

    def insert(self, table_name: str, data: Dict[str, Any]) -> bool:
        """
        Insert data into a specified table
        
        Args:
            table_name: Name of the table to insert data into
            data: A dictionary with column names as keys
        
        Returns:
            True if inserted successfully else False
        """
        conn = None
        try:
            # Validate input
            if not data or not isinstance(data, dict):
                logger.warning("Insert failed: Data must be a non-empty dictionary")
                return False

            # Remove None values to avoid inserting NULL for all columns
            data = {k: v for k, v in data.items() if v is not None}

            if not data:
                logger.warning("Insert failed: No valid data after removing None values")
                return False

            # Establish connection
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()

            # Prepare columns and values
            columns = list(data.keys())
            values = list(data.values())
            
            # Không dùng capitalize() nữa, giữ nguyên tên bảng và dùng sql.Identifier
            # Thêm dấu ngoặc kép cho tên bảng bằng sql.Identifier để tránh lỗi phân biệt hoa/thường

            # Construct insert query với sql.Identifier cho tên bảng và tên các cột
            insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(columns))
            )

            # Execute insert
            cursor.execute(insert_query, values)
            conn.commit()
            return True

        except psycopg2.Error as e:
            # More specific error handling
            if conn:
                conn.rollback()
            
            # Log different types of errors more specifically
            if isinstance(e, psycopg2.IntegrityError):
                logger.error(f"Integrity error inserting into {table_name}: {str(e)}")
            elif isinstance(e, psycopg2.DataError):
                logger.error(f"Data error inserting into {table_name}: {str(e)}")
            else:
                logger.error(f"Database error inserting into {table_name}: {str(e)}", exc_info=True)
            
            return False

        except Exception as e:
            # Catch-all for unexpected errors
            if conn:
                conn.rollback()
            logger.error(f"Unexpected error inserting into {table_name}: {str(e)}", exc_info=True)
            return False

        finally:
            # Ensure connection is closed
            if conn is not None:
                if 'cursor' in locals():
                    cursor.close()
                conn.close()

    def update(self, table_name: str, data: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """
        Update data in a specified table based on a condition
        
        Args:
            table_name: Name of the table to update
            data: Dictionary of columns and values to update
            condition: Dictionary of conditions for the WHERE clause
        
        Returns:
            True if updated successfully, False otherwise
        """
        conn = None
        try:
            # Validate inputs
            if not data or not isinstance(data, dict):
                logger.warning("Update failed: Data must be a non-empty dictionary")
                return False
            
            if not condition or not isinstance(condition, dict):
                logger.warning("Update failed: Condition must be a non-empty dictionary")
                return False

            # Remove None values from data to avoid unnecessary updates
            data = {k: v for k, v in data.items() if v is not None}

            if not data:
                logger.warning("Update failed: No valid data to update")
                return False

            # Establish connection
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()

            # Cải tiến: Sử dụng SQL composables cho cả câu lệnh
            # Tạo mệnh đề SET với sql.Identifier cho tên cột
            set_items = []
            set_values = []
            for k, v in data.items():
                set_items.append(sql.SQL("{} = %s").format(sql.Identifier(k)))
                set_values.append(v)

            # Tạo mệnh đề WHERE với sql.Identifier cho tên cột
            where_items = []
            where_values = []
            for k, v in condition.items():
                where_items.append(sql.SQL("{} = %s").format(sql.Identifier(k)))
                where_values.append(v)

            # Xây dựng câu lệnh SQL hoàn chỉnh
            update_query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
                sql.Identifier(table_name),
                sql.SQL(", ").join(set_items),
                sql.SQL(" AND ").join(where_items)
            )

            # Kết hợp tất cả giá trị cho câu lệnh
            all_values = set_values + where_values

            # Thực thi truy vấn cập nhật
            cursor.execute(update_query, all_values)
            
            # Kiểm tra số dòng được cập nhật
            rows_affected = cursor.rowcount
            conn.commit()

            if rows_affected == 0:
                logger.warning(f"No rows updated in {table_name}. Condition might not match any records.")
                return False

            return True

        except psycopg2.Error as e:
            # More specific error handling for PostgreSQL errors
            if conn:
                conn.rollback()
            
            if isinstance(e, psycopg2.IntegrityError):
                logger.error(f"Integrity error updating {table_name}: {str(e)}")
            elif isinstance(e, psycopg2.DataError):
                logger.error(f"Data error updating {table_name}: {str(e)}")
            else:
                logger.error(f"Database error updating {table_name}: {str(e)}", exc_info=True)
            
            return False

        except Exception as e:
            # Catch-all for unexpected errors
            if conn:
                conn.rollback()
            logger.error(f"Unexpected error updating {table_name}: {str(e)}", exc_info=True)
            return False

        finally:
            # Ensure connection is closed
            if conn is not None:
                if 'cursor' in locals():
                    cursor.close()
                conn.close()

    def select(self, table_name: str, columns: List[str] = None, 
            conditions: Dict[str, Any] = None, order_by: str = None, 
            limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """
        Perform a SELECT query from a database table
        Args:
            table_name: Name of the table to query
            columns: List of columns to retrieve, defaults to all (*)
            conditions: Dictionary of conditions for the WHERE clause
            order_by: Sorting string (e.g., "id DESC")
            limit: Maximum number of records to return
            offset: Starting position for data retrieval

        Returns:
            List[Dict[str, Any]]: Query result as a list of dictionaries
        """
        conn = None
        try:
            # Xây dựng câu truy vấn SQL an toàn bằng sql.SQL và sql.Identifier
            parts = [sql.SQL("SELECT")]
            
            # Xử lý columns
            if columns and isinstance(columns, list) and len(columns) > 0:
                cols_sql = sql.SQL(", ").join(map(sql.Identifier, columns))
                parts.append(cols_sql)
            else:
                parts.append(sql.SQL("*"))
            
            # Thêm FROM clause
            parts.append(sql.SQL("FROM {}").format(sql.Identifier(table_name)))
            
            # Xử lý WHERE clause
            params = []
            if conditions and isinstance(conditions, dict) and len(conditions) > 0:
                where_parts = []
                
                for key, value in conditions.items():
                    if isinstance(value, (list, tuple)):
                        # Xử lý IN condition
                        placeholders = sql.SQL(", ").join([sql.Placeholder()] * len(value))
                        where_parts.append(
                            sql.SQL("{} IN ({})").format(sql.Identifier(key), placeholders)
                        )
                        params.extend(value)
                    elif isinstance(value, dict) and len(value) == 1:
                        # Xử lý các toán tử so sánh (>, <, >=, <=, !=)
                        op = list(value.keys())[0]
                        val = value[op]
                        where_parts.append(
                            sql.SQL("{} {} {}").format(sql.Identifier(key), sql.SQL(op), sql.Placeholder())
                        )
                        params.append(val)
                    else:
                        # Mặc định là so sánh bằng
                        where_parts.append(
                            sql.SQL("{} = {}").format(sql.Identifier(key), sql.Placeholder())
                        )
                        params.append(value)
                
                if where_parts:
                    parts.append(sql.SQL("WHERE ") + sql.SQL(" AND ").join(where_parts))
            
            # Xử lý ORDER BY
            if order_by:
                # Phân tích chuỗi order_by
                order_parts = order_by.split()
                if len(order_parts) >= 1:
                    column = order_parts[0]
                    direction = " ".join(order_parts[1:]) if len(order_parts) > 1 else ""
                    
                    # Tạo mệnh đề ORDER BY
                    order_sql = sql.SQL("ORDER BY {} {}").format(
                        sql.Identifier(column), 
                        sql.SQL(direction)
                    )
                    parts.append(order_sql)
            
            # Xử lý LIMIT và OFFSET
            if limit is not None:
                parts.append(sql.SQL("LIMIT {}").format(sql.Placeholder()))
                params.append(limit)
            
            if offset is not None:
                parts.append(sql.SQL("OFFSET {}").format(sql.Placeholder()))
                params.append(offset)
            
            # Kết hợp tất cả các phần thành một câu truy vấn hoàn chỉnh
            query = sql.SQL(" ").join(parts)
            
            # Thực hiện truy vấn
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Log truy vấn cho debug
            logger.debug(f"Executing query: {query.as_string(cursor)} with params: {params}")
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Chuyển đổi kết quả thành list of dicts
            result_list = [dict(row) for row in results]
            
            cursor.close()
            
            return result_list
        
        except Exception as e:
            logger.error(f"Error executing SELECT query on table {table_name}: {str(e)}", exc_info=True)
            raise
        
        finally:
            if conn is not None:
                conn.close()

    def delete(self, table_name: str, conditions: Dict[str, Any]) -> bool:
        """
        Perform a DELETE query from a database table with conditions
        
        Args:
            table_name: Name of the table to query
            conditions: Dictionary of conditions for the WHERE clause
        
        Returns:
            bool: True if deleted successfully else False
        """
        conn = None
        try:
            # Validate input
            if not conditions or not isinstance(conditions, dict):
                logger.warning("Delete failed: Conditions must be a non-empty dictionary")
                return False
            
            # Establish connection
            conn = psycopg2.connect(self.connection_string)
            conn.autocommit = False
            cursor = conn.cursor()
            
            # Xây dựng các mệnh đề WHERE
            where_items = []
            where_values = []
            for k, v in conditions.items():
                where_items.append(sql.SQL("{} = %s").format(sql.Identifier(k)))
                where_values.append(v)
            
            # Xây dựng câu lệnh DELETE hoàn chỉnh
            delete_query = sql.SQL("DELETE FROM {} WHERE {}").format(
                sql.Identifier(table_name),
                sql.SQL(" AND ").join(where_items)
            )
            
            # Thực thi truy vấn xóa
            cursor.execute(delete_query, where_values)
            
            # Kiểm tra số dòng bị ảnh hưởng
            rows_affected = cursor.rowcount
            conn.commit()
            
            logger.info(f"Deleted {rows_affected} rows from table {table_name}")
            
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error deleting from {table_name}: {str(e)}", exc_info=True)
            return False
        
        finally:
            if conn is not None:
                if 'cursor' in locals():
                    cursor.close()
                conn.close()
    
    def get_tables(self) -> List[str]:
        """
        Get list of tables in database
        
        Returns:
            List[str]: Table names
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            
            cursor.close()
            
            return [table[0] for table in tables]
        except Exception as e:
            logger.error(f"Error getting tables: {str(e)}", exc_info=True)
            raise
        finally:
            if conn is not None:
                conn.close()
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get schema for table
        
        Args:
            table_name: Table name
            
        Returns:
            Dict[str, Any]: Table schema
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Get columns
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            
            # Get primary key if any
            cursor.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                AND i.indisprimary;
            """, (table_name,))
            
            primary_keys = cursor.fetchall()
            
            # Get foreign keys if any
            cursor.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM
                    information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s;
            """, (table_name,))
            
            foreign_keys = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            
            cursor.close()
            
            # Format result
            schema = {
                "table_name": table_name,
                "row_count": count,
                "columns": [],
                "primary_keys": [pk[0] for pk in primary_keys],
                "foreign_keys": []
            }
            
            for column in columns:
                schema["columns"].append({
                    "name": column[0],
                    "type": column[1],
                    "nullable": column[2]
                })
            
            for fk in foreign_keys:
                schema["foreign_keys"].append({
                    "column": fk[0],
                    "foreign_table": fk[1],
                    "foreign_column": fk[2]
                })
            
            return schema
        except Exception as e:
            logger.error(f"Error getting table schema: {str(e)}", exc_info=True)
            raise
        finally:
            if conn is not None:
                conn.close()
    
    def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get sample data from table
        
        Args:
            table_name: Table name
            limit: Maximum number of rows to return
            
        Returns:
            List[Dict[str, Any]]: Sample data
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = sql.SQL("SELECT * FROM {} LIMIT %s").format(sql.Identifier(table_name))
            cursor.execute(query, (limit,))
            
            results = cursor.fetchall()
            
            cursor.close()
            
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting table sample: {str(e)}", exc_info=True)
            raise
        finally:
            if conn is not None:
                conn.close()
    
    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        """
        Execute query and return results as DataFrame
        
        Args:
            query: SQL query
            
        Returns:
            pd.DataFrame: Query results
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            
            # Execute query
            df = pd.read_sql_query(query, conn)
            
            return df
        except Exception as e:
            logger.error(f"Error executing query to DataFrame: {str(e)}", exc_info=True)
            raise
        finally:
            if conn is not None:
                conn.close()

# LangChain Tools for PostgreSQL

class PostgreSQLQueryTool(BaseTool):
    """Tool for executing SQL queries"""
    
    name: str = "postgresql_query"
    description: str = """
    Execute SQL queries on the PostgreSQL database.
    Input should be a valid SQL query string.
    Returns the results of the query.
    Use this tool when you need to retrieve or manipulate data in the database.
    """
    
    def __init__(self, connector: Optional[Union[str, PostgreSQLConnector]] = None):
        """Initialize tool with connector"""
        super().__init__()
        
        # Handle different input types
        if connector is None:
            self._connector = PostgreSQLConnector()
        elif isinstance(connector, str):
            self._connector = PostgreSQLConnector(connector)
        elif isinstance(connector, PostgreSQLConnector):
            self._connector = connector
        else:
            raise ValueError(f"Invalid connector type: {type(connector)}")

    def _run(self, query: str) -> str:
        """Execute SQL query"""
        try:
            # Execute query
            results, _ = self._connector.execute_query(query)
            
            # Format results
            if not results:
                return "Query executed successfully. No results returned."
            
            # Limit output size for large result sets
            if len(results) > 20:
                result_str = json.dumps(results[:20], indent=2, default=str)
                return f"{result_str}\n\n(Showing 20 of {len(results)} results)"
            else:
                return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return f"Error executing query: {str(e)}"

class PostgreSQLSchemaTool(BaseTool):
    """Tool for getting database schema information"""
    
    name: str = "postgresql_schema"
    description: str = """
    Get schema information about the PostgreSQL database.
    Input can be empty for a list of all tables, or a specific table name for detailed schema.
    Returns information about tables, columns, and relationships.
    Use this tool when you need to understand the database structure.
    """
    
    def __init__(self, connector: Optional[Union[str, PostgreSQLConnector]] = None):
        """Initialize tool with connector"""
        super().__init__()
        
        # Handle different input types
        if connector is None:
            self._connector = PostgreSQLConnector()
        elif isinstance(connector, str):
            self._connector = PostgreSQLConnector(connector)
        elif isinstance(connector, PostgreSQLConnector):
            self._connector = connector
        else:
            raise ValueError(f"Invalid connector type: {type(connector)}")

    def _run(self, table_name: str = "") -> str:
        """Get schema information"""
        try:
            if not table_name:
                # Get list of all tables
                tables = self._connector.get_tables()
                return f"Tables in database:\n{', '.join(tables)}"
            else:
                # Get schema for specific table
                schema = self._connector.get_table_schema(table_name)
                return json.dumps(schema, indent=2)
        except Exception as e:
            return f"Error getting schema information: {str(e)}"

class PostgreSQLSampleTool(BaseTool):
    """Tool for getting sample data from a table"""
    
    name: str = "postgresql_sample"
    description: str = """
    Get sample data from a table in the PostgreSQL database.
    Input should be a table name.
    Returns a few sample rows from the table.
    Use this tool when you need to see example data from a table.
    """
    
    def __init__(self, connector: Optional[Union[str, PostgreSQLConnector]] = None):
        """Initialize tool with connector"""
        super().__init__()
        
        # Handle different input types
        if connector is None:
            self._connector = PostgreSQLConnector()
        elif isinstance(connector, str):
            self._connector = PostgreSQLConnector(connector)
        elif isinstance(connector, PostgreSQLConnector):
            self._connector = connector
        else:
            raise ValueError(f"Invalid connector type: {type(connector)}")

    def _run(self, table_name: str) -> str:
        """Get sample data from table"""
        try:
            # Get sample data
            sample = self._connector.get_table_sample(table_name)
            
            if not sample:
                return f"Table '{table_name}' exists but has no data."
            
            return json.dumps(sample, indent=2, default=str)
        except Exception as e:
            return f"Error getting sample data: {str(e)}"