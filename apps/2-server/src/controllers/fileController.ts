// controllers/fileController.ts
import { ChartType, InsightType } from '@prisma/client';
import { Response } from 'express';
import fs from 'fs';
import path from 'path';
import prisma from '../lib/prisma';
import { AuthRequest } from '../middlewares/auth';
import { moveToProcessed } from '../middlewares/upload';
import { forwardRequest } from '../services/gatewayService';
import { jsonService } from '../services/jsonService';
import { ResponseStatus, TimeSeriesAnalysisRequest, UploadResponse } from '../types';

/**
 * Convert insight type from string to enum
 */
const convertInsightType = (type: string): InsightType => {
    type = type.toLowerCase();
    switch (type) {
        case "correlation":
            return InsightType.CORRELATION
        case "trend":
            return InsightType.TREND
        case "distribution":
            return InsightType.DISTRIBUTION
        case "outlier":
            return InsightType.OUTLIER
        case "summary":
            return InsightType.SUMMARY
        case "pattern":
            return InsightType.PATTERN
        case "anomaly":
            return InsightType.ANOMALY
        case "comparison":
            return InsightType.COMPARISON
        case "likert":
            return InsightType.LIKERT
        case "binary":
            return InsightType.BINARY
        case "gender":
            return InsightType.GENDER
        case "range":
            return InsightType.RANGE
        case "text":
            return InsightType.TEXT
        default:
            return InsightType.SUMMARY
    }
}

/**
 * Convert chart type from string to enum
 */
const convertChartType = (type: string): ChartType => {
    type = type.toLowerCase();
    switch (type) {
        case "line":
            return ChartType.LINE
        case "bar":
            return ChartType.BAR
        case "scatter":
            return ChartType.SCATTER
        case "pie":
            return ChartType.PIE
        case "histogram":
            return ChartType.HISTOGRAM
        case "grouped histogram":
            return ChartType.GROUPED_HISTOGRAM
        case "box":
            return ChartType.BOX
        case "heatmap":
            return ChartType.HEATMAP
        case "area":
            return ChartType.AREA
        case "bubble":
            return ChartType.BUBBLE
        case "radar":
            return ChartType.RADAR
        case "combo":
            return ChartType.COMBO
        case "waterfall":
            return ChartType.WATERFALL
        case "treemap":
            return ChartType.TREEMAP
        case "sankey":
            return ChartType.SANKEY
        case "likert":
            return ChartType.LIKERT
        case "word cloud":
            return ChartType.WORD_CLOUD
        case "range":
            return ChartType.RANGE
        case "text":
            return ChartType.TEXT
        case "likert correlation":
            return ChartType.LIKERT_CORRELATION
        case "bar grouped":
            return ChartType.BAR_GROUPED
        case "violin":
            return ChartType.VIOLIN
        case "mosaic":
            return ChartType.MOSAIC
        case "scatter 3d":
            return ChartType.SCATTER_3D
        case "chord":
            return ChartType.CHORD
        case "facet":
            return ChartType.FACET
        case "gantt":
            return ChartType.GANTT
        case "donut":
            return ChartType.DONUT
        case "hexbin":
            return ChartType.HEXBIN
        case "network":
            return ChartType.NETWORK
        case "animation":
            return ChartType.ANIMATION
        case "diverging":
            return ChartType.DIVERGING
        case "matrix":
            return ChartType.MATRIX
        case "regression":
            return ChartType.REGRESSION
        default:
            return ChartType.BAR
    }
}

/**
 * Calculate column quality based on data quality metrics
 */
const calculateColumnQuality = (columnName: string, data: any): number => {
    let quality = 1.0; // Bắt đầu với chất lượng tối đa

    // Giảm chất lượng dựa trên dữ liệu thiếu
    const missingColumns = data.dataQuality?.qualityMetrics?.completeness?.columnsWithMissing || [];
    if (missingColumns.includes(columnName)) {
        quality -= 0.2;
    }

    // Giảm chất lượng dựa trên outliers
    const outlierStats = data.dataQuality?.qualityMetrics?.integrity?.outlierStats || {};
    if (outlierStats[columnName]) {
        quality -= outlierStats[columnName].outlierPercent / 100 * 0.3;
    }

    // Giảm chất lượng dựa trên vấn đề tính nhất quán
    const inconsistentColumns = data.dataQuality?.qualityMetrics?.consistency?.inconsistentColumns || [];
    if (inconsistentColumns.some((col: any) => col.column === columnName)) {
        quality -= 0.2;
    }

    // Additional quality evaluation for new column types
    // Check for text quality if applicable
    const textAnalysis = data.advancedAnalysis?.textAnalysis || {};
    if (textAnalysis[columnName]) {
        // Lower quality for columns with short or inconsistent text length
        const lengthStats = textAnalysis[columnName].lengthStatistics;
        if (lengthStats && lengthStats.meanLength < 5) {
            quality -= 0.1;
        }
    }

    // Check for likert scale consistency
    const likertAnalysis = data.advancedAnalysis?.likertAnalysis?.responsePatterns || {};
    if (likertAnalysis[columnName] && likertAnalysis[columnName].polarization > 0.7) {
        quality -= 0.1; // High polarization might indicate issues
    }

    return Math.max(0, Math.min(1, quality));
}

/**
 * Calculate column completeness
 */
const calculateCompleteness = (columnName: string, data: any): number => {
    const qualityMetrics = data.dataQuality?.qualityMetrics;
    const columnsWithMissing = qualityMetrics?.completeness?.columnsWithMissing || [];

    if (columnsWithMissing.includes(columnName)) {
        // Nếu có thông tin chi tiết từng cột
        const columnStats = data.statisticalAnalysis?.[columnName];
        if (columnStats && columnStats.missing_count !== undefined && columnStats.count !== undefined) {
            return 1 - (columnStats.missing_count / columnStats.count);
        }
        return 0.8; // Giá trị mặc định nếu không có chi tiết
    }
    return 1.0; // Hoàn toàn đầy đủ
}

/**
 * Process and save analysis data to database
 */
const processAnalysisData = async (fileId: string, data: any) => {
    try {
        console.log("Processing analysis data for file:", fileId);

        // 1. Upsert Analysis record
        await prisma.analysis.upsert({
            where: {
                fileId: fileId
            },
            update: {
                rowCount: data.datasetInfo?.rows || 0,
                columnCount: data.datasetInfo?.columns || 0,
                missingValues: data.datasetInfo?.missingValues?.count || 0,
                duplicateRows: data.dataQuality?.qualityMetrics?.uniqueness?.duplicateRows || 0,
                outliers: Object.values(data.dataQuality?.qualityMetrics?.integrity?.outlierStats || {})
                    .reduce((sum: number, stat: any) => sum + (stat.outlierCount || 0), 0),
                datasetInfo: data.datasetInfo || {},
                statisticalAnalysis: data.statisticalAnalysis || {},
                advancedAnalysis: data.advancedAnalysis || {},
                qualityMetrics: data.dataQuality?.qualityMetrics || {},
                summary: data.summary || { generated: false },
                dataQuality: data.dataQuality || {},
                recommendations: data.recommendations || [],
                updatedAt: (new Date()).toISOString()
            },
            create: {
                fileId: fileId,
                rowCount: data.datasetInfo?.rows || 0,
                columnCount: data.datasetInfo?.columns || 0,
                missingValues: data.datasetInfo?.missingValues?.count || 0,
                duplicateRows: data.dataQuality?.qualityMetrics?.uniqueness?.duplicateRows || 0,
                outliers: Object.values(data.dataQuality?.qualityMetrics?.integrity?.outlierStats || {})
                    .reduce((sum: number, stat: any) => sum + (stat.outlierCount || 0), 0),
                datasetInfo: data.datasetInfo || {},
                statisticalAnalysis: data.statisticalAnalysis || {},
                advancedAnalysis: data.advancedAnalysis || {},
                qualityMetrics: data.dataQuality?.qualityMetrics || {},
                summary: data.summary || { generated: false },
                dataQuality: data.dataQuality || {},
                recommendations: data.recommendations || [],
                createdAt: (new Date()).toISOString(),
                updatedAt: (new Date()).toISOString()
            }
        });

        // 2. Xóa các FileColumn hiện có và tạo lại
        await prisma.fileColumn.deleteMany({
            where: { fileId }
        });
        await createFileColumns(fileId, data);

        // 3. Xóa các Insight hiện có và tạo lại
        await prisma.insight.deleteMany({
            where: { fileId }
        });
        if (data.insights && Array.isArray(data.insights)) {
            await createInsights(fileId, data.insights);
        }

        // 4. Xóa các Visualization hiện có và tạo lại
        await prisma.visualization.deleteMany({
            where: { fileId }
        });
        if (data.visualizations && Array.isArray(data.visualizations)) {
            await createVisualizations(fileId, data.visualizations);
        }

        // 5. Xóa các TimeSeriesAnalysis hiện có và tạo lại
        await prisma.timeSeriesAnalysis.deleteMany({
            where: { fileId }
        });

        // Enhanced Time Series Analysis handling
        if (data.timeSeriesAnalysis) {
            // Handle both object and array formats from analyzer.py
            if (Array.isArray(data.timeSeriesAnalysis.analyses)) {
                // Newer format from analyzer.py
                await createTimeSeriesAnalysesFromArray(fileId, data.timeSeriesAnalysis);
            } else if (Object.keys(data.timeSeriesAnalysis).length > 0) {
                // Legacy format
                await createTimeSeriesAnalyses(fileId, data.timeSeriesAnalysis);
            }
        }

        // 6. Xóa các ChartRecommendation hiện có và tạo lại
        await prisma.chartRecommendation.deleteMany({
            where: { fileId }
        });
        if (data.chartRecommendations) {
            await createChartRecommendations(fileId, data.chartRecommendations);
        }

        // 7. Xóa các Prediction hiện có và tạo lại
        await prisma.prediction.deleteMany({
            where: { fileId }
        });
        if (data.predictions && Array.isArray(data.predictions)) {
            await createPredictions(fileId, data.predictions);
        }

        // 8. Update file quality score
        if (data.dataQuality?.qualityMetrics?.overallScore !== undefined) {
            await prisma.file.update({
                where: { id: fileId },
                data: {
                    qualityScore: data.dataQuality.qualityMetrics.overallScore
                }
            });
        }

        await prisma.file.update({
            where: { id: fileId },
            data: { isPending: false }
        });

        console.log(`Analysis data processing completed for file ${fileId}`);
    } catch (error) {
        console.error(`Error processing analysis data for file ${fileId}:`, error);
        throw error;
    }
};

/**
 * Create FileColumn records
 */
const createFileColumns = async (fileId: string, data: any) => {
    try {
        // Get column types from dataset info - handle all the new types from data_processor.py
        const columnTypes = data.datasetInfo?.columnTypes || {};
        const allColumns: string[] = [
            ...(columnTypes.id || []),
            ...(columnTypes.numeric || []),
            ...(columnTypes.categorical || []),
            ...(columnTypes.datetime || []),
            ...(columnTypes.boolean || []),
            // Add new column types from data_processor.py
            ...(columnTypes.likert || []),
            ...(columnTypes.binary || []),
            ...(columnTypes.gender || []),
            ...(columnTypes.range || []),
            ...(columnTypes.text || []),
            ...(columnTypes.email || []),
            ...(columnTypes.phone || []),
            ...(columnTypes.address || []),
            ...(columnTypes.name || []),
            ...(columnTypes.url || [])
        ];

        // Remove duplicates (some columns might appear in multiple types)
        const uniqueColumns = [...new Set(allColumns)];

        for (const columnName of uniqueColumns) {
            // Determine column type with enhanced detection for the new types
            let type = 'unknown';
            if (columnTypes.id?.includes(columnName)) type = 'id';
            else if (columnTypes.numeric?.includes(columnName)) type = 'numeric';
            else if (columnTypes.categorical?.includes(columnName)) type = 'categorical';
            else if (columnTypes.datetime?.includes(columnName)) type = 'datetime';
            else if (columnTypes.boolean?.includes(columnName)) type = 'boolean';
            // New column types
            else if (columnTypes.likert?.includes(columnName)) type = 'likert';
            else if (columnTypes.binary?.includes(columnName)) type = 'binary';
            else if (columnTypes.gender?.includes(columnName)) type = 'gender';
            else if (columnTypes.range?.includes(columnName)) type = 'range';
            else if (columnTypes.text?.includes(columnName)) type = 'text';
            else if (columnTypes.email?.includes(columnName)) type = 'email';
            else if (columnTypes.phone?.includes(columnName)) type = 'phone';
            else if (columnTypes.address?.includes(columnName)) type = 'address';
            else if (columnTypes.name?.includes(columnName)) type = 'name';
            else if (columnTypes.url?.includes(columnName)) type = 'url';

            // Get column statistics - handle specific stats for new column types
            let stats = {};

            // General statistics
            if (data.statisticalAnalysis?.[columnName]) {
                stats = data.statisticalAnalysis[columnName];
            }

            // Type-specific statistics
            if (type === 'likert' && data.statisticalAnalysis?.likertSummary?.[columnName]) {
                stats = {
                    ...stats,
                    likertStats: data.statisticalAnalysis.likertSummary[columnName]
                };
            } else if (type === 'binary' && data.statisticalAnalysis?.binarySummary?.[columnName]) {
                stats = {
                    ...stats,
                    binaryStats: data.statisticalAnalysis.binarySummary[columnName]
                };
            } else if (type === 'gender' && data.statisticalAnalysis?.genderSummary?.[columnName]) {
                stats = {
                    ...stats,
                    genderStats: data.statisticalAnalysis.genderSummary[columnName]
                };
            } else if (type === 'range' && data.statisticalAnalysis?.rangeSummary?.[columnName]) {
                stats = {
                    ...stats,
                    rangeStats: data.statisticalAnalysis.rangeSummary[columnName]
                };
            } else if (type === 'text' && data.statisticalAnalysis?.textSummary?.[columnName]) {
                stats = {
                    ...stats,
                    textStats: data.statisticalAnalysis.textSummary[columnName]
                };
            }

            // Advanced analysis stats
            if (type === 'text' && data.advancedAnalysis?.textAnalysis?.[columnName]) {
                stats = {
                    ...stats,
                    textAnalysis: data.advancedAnalysis.textAnalysis[columnName]
                };
            } else if (type === 'likert' && data.advancedAnalysis?.likertAnalysis?.responsePatterns?.[columnName]) {
                stats = {
                    ...stats,
                    likertAnalysis: data.advancedAnalysis.likertAnalysis.responsePatterns[columnName]
                };
            }

            // Calculate quality metrics
            const quality = calculateColumnQuality(columnName, data);
            const completeness = calculateCompleteness(columnName, data);

            // Check if column is nullable
            const nullable = data.dataQuality?.qualityMetrics?.completeness?.columnsWithMissing?.includes(columnName) || true;

            // Create a formatted display name from the column name
            const displayName = columnName
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');

            await prisma.fileColumn.create({
                data: {
                    fileId,
                    name: columnName,
                    displayName: displayName,
                    type,
                    stats,
                    quality,
                    completeness,
                    nullable,
                    createdAt: (new Date()).toISOString(),
                    updatedAt: (new Date()).toISOString()
                }
            });
        }

        console.log(`Created ${uniqueColumns.length} FileColumn records for file ${fileId}`);
    } catch (error) {
        console.error(`Error creating FileColumn records for file ${fileId}:`, error);
        throw error;
    }
};

/**
 * Create Insight records
 */
const createInsights = async (fileId: string, insights: any[]) => {
    try {
        for (const insight of insights) {
            await prisma.insight.create({
                data: {
                    fileId,
                    type: convertInsightType(insight.type || ''),
                    title: insight.title || 'Untitled Insight',
                    content: insight.content || '',
                    importance: insight.importance || 1,
                    sourceType: insight.sourceType || 'automatic',
                    columns: insight.columns || [],
                    relatedCharts: insight.relatedCharts || [],
                    metadata: insight.metadata || {},
                    createdAt: (new Date()).toISOString(),
                    updatedAt: (new Date()).toISOString()
                }
            });
        }

        console.log(`Created ${insights.length} Insight records for file ${fileId}`);
    } catch (error) {
        console.error(`Error creating Insight records for file ${fileId}:`, error);
        throw error;
    }
};

/**
 * Create Visualization records
 */
const createVisualizations = async (fileId: string, visualizations: any[]) => {
    try {
        for (const viz of visualizations) {
            await prisma.visualization.create({
                data: {
                    fileId,
                    type: convertChartType(viz.type || ''),
                    title: viz.title || 'Untitled Visualization',
                    description: viz.description || null,
                    config: viz.config || {},
                    data: viz.data || [],
                    parameters: viz.parameters || null,
                    chartLibrary: viz.chartLibrary || 'echarts',
                    insight: viz.insight || null,
                    recommendedType: viz.recommendedType || null,
                    relatedInsights: viz.relatedInsights || [],
                    isCustom: viz.isCustom || false,
                    createdAt: (new Date()).toISOString(),
                    updatedAt: (new Date()).toISOString()
                }
            });
        }

        console.log(`Created ${visualizations.length} Visualization records for file ${fileId}`);
    } catch (error) {
        console.error(`Error creating Visualization records for file ${fileId}:`, error);
        throw error;
    }
};

/**
 * Create TimeSeriesAnalysis records (legacy format)
 */
const createTimeSeriesAnalyses = async (fileId: string, timeSeriesData: any) => {
    try {
        for (const [key, analysis] of Object.entries(timeSeriesData)) {
            // Extract date and value columns from key (assuming format: dateCol_vs_valueCol)
            const keyParts = key.split('_vs_');
            if (keyParts.length !== 2) continue;

            const [dateColumn, valueColumn] = keyParts;

            await prisma.timeSeriesAnalysis.create({
                data: {
                    fileId,
                    dateColumn,
                    valueColumn,
                    results: analysis || {},
                    forecastIncluded: analysis && (analysis as any).forecast ? true : false,
                    forecastPeriods: analysis && (analysis as any).forecast ? (analysis as any).forecast.periods : null,
                    createdAt: (new Date()).toISOString(),
                    updatedAt: (new Date()).toISOString()
                }
            });
        }

        console.log(`Created TimeSeriesAnalysis records for file ${fileId}`);
    } catch (error) {
        console.error(`Error creating TimeSeriesAnalysis records for file ${fileId}:`, error);
        throw error;
    }
};

/**
 * Create TimeSeriesAnalysis records from analyses array (new format from analyzer.py)
 */
const createTimeSeriesAnalysesFromArray = async (fileId: string, timeSeriesData: any) => {
    try {
        const analyses = timeSeriesData.analyses || [];
        const forecasts = timeSeriesData.forecasts || [];

        // Process each time series analysis
        for (const analysis of analyses) {
            const dateColumn = analysis.dateColumn || analysis.date_column;
            const valueColumn = analysis.valueColumn || analysis.value_column;

            if (!dateColumn || !valueColumn) continue;

            // Check if there's a forecast for this analysis
            const forecast = forecasts.find((f: TimeSeriesAnalysisRequest) =>
                (f.dateColumn) === dateColumn &&
                (f.valueColumn) === valueColumn
            );

            await prisma.timeSeriesAnalysis.create({
                data: {
                    fileId,
                    dateColumn,
                    valueColumn,
                    results: {
                        ...analysis,
                        forecast: forecast ? forecast.forecastData || forecast.forecast_data : null
                    },
                    forecastIncluded: !!forecast,
                    forecastPeriods: forecast ? forecast.periods : null,
                    createdAt: (new Date()).toISOString(),
                    updatedAt: (new Date()).toISOString()
                }
            });
        }

        console.log(`Created ${analyses.length} TimeSeriesAnalysis records for file ${fileId}`);
    } catch (error) {
        console.error(`Error creating TimeSeriesAnalysis records from array for file ${fileId}:`, error);
        throw error;
    }
};

/**
 * Create ChartRecommendation records
 */
const createChartRecommendations = async (fileId: string, recommendations: any) => {
    try {
        await prisma.chartRecommendation.create({
            data: {
                fileId,
                columns: recommendations.columns || [],
                recommendations: recommendations.recommendations || {},
                bestCharts: recommendations.bestCharts || null,
                createdAt: (new Date()).toISOString(),
                updatedAt: (new Date()).toISOString()
            }
        });

        console.log(`Created ChartRecommendation record for file ${fileId}`);
    } catch (error) {
        console.error(`Error creating ChartRecommendation record for file ${fileId}:`, error);
        throw error;
    }
};

/**
 * Create Prediction records
 */
const createPredictions = async (fileId: string, predictions: any[]) => {
    try {
        for (const prediction of predictions) {
            await prisma.prediction.create({
                data: {
                    fileId,
                    targetColumn: prediction.targetColumn || '',
                    featureColumns: prediction.featureColumns || [],
                    modelType: prediction.modelType || 'unknown',
                    config: prediction.config || {},
                    results: prediction.results || {},
                    metrics: prediction.metrics || {},
                    testSize: prediction.testSize || 0.2,
                    importance: prediction.importance || null,
                    visualization: prediction.visualization || null,
                    createdAt: (new Date()).toISOString(),
                    updatedAt: (new Date()).toISOString()
                }
            });
        }

        console.log(`Created ${predictions.length} Prediction records for file ${fileId}`);
    } catch (error) {
        console.error(`Error creating Prediction records for file ${fileId}:`, error);
        throw error;
    }
};

/**
 * Upload a file and initiate analysis
 */
export const uploadFile = async (req: AuthRequest, res: Response) => {
    try {
        if (!req.file) {
            res.status(400).json({
                status: ResponseStatus.ERROR,
                error: 'No file found'
            });
            return;
        }

        const { originalname, filename, mimetype, size } = req.file;

        // Create new filename to avoid conflicts
        const newFilename = `${Date.now()}_${path.basename(filename)}`;
        // Move file and get full path
        const fullPath = moveToProcessed(filename, newFilename);

        // Save file info to database
        const file = await prisma.file.create({
            data: {
                filename: newFilename,
                originalName: originalname,
                type: mimetype,
                size,
                path: fullPath,
                userId: req.user!.id,
                isPending: true,
                createdAt: (new Date()).toISOString(),
                updatedAt: (new Date()).toISOString()
            },
        });

        // Send file analysis request to AI service (asynchronous)
        forwardRequest(
            '/analyze/full',
            'POST',
            { file_id: file.id, user_id: file.userId },
            null,
            {
                additionalFields: {
                    analysis_type: 'full'
                },
                timeout: 600000  // 10 minutes timeout for large files
            }
        ).then(async (response) => {
            if (response.status === ResponseStatus.SUCCESS && response.data) {
                // Process and save analysis data
                try {
                    const analysisData = jsonService.toCamelCase(response.data);
                    await processAnalysisData(file.id, analysisData);
                } catch (err) {
                    console.error(`Error saving analysis data for ${file.id}:`, err);
                    await prisma.file.update({
                        where: { id: file.id },
                        data: { isPending: false }  // Mark as not pending even if analysis failed
                    });
                }
            } else {
                console.error(`Analysis service returned error for file ${file.id}:`, response.error);
                await prisma.file.update({
                    where: { id: file.id },
                    data: { isPending: false }  // Mark as not pending
                });
            }
        }).catch(err => {
            console.error(`Background analysis error for file ${file.id}:`, err);
            // Update file status in case of error
            prisma.file.update({
                where: { id: file.id },
                data: { isPending: false }
            }).catch(updateErr => {
                console.error(`Failed to update file status after analysis error: ${updateErr}`);
            });
        });

        // Return success immediately without waiting for analysis
        const response: UploadResponse = {
            status: ResponseStatus.SUCCESS,
            data: {
                fileId: file.id,
                originalName: file.originalName,
                message: 'File uploaded, analyzing data...'
            }
        };

        res.status(201).json(response);
    } catch (error) {
        console.error('Error uploading file:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error uploading file'
        });
    }
};

/**
 * Delete a file
 */
export const deleteFile = async (req: AuthRequest, res: Response) => {
    try {
        const { id } = req.params;

        const file = await prisma.file.findUnique({
            where: {
                id,
                userId: req.user!.id,
            },
        });

        if (!file) {
            res.status(404).json({
                status: ResponseStatus.ERROR,
                error: 'File not found'
            });
            return;
        }

        // Delete file from filesystem
        try {
            await fs.promises.unlink(file.path);
        } catch (err) {
            console.error(`Could not delete file at ${file.path}:`, err);
        }

        // Delete file from database
        await prisma.file.delete({
            where: { id },
        });

        res.json({
            status: ResponseStatus.SUCCESS,
            data: {
                message: 'File deleted successfully'
            }
        });
    } catch (error) {
        console.error('Error deleting file:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error deleting file'
        });
    }
};

/**
 * Get file data
 */
export const getFileById = async (req: AuthRequest, res: Response) => {
    try {
        const { id } = req.params
        const file = await prisma.file.findUnique({
            where: {
                id,
                userId: req.user!.id,
            },
        })

        if (!file) {
            res.status(404).json({
                status: ResponseStatus.ERROR,
                error: 'File not found'
            })
            return;
        }

        const formattedFile = {
            id: id,
            filename: file.filename,
            originalName: file.originalName,
            type: file.type.split('/').pop() || 'unknown',
            size: file.size,
            path: file.path,
            userId: file.userId,
            qualityScore: file.qualityScore,
            isPending: file.isPending,
            createdAt: file.createdAt,
            updatedAt: file.updatedAt,
        };

        res.json({
            status: ResponseStatus.SUCCESS,
            data: formattedFile
        });
    } catch (error) {
        console.error('Error fetching file data:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error fetching file data'
        });
    }
}

/**
 * Get all files for current user
 */
export const getFiles = async (req: AuthRequest, res: Response) => {
    try {
        const files = await prisma.file.findMany({
            where: {
                userId: req.user!.id,
            },
            orderBy: {
                createdAt: 'desc',
            },
            include: {
                analysis: true
            }
        });

        const formattedFiles = files.map(file => ({
            id: file.id,
            filename: file.filename,
            originalName: file.originalName,
            type: file.type.split('/').pop() || 'unknown',
            size: file.size,
            path: file.path,
            userId: file.userId,
            qualityScore: file.qualityScore,
            isPending: file.isPending,
            createdAt: file.createdAt,
            updatedAt: file.updatedAt,
            analysis: file.analysis,
        }));

        res.json({
            status: ResponseStatus.SUCCESS,
            data: { files: formattedFiles }
        });
    } catch (error) {
        console.error('Error fetching files:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error fetching files'
        });
    }
};

/**
 * Get file analysis data
 */
export const getFileAnalysis = async (req: AuthRequest, res: Response) => {
    try {
        const { id } = req.params;
        const { type } = req.query; // 'summary' hoặc 'details' hoặc mặc định

        const file = await prisma.file.findUnique({
            where: {
                id,
                userId: req.user!.id,
            },
            include: {
                analysis: true,
                columns: true,
                insights: true,
                visualizations: true,
                timeSeriesAnalyses: true,
                chartRecommendations: true,
                predictions: true
            },
        });

        if (!file) {
            res.status(404).json({
                status: ResponseStatus.ERROR,
                error: 'File not found'
            });
            return;
        }

        // Nếu chưa có phân tích, gọi AI service
        if (!file.analysis) {
            if (file.isPending) {
                // Đang phân tích, trả về PENDING
                res.status(202).json({
                    status: ResponseStatus.PENDING,
                    data: {
                        message: 'File is being analyzed',
                        ready: false
                    }
                });
                return
            } else {
                try {
                    const aiResponse = await forwardRequest(
                        '/analyze/full',
                        'POST',
                        {
                            fileId: file.id,
                            userId: req.user!.id
                        },
                        null,
                        {
                            additionalFields: {
                                analysis_type: 'full'
                            },
                            timeout: 300000 // 5 minute timeout
                        }
                    );

                    if (aiResponse.status === ResponseStatus.SUCCESS && aiResponse.data) {
                        // Lưu dữ liệu phân tích nhận được
                        const analysisData = jsonService.toCamelCase(aiResponse.data);
                        await processAnalysisData(file.id, analysisData);

                        // Lấy dữ liệu mới sau khi lưu
                        const updatedFile = await prisma.file.findUnique({
                            where: { id: file.id },
                            include: {
                                analysis: true,
                                columns: true,
                                insights: true,
                                visualizations: true,
                                timeSeriesAnalyses: true,
                                chartRecommendations: true,
                                predictions: true
                            },
                        });

                        if (type === 'summary') {
                            res.json({
                                status: ResponseStatus.SUCCESS,
                                data: {
                                    summary: jsonService.toCamelCase(updatedFile?.analysis),
                                    ready: true
                                }
                            });
                        } else {
                            res.json({
                                status: ResponseStatus.SUCCESS,
                                data: jsonService.toCamelCase(updatedFile)
                            });
                        }
                        return;
                    } else {
                        // Mark file as not pending since analysis failed
                        await prisma.file.update({
                            where: { id: file.id },
                            data: { isPending: false }
                        });

                        res.status(202).json({
                            status: ResponseStatus.PENDING,
                            data: {
                                message: 'Analysis in progress, please try again later',
                                ready: false,
                                file: type === 'summary' ? undefined : jsonService.toCamelCase(file)
                            }
                        });
                        return;
                    }
                } catch (apiError) {
                    console.error('Error from AI service:', apiError);

                    // Mark file as not pending since analysis failed
                    await prisma.file.update({
                        where: { id: file.id },
                        data: { isPending: false }
                    });

                    res.status(202).json({
                        status: ResponseStatus.PENDING,
                        data: {
                            message: 'Analysis in progress, please try again later',
                            ready: false,
                            file: type === 'summary' ? undefined : jsonService.toCamelCase(file)
                        }
                    });
                    return;
                }
            }
        }

        // Trả về dữ liệu dựa trên loại yêu cầu
        if (type === 'summary') {
            res.json({
                status: ResponseStatus.SUCCESS,
                data: {
                    summary: jsonService.toCamelCase(file.analysis),
                    ready: true
                }
            });
        } else {
            res.json({
                status: ResponseStatus.SUCCESS,
                data: jsonService.toCamelCase(file)
            });
        }
    } catch (error) {
        console.error('Error fetching file data:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error fetching file data'
        });
    }
};

export const getFileInsights = async (req: AuthRequest, res: Response) => {
    try {
        const { id } = req.params;
        if (!id) {
            res.status(400).json({
                status: ResponseStatus.ERROR,
                error: "'id' is required"
            })
            return;
        }

        const insights = await prisma.insight.findMany({
            where: { fileId: id },
            orderBy: {
                importance: 'desc'
            }
        })

        const formattedInsights = insights.map(insight => ({
            id: insight.id,
            fileId: id,
            type: insight.type,
            title: insight.title,
            content: insight.content,
            importance: insight.importance,
            columns: insight.columns,
            relatedCharts: insight.relatedCharts,
            metadata: insight.metadata
        }))

        res.json({
            status: ResponseStatus.SUCCESS,
            data: { insights: formattedInsights }
        })

    } catch (error) {
        console.error('Error fetching insight data:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error fetching insight data'
        });
    }
}

export const getFileVisualizations = async (req: AuthRequest, res: Response) => {
    try {
        const { fileId } = req.params;
        if (!fileId) {
            res.status(400).json({
                status: ResponseStatus.ERROR,
                error: "fileId is required"
            })
            return;
        }

        const visualizations = await prisma.visualization.findMany({
            where: { fileId },
        })

        const formattedVisualizations = visualizations.map(visualization => ({
            id: visualization.id,
            fileId,
            type: visualization.type,
            title: visualization.title,
            description: visualization.description,
            data: visualization.data,
            config: visualization.config,
            insight: visualization.insight,
            relatedInsights: visualization.relatedInsights,
            isCustom: visualization.isCustom
        }))

        res.json({
            status: ResponseStatus.SUCCESS,
            data: { visualizations: formattedVisualizations }
        })

    } catch (error) {
        console.error('Error fetching chart data:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error fetching chart data'
        });
    }
}