"""
Enhanced data analysis tools for integration with LangChain
"""
import logging
import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Union

# Import ML components
from ml.data.data_processor import DataProcessor
from ml.data.data_validator import DataValidator
from ml.analysis.analyzer import DataAnalyzer
from ml.visualization.charts import ChartGenerator
from ml.visualization.insights import InsightGenerator
from ml.visualization.recommender import ChartRecommender

# PostgreSQL connection
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class DataAnalysisTools:
    """
    Tools for data analysis with LangChain integration
    """
    
    def __init__(self,  db_connection_string: Optional[str] = None):
        """
        Initialize data analysis tools
        
        Args:
            db_connection_string: PostgreSQL connection string
        """
        # Set default connection string if not provided
        self.db_connection_string = db_connection_string or "postgresql://ecommerce:ecommerce@localhost:5432/datasense"
        
        # Initialize ML components
        self.data_processor = DataProcessor()
        self.data_validator = DataValidator()
        self.data_analyzer = DataAnalyzer()
        self.chart_generator = ChartGenerator()
        self.insight_generator = InsightGenerator()
        self.chart_recommender = ChartRecommender()
        
        logger.info("DataAnalysisTools initialized")
    
    def process_data(self, data: Union[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Process data using DataProcessor
        
        Args:
            data: Data to process (DataFrame or path to file)
            
        Returns:
            pd.DataFrame: Processed DataFrame
        """
        try:
            df = self._load_data(data)
            
            # Process data
            processed_df = self.data_processor.process(df)
            
            return processed_df
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}", exc_info=True)
            raise
    
    def validate_data(self, data: Union[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Validate data using DataValidator
        
        Args:
            data: Data to validate (DataFrame or path to file)
            
        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            df = self._load_data(data)
            
            # Validate data
            validation_results = self.data_validator.validate_dataset(df)
            
            return validation_results
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}", exc_info=True)
            raise
    
    def analyze_data(self, data: Union[str, pd.DataFrame], analysis_type: str = "full") -> Dict[str, Any]:
        """
        Analyze data using DataAnalyzer
        
        Args:
            data: Data to analyze (DataFrame or path to file)
            analysis_type: Type of analysis to perform
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            df = self._load_data(data)
            
            # Analyze data
            analysis_results = self.data_analyzer.run_analysis(df, analysis_type=analysis_type)
            
            return analysis_results
        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}", exc_info=True)
            raise
    
    def generate_visualizations(
        self, 
        data: Union[str, pd.DataFrame], 
        columns: Optional[List[str]] = None,
        chart_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate visualizations
        
        Args:
            data: Data to visualize (DataFrame or path to file)
            columns: Columns to visualize
            chart_type: Type of chart to generate
            
        Returns:
            List[Dict[str, Any]]: Visualization specifications
        """
        try:
            df = self._load_data(data)
            
            # Filter columns if provided
            if columns:
                valid_columns = [col for col in columns if col in df.columns]
                if valid_columns:
                    df = df[valid_columns]
            
            # Generate visualizations using ChartGenerator
            chart_types = [chart_type] if chart_type else None
            visualizations = self.chart_generator.generate_automatic_charts(df, chart_types=chart_types)
            
            return visualizations
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}", exc_info=True)
            raise
    
    def generate_insights(
        self, 
        data: Union[str, pd.DataFrame], 
        insight_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate insights
        
        Args:
            data: Data to analyze (DataFrame or path to file)
            insight_types: Types of insights to generate
            
        Returns:
            List[Dict[str, Any]]: Generated insights
        """
        try:
            df = self._load_data(data)
            
            # Generate insights using InsightGenerator
            insights = self.insight_generator.generate_rule_based_insights(df, None, insight_types)
            
            return insights
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}", exc_info=True)
            raise
    
    def recommend_charts(
        self, 
        data: Union[str, pd.DataFrame], 
        columns: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Recommend charts based on data
        
        Args:
            data: Data to analyze (DataFrame or path to file)
            columns: Columns to consider
            
        Returns:
            Dict[str, Dict[str, Any]]: Chart recommendations
        """
        try:
            df = self._load_data(data)
            
            # Get chart recommendations
            recommendations = self.chart_recommender.recommend_charts(df, columns)
            
            return recommendations
        except Exception as e:
            logger.error(f"Error recommending charts: {str(e)}", exc_info=True)
            raise
    
    def get_best_charts(
        self, 
        data: Union[str, pd.DataFrame], 
        columns: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get best chart recommendations
        
        Args:
            data: Data to analyze (DataFrame or path to file)
            columns: Columns to consider
            top_k: Number of top charts to return
            
        Returns:
            List[Dict[str, Any]]: Best chart recommendations
        """
        try:
            df = self._load_data(data)
            
            # Get best charts
            best_charts = self.chart_recommender.get_best_charts(df, columns, top_k)
            
            return best_charts
        except Exception as e:
            logger.error(f"Error getting best charts: {str(e)}", exc_info=True)
            raise
    
    def execute_sql(self, query: str) -> Union[List[Dict[str, Any]], str]:
        """
        Execute SQL query on PostgreSQL database
        
        Args:
            query: SQL query
            
        Returns:
            Union[List[Dict[str, Any]], str]: Query results or error message
        """
        try:
            # Connect to database
            conn = psycopg2.connect(self.db_connection_string)
            
            # Create cursor with dictionary results
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Execute query
            cursor.execute(query)
            
            # Fetch results
            results = cursor.fetchall()
            
            # Close cursor and connection
            cursor.close()
            conn.close()
            
            # Convert to list of dicts
            result_list = [dict(row) for row in results]
            
            return result_list
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def describe_tables(self) -> Dict[str, Dict[str, Any]]:
        """
        Get description of tables in PostgreSQL database
        
        Returns:
            Dict[str, Dict[str, Any]]: Table descriptions
        """
        try:
            # Connect to database
            conn = psycopg2.connect(self.db_connection_string)
            
            # Create cursor
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            
            # Get schema for each table
            result = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                
                # Format table schema
                result[table_name] = {
                    "columns": {}
                }
                
                for col in columns:
                    col_name, col_type, is_nullable = col
                    result[table_name]["columns"][col_name] = {
                        "type": col_type,
                        "nullable": is_nullable
                    }
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                result[table_name]["row_count"] = count
                
                # Get primary key if any
                cursor.execute(f"""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = '{table_name}'::regclass
                    AND i.indisprimary;
                """)
                
                primary_keys = cursor.fetchall()
                if primary_keys:
                    result[table_name]["primary_key"] = [pk[0] for pk in primary_keys]
            
            # Close cursor and connection
            cursor.close()
            conn.close()
            
            return result
        except Exception as e:
            logger.error(f"Error describing tables: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def get_table_sample(self, table_name: str, limit: int = 10) -> Union[List[Dict[str, Any]], str]:
        """
        Get sample data from table
        
        Args:
            table_name: Table name
            limit: Maximum number of rows to return
            
        Returns:
            Union[List[Dict[str, Any]], str]: Sample data or error message
        """
        try:
            # Connect to database
            conn = psycopg2.connect(self.db_connection_string)
            
            # Create cursor with dictionary results
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Execute query
            query = sql.SQL("SELECT * FROM {} LIMIT %s").format(sql.Identifier(table_name))
            cursor.execute(query, (limit,))
            
            # Fetch results
            results = cursor.fetchall()
            
            # Close cursor and connection
            cursor.close()
            conn.close()
            
            # Convert to list of dicts
            result_list = [dict(row) for row in results]
            
            return result_list
        except Exception as e:
            logger.error(f"Error getting table sample: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _load_data(self, data: Union[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Load data from various sources
        
        Args:
            data: Data source (DataFrame, path, or JSON string)
            
        Returns:
            pd.DataFrame: Loaded DataFrame
        """
        if isinstance(data, pd.DataFrame):
            return data
        
        if isinstance(data, str):
            # Check if it's a file path
            if os.path.exists(data):
                # Determine file type from extension
                if data.endswith('.csv'):
                    return pd.read_csv(data)
                elif data.endswith('.xlsx') or data.endswith('.xls'):
                    return pd.read_excel(data)
                elif data.endswith('.json'):
                    return pd.read_json(data)
                else:
                    # Try CSV as default
                    return pd.read_csv(data)
            
            # Try to parse as JSON string
            try:
                data_dict = json.loads(data)
                if isinstance(data_dict, list):
                    return pd.DataFrame(data_dict)
                elif isinstance(data_dict, dict):
                    return pd.DataFrame([data_dict])
                else:
                    raise ValueError("Invalid JSON data structure")
            except:
                # Try to parse as CSV string
                try:
                    import io
                    return pd.read_csv(io.StringIO(data))
                except:
                    raise ValueError("Could not parse data as JSON or CSV")
        
        raise ValueError("Unsupported data type")