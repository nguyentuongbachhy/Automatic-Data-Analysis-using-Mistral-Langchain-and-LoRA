// services/jsonService.ts
import { z } from 'zod';
import { ApiResponse } from '../types';

interface TransformOptions {
    convertToSnakeCase?: boolean;
    convertToCamelCase?: boolean;
    addFields?: Record<string, any>;
    removeFields?: string[];
    validateWithSchema?: z.ZodType<any>;
    throwOnValidationError?: boolean;
}

/**
 * Service for JSON processing with transformation, validation, and normalization
 */
class JsonService {
    /**
     * Transform and normalize request from client to send to AI service
     */
    transformRequest(data: any, options: TransformOptions = {}): any {
        // Clone data to avoid modifying original
        const transformed = JSON.parse(JSON.stringify(data));

        // Convert fields according to camelCase -> snake_case rules
        if (options.convertToSnakeCase) {
            return this.toSnakeCase(transformed);
        }

        // Add required fields
        if (options.addFields) {
            Object.assign(transformed, options.addFields);
        }

        // Remove unnecessary fields
        if (options.removeFields && options.removeFields.length > 0) {
            options.removeFields.forEach(field => {
                delete transformed[field];
            });
        }

        return transformed;
    }

    /**
     * Transform and normalize response from AI service before sending to client
     */
    transformResponse<T = any>(data: any, options: TransformOptions = {}): ApiResponse<T> {
        if (!data) return data;

        // Clone data to avoid modifying original
        let transformed = JSON.parse(JSON.stringify(data));

        // Convert fields according to snake_case -> camelCase rules
        if (options.convertToCamelCase) {
            transformed = this.toCamelCase(transformed);
        }

        // Apply schema validation if available
        if (options.validateWithSchema) {
            try {
                transformed = options.validateWithSchema.parse(transformed);
            } catch (error) {
                console.error('JSON validation error:', error);
                // Return error or original data depending on configuration
                if (options.throwOnValidationError) {
                    throw error;
                }
            }
        }

        return transformed;
    }

    /**
     * Convert object with keys from camelCase to snake_case
     */
    toSnakeCase(data: any): any {
        if (data === null || data === undefined) return data;

        if (Array.isArray(data)) {
            return data.map(item => this.toSnakeCase(item));
        }

        if (typeof data === 'object' && data !== null) {
            const result: Record<string, any> = {};

            Object.keys(data).forEach(key => {
                const snakeKey = key.replace(/([A-Z])/g, '_$1').toLowerCase();
                result[snakeKey] = this.toSnakeCase(data[key]);
            });

            return result;
        }

        return data;
    }

    /**
     * Convert object with keys from snake_case to camelCase
     */
    toCamelCase(data: any): any {
        if (data === null || data === undefined) return data;

        if (Array.isArray(data)) {
            return data.map(item => this.toCamelCase(item));
        }

        if (typeof data === 'object' && data !== null) {
            const result: Record<string, any> = {};

            // Enhanced special field mapping - added new column types and chart types
            const specialFieldMap: Record<string, string> = {
                // Original mappings
                'dataset_info': 'datasetInfo',
                'data_quality': 'dataQuality',
                'statistical_analysis': 'statisticalAnalysis',
                'advanced_analysis': 'advancedAnalysis',
                'quality_metrics': 'qualityMetrics',
                'related_charts': 'relatedCharts',
                'recommended_type': 'recommendedType',
                'related_insights': 'relatedInsights',
                'is_custom': 'isCustom',
                'file_id': 'fileId',
                'user_id': 'userId',
                'file_path': 'filePath',
                'target_column': 'targetColumn',
                'feature_columns': 'featureColumns',
                'model_type': 'modelType',
                'time_column': 'timeColumn',
                'test_size': 'testSize',
                'memory_usage_mb': 'memoryUsageMb',
                'dtypes_summary': 'dtypesSummary',
                'column_types': 'columnTypes',
                'missing_values': 'missingValues',
                'duplicate_rows': 'duplicateRows',
                'missing_cells': 'missingCells',
                'missing_percent': 'missingPercent',
                'columns_with_missing': 'columnsWithMissing',
                'problematic_columns': 'problematicColumns',
                'inconsistency_count': 'inconsistencyCount',
                'inconsistent_columns': 'inconsistentColumns',
                'duplicate_percent': 'duplicatePercent',
                'unique_values': 'uniqueValues',
                'unique_percent': 'uniquePercent',
                'potential_identifiers': 'potentialIdentifiers',
                'integrity_issues': 'integrityIssues',
                'outlier_count': 'outlierCount',
                'outlier_percent': 'outlierPercent',
                'range_violations': 'rangeViolations',
                'date_violations': 'dateViolations',
                'accuracy_issues': 'accuracyIssues',
                'suspect_columns': 'suspectColumns',
                'overall_score': 'overallScore',
                'date_column': 'dateColumn',
                'value_column': 'valueColumn',
                'forecast_periods': 'forecastPeriods',
                'exogenous_variables': 'exogenousVariables',
                'return_confidence': 'returnConfidence',
                'chart_type': 'chartType',
                'top_k': 'topK',
                'created_at': 'createdAt',
                'updated_at': 'updatedAt',
                'page_size': 'pageSize',
                'total_pages': 'totalPages',

                // New mappings for additional chart types
                'word_cloud': 'wordCloud',
                'likert_correlation': 'likertCorrelation',
                'grouped_histogram': 'groupedHistogram',

                // New mappings for additional field types
                'likert_cols': 'likertCols',
                'gender_cols': 'genderCols',
                'range_cols': 'rangeCols',
                'text_cols': 'textCols',
                'binary_cols': 'binaryCols',

                // Additional common transformations
                'source_type': 'sourceType',
                'chart_library': 'chartLibrary',
                'display_name': 'displayName',
                'is_pending': 'isPending',
                'quality_score': 'qualityScore',
                'original_name': 'originalName'
            };

            Object.keys(data).forEach(key => {
                // If in map, use existing mapping
                if (specialFieldMap[key]) {
                    result[specialFieldMap[key]] = this.toCamelCase(data[key]);
                } else {
                    // Convert all other fields to camelCase
                    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
                    result[camelKey] = this.toCamelCase(data[key]);
                }
            });
            return result;
        }
        return data;
    }

    /**
     * Validate data against schema with error logging
     */
    validate<T>(data: any, schema: z.ZodType<T>, logErrors: boolean = true): T | null {
        try {
            return schema.parse(data);
        } catch (error) {
            if (logErrors) {
                console.error('Validation error:', error);
            }
            return null;
        }
    }

    /**
     * Convert data to JSON string with formatting
     */
    stringify(data: any, pretty: boolean = false): string {
        return pretty
            ? JSON.stringify(data, null, 2)
            : JSON.stringify(data);
    }

    /**
     * Parse JSON string to object with error handling
     */
    parse(jsonString: string): any {
        try {
            return JSON.parse(jsonString);
        } catch (error) {
            console.error('JSON parse error:', error);
            throw new Error('Invalid JSON string');
        }
    }

    /**
     * Deep clone an object without reference
     */
    deepClone<T>(obj: T): T {
        return JSON.parse(JSON.stringify(obj));
    }
}

// Singleton instance
export const jsonService = new JsonService();