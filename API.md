# Data Analytics & ML Service API Documentation

This document provides detailed information about the API endpoints available in our data analytics and machine learning service. The system consists of several interconnected services that handle file processing, data analysis, visualization, and AI-powered Q&A capabilities.

## Table of Contents

1. [Authentication](#authentication)
2. [File Management](#file-management)
3. [Chat & Conversation](#chat--conversation)
4. [Data Analysis](#data-analysis)
5. [Visualization](#visualization)
6. [Time Series Analysis](#time-series-analysis)
7. [Advanced Analytics](#advanced-analytics)

## Authentication

### Register
- **Endpoint**: `POST /auth/register`
- **Description**: Create a new user account
- **Parameters**:
  - `email` (string): User's email address
  - `password` (string): User's password
  - `name` (string): User's name
- **Response**:
  - Success (201): User info and authentication token
  - Error (400): If email is already in use

### Login
- **Endpoint**: `POST /auth/login`
- **Description**: Authenticate and receive a token
- **Parameters**:
  - `email` (string): User's email address
  - `password` (string): User's password
- **Response**:
  - Success (200): User info and authentication token
  - Error (401): Invalid credentials

### Current User
- **Endpoint**: `GET /auth/me`
- **Description**: Get current user information
- **Authentication**: Required
- **Response**:
  - Success (200): User profile information
  - Error (404): User not found

## File Management

### Upload File
- **Endpoint**: `POST /files/upload`
- **Description**: Upload a CSV or XLSX file for analysis
- **Authentication**: Required
- **Parameters**:
  - `file` (form-data): The file to be uploaded
- **Response**:
  - Success (201): File ID and metadata
  - Error (400): Invalid file

### Get Files
- **Endpoint**: `GET /files`
- **Description**: Get a list of all files uploaded by the user
- **Authentication**: Required
- **Response**:
  - Success (200): List of files with metadata
  - Error (500): Server error

### Get File Details
- **Endpoint**: `GET /files/:id`
- **Description**: Get detailed information about a specific file
- **Authentication**: Required
- **Parameters**:
  - `id` (path): File ID
- **Response**:
  - Success (200): File details including analysis information
  - Error (404): File not found

### Delete File
- **Endpoint**: `DELETE /files/:id`
- **Description**: Delete a file
- **Authentication**: Required
- **Parameters**:
  - `id` (path): File ID
- **Response**:
  - Success (200): Confirmation message
  - Error (404): File not found

### Get File Summary
- **Endpoint**: `GET /files/:id/summary`
- **Description**: Get a summary of file analysis
- **Authentication**: Required
- **Parameters**:
  - `id` (path): File ID
- **Response**:
  - Success (200): Analysis summary
  - Pending (202): If analysis is still in progress
  - Error (404): File not found

## Chat & Conversation

### Process Message
- **Endpoint**: `POST /chat/message`
- **Description**: Process a chat message and get a response with ML integration
- **Authentication**: Required
- **Parameters**:
  - `user_id` (string): User identifier
  - `query` (string): The user's question or message
  - `messages` (array, optional): Previous messages in the conversation
  - `file_id` (string, optional): File ID if asking about data
  - `file_path` (string, optional): File path if asking about data
  - `use_cache` (boolean, default: true): Whether to use cached responses
- **Response**:
  - Success: AI response with optional visualizations and insights

### Stream Chat
- **Endpoint**: `GET /chat/stream`
- **Description**: Stream chat response token by token with asynchronous data analysis
- **Parameters**:
  - `query` (string): User query
  - `file_id` (string, optional): File ID for data processing
  - `file_path` (string, optional): File path for data processing
  - `user_id` (string, optional): User ID for conversation tracking
  - `chat_id` (string, optional): Chat ID for conversation tracking
  - `message_id` (string, optional): Message ID for tracking
  - `include_visualizations` (boolean, default: true): Include visualizations in response
  - `include_insights` (boolean, default: true): Include insights in response
- **Response**:
  - Server-Sent Events stream with tokens, visualizations, and insights

### Data Question
- **Endpoint**: `POST /chat/data-question`
- **Description**: Answer a specific data question with advanced ML analysis
- **Parameters**:
  - `user_id` (string): User identifier
  - `query` (string): The question about the data
  - `file_id` (string): File ID to analyze
  - `file_path` (string): File path to analyze
- **Response**:
  - Success: Detailed answer with analysis results

### Semantic Search
- **Endpoint**: `POST /chat/semantic-search`
- **Description**: Perform semantic search within data using ML embeddings
- **Parameters**:
  - `user_id` (string): User identifier
  - `query` (string): Search query
  - `file_id` (string): File ID to search in
  - `file_path` (string): File path to search in
  - `top_k` (query, default: 5): Number of results to return
- **Response**:
  - Success: Semantically relevant results from the data

### Detect Intent
- **Endpoint**: `POST /chat/intent-detect`
- **Description**: Detect user intent from query using ML
- **Parameters**:
  - `user_id` (string): User identifier
  - `query` (string): User query to analyze
  - `file_path` (string): File path for context
- **Response**:
  - Success: Detected intent information and confidence

### Chat History
- **Endpoint**: `GET /chat/history/{user_id}`
- **Description**: Get chat history for a specific user
- **Parameters**:
  - `user_id` (path): User ID to retrieve history for
- **Response**:
  - Success: List of conversation messages

### Clear Chat History
- **Endpoint**: `DELETE /chat/history/{user_id}`
- **Description**: Clear chat history for a specific user
- **Parameters**:
  - `user_id` (path): User ID to clear history for
- **Response**:
  - Success: Confirmation of cleared history

## Data Analysis

### Generate Insights
- **Endpoint**: `POST /analyze/insights`
- **Description**: Analyze data and generate insights using advanced ML techniques
- **Parameters**:
  - `fileId` (string): File ID to analyze
  - `filePath` (string): File path to analyze
  - `insight_types` (query, optional): Types of insights to generate
  - `target_columns` (query, optional): Specific columns to focus analysis on
- **Response**:
  - Success: List of insights with importance scores and descriptions

### Visualize Data
- **Endpoint**: `POST /analyze/visualize`
- **Description**: Create appropriate charts based on data attributes
- **Parameters**:
  - `fileId` (string): File ID to visualize
  - `filePath` (string): File path to visualize
  - `chart_types` (query, optional): Types of charts to create
  - `target_columns` (query, optional): Specific columns to visualize
  - `query` (query, optional): Natural language description of desired visualization
- **Response**:
  - Success: List of visualization configurations

### Predict
- **Endpoint**: `POST /analyze/predict`
- **Description**: Generate predictions based on data using ML models
- **Parameters**:
  - `fileId` (string): File ID for prediction
  - `filePath` (string): File path for prediction
  - `data` (object): Prediction configuration
    - `targetColumn` (string): Target column to predict
    - `featureColumns` (array): Feature columns to use
    - `modelType` (string): Type of model to use
- **Response**:
  - Success: Prediction results, metrics, and visualization

### Full Analysis
- **Endpoint**: `POST /analyze/full`
- **Description**: Perform comprehensive analysis of data including statistics, insights, and charts
- **Parameters**:
  - `fileId` (string): File ID to analyze
  - `filePath` (string): File path to analyze
  - `analysis_type` (query, default: "full"): Type of analysis
  - `query` (query, optional): Natural language query to guide analysis
- **Response**:
  - Success: Comprehensive analysis results

### Recommend Charts
- **Endpoint**: `POST /analyze/recommend-charts`
- **Description**: Suggest best chart types for the data
- **Parameters**:
  - `fileId` (string): File ID
  - `filePath` (string): File path
  - `columns` (query, optional): Specific columns to consider
  - `top_k` (query, default: 5): Number of recommendations to return
- **Response**:
  - Success: Chart recommendations with suitability scores

### Create Chart
- **Endpoint**: `POST /analyze/create-chart`
- **Description**: Create a specific chart based on provided parameters
- **Parameters**:
  - `fileId` (string): File ID
  - `filePath` (string): File path
  - `chart_type` (query): Type of chart (BAR, LINE, SCATTER, etc.)
  - `columns` (query): Columns to use in the chart
- **Response**:
  - Success: Chart configuration and data

## Time Series Analysis

### Time Series Analysis
- **Endpoint**: `POST /analyze/time-series`
- **Description**: Perform specialized time series analysis and forecasting
- **Parameters**:
  - `fileId` (string): File ID
  - `filePath` (string): File path
  - `data` (object): Configuration
    - `date_column` (string): Date/time column
    - `value_column` (string): Value column to analyze
    - `forecast` (boolean, optional): Whether to generate forecast
    - `forecast_periods` (number, optional): Number of periods to forecast
- **Response**:
  - Success: Time series analysis with optional forecast

### Time Series Forecast
- **Endpoint**: `POST /chat/time-series-forecast`
- **Description**: Generate time series forecast using advanced ML
- **Parameters**:
  - `user_id` (string): User identifier
  - `query` (string): Context query
  - `file_id` (string): File ID
  - `file_path` (string): File path
  - `date_column` (query): Date column name
  - `value_column` (query): Value column to forecast
  - `periods` (query, default: 10): Number of periods to forecast
  - `confidence_intervals` (query, default: true): Include confidence intervals
- **Response**:
  - Success: Forecast results with visualization

## Advanced Analytics

### Correlation Analysis
- **Endpoint**: `POST /analyze/correlation`
- **Description**: Analyze correlations between variables
- **Parameters**:
  - `fileId` (string): File ID
  - `filePath` (string): File path
  - `columns` (query, optional): Specific columns to analyze correlations
  - `threshold` (query, default: 0.3): Correlation strength threshold (0-1)
- **Response**:
  - Success: Correlation data and heatmap visualization

### Generate Visualizations
- **Endpoint**: `POST /chat/generate-visualization`
- **Description**: Create charts from data using integrated ML
- **Parameters**:
  - `user_id` (string): User identifier
  - `query` (string): Description of desired visualization
  - `file_id` (string): File ID
  - `file_path` (string): File path
  - `chart_type` (query, optional): Chart type to generate
  - `columns` (query, optional): Columns to use
- **Response**:
  - Success: Visualization configurations

### Generate Insights (Chat)
- **Endpoint**: `POST /chat/generate-insights`
- **Description**: Create insights from data using advanced ML
- **Parameters**:
  - `user_id` (string): User identifier
  - `query` (string): Context for insight generation
  - `file_id` (string): File ID
  - `file_path` (string): File path
  - `insight_types` (query, optional): Types of insights to generate
- **Response**:
  - Success: List of insights

### Asynchronous Analysis
- **Endpoint**: `POST /analyze/async/full`
- **Description**: Start a background task for comprehensive data analysis
- **Parameters**:
  - `fileId` (string): File ID
  - `filePath` (string): File path
  - `analysis_type` (query, default: "full"): Type of analysis
  - `query` (query, optional): Natural language query to guide analysis
- **Response**:
  - Success: Task ID and status

### Stream Analysis Progress
- **Endpoint**: `GET /analyze/stream/analysis/{file_id}`
- **Description**: Stream progress of a complex analysis operation
- **Parameters**:
  - `file_id` (path): File ID for analysis
  - `file_path` (query): File path for analysis
  - `analysis_type` (query, default: "full"): Type of analysis
  - `query` (query, optional): Natural language query to guide analysis
- **Response**:
  - Server-Sent Events with progress updates and results

## Response Format

All API responses follow a consistent structure:

```json
{
  "status": "success|error|pending",
  "data": { /* Response data */ },
  "error": "Error message if status is error",
  "meta": {
    /* Metadata about the request and response */
    "processing_time": 1.234,
    "timestamp": "2025-04-15T10:15:30Z"
  }
}
```

- For streaming endpoints, the response follows the Server-Sent Events (SSE) format.
- All timestamps are in ISO 8601 format.
- Numerical values use standard JSON number format.

## Error Handling

Errors are returned with appropriate HTTP status codes and detailed error messages:

- 400: Bad Request - Invalid parameters
- 401: Unauthorized - Authentication required
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource not found
- 500: Internal Server Error - Server-side error

Error responses include details to help diagnose the issue:

```json
{
  "status": "error",
  "error": "Error message",
  "error_details": {
    "code": "error_code",
    "message": "Detailed error message",
    "location": "Parameter or location of error",
    "details": {
      /* Additional error details */
    }
  }
}
```