-- CreateEnum
CREATE TYPE "ResponseStatus" AS ENUM ('SUCCESS', 'ERROR', 'PENDING');

-- CreateEnum
CREATE TYPE "InsightType" AS ENUM ('CORRELATION', 'TREND', 'DISTRIBUTION', 'OUTLIER', 'SUMMARY', 'PATTERN', 'ANOMALY', 'COMPARISON', 'LIKERT', 'BINARY', 'GENDER', 'RANGE', 'TEXT');

-- CreateEnum
CREATE TYPE "ChartType" AS ENUM ('LINE', 'BAR', 'SCATTER', 'PIE', 'HISTOGRAM', 'GROUPED_HISTOGRAM', 'BOX', 'HEATMAP', 'AREA', 'BUBBLE', 'RADAR', 'COMBO', 'WATERFALL', 'TREEMAP', 'SANKEY', 'LIKERT', 'WORD_CLOUD', 'RANGE', 'TEXT', 'LIKERT_CORRELATION', 'BAR_GROUPED', 'VIOLIN', 'MOSAIC', 'SCATTER_3D', 'CHORD', 'FACET', 'GANTT', 'DONUT', 'HEXBIN', 'NETWORK', 'ANIMATION', 'DIVERGING', 'MATRIX', 'REGRESSION');

-- CreateEnum
CREATE TYPE "MessageRole" AS ENUM ('SYSTEM', 'USER', 'ASSISTANT');

-- CreateEnum
CREATE TYPE "IntentType" AS ENUM ('QUESTION', 'VISUALIZATION', 'ANALYSIS', 'INSIGHT', 'PREDICTION', 'UNKNOWN');

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "name" TEXT,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "File" (
    "id" TEXT NOT NULL,
    "filename" TEXT NOT NULL,
    "originalName" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "size" INTEGER NOT NULL,
    "path" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "qualityScore" DOUBLE PRECISION,
    "isPending" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "File_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "FileColumn" (
    "id" TEXT NOT NULL,
    "fileId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "displayName" TEXT,
    "type" TEXT NOT NULL,
    "stats" JSONB NOT NULL,
    "quality" DOUBLE PRECISION,
    "completeness" DOUBLE PRECISION,
    "nullable" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "FileColumn_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Analysis" (
    "id" TEXT NOT NULL,
    "fileId" TEXT NOT NULL,
    "rowCount" INTEGER NOT NULL,
    "columnCount" INTEGER NOT NULL,
    "missingValues" INTEGER NOT NULL,
    "duplicateRows" INTEGER NOT NULL,
    "outliers" INTEGER NOT NULL,
    "datasetInfo" JSONB,
    "statisticalAnalysis" JSONB,
    "advancedAnalysis" JSONB,
    "qualityMetrics" JSONB,
    "summary" JSONB NOT NULL,
    "dataQuality" JSONB,
    "recommendations" JSONB,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "Analysis_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Insight" (
    "id" TEXT NOT NULL,
    "fileId" TEXT NOT NULL,
    "type" "InsightType" NOT NULL,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "importance" DOUBLE PRECISION NOT NULL,
    "sourceType" TEXT,
    "columns" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "relatedCharts" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "metadata" JSONB,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "Insight_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Visualization" (
    "id" TEXT NOT NULL,
    "fileId" TEXT NOT NULL,
    "type" "ChartType" NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT,
    "config" JSONB NOT NULL,
    "data" JSONB NOT NULL,
    "parameters" JSONB,
    "chartLibrary" TEXT,
    "insight" TEXT,
    "recommendedType" TEXT,
    "relatedInsights" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "isCustom" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "Visualization_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ChartRecommendation" (
    "id" TEXT NOT NULL,
    "fileId" TEXT NOT NULL,
    "columns" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "recommendations" JSONB NOT NULL,
    "bestCharts" JSONB,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "ChartRecommendation_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Chat" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "fileId" TEXT,
    "title" TEXT NOT NULL DEFAULT 'New Chat',
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,
    "isArchived" BOOLEAN NOT NULL DEFAULT false,
    "lastMessage" TEXT,

    CONSTRAINT "Chat_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Message" (
    "id" TEXT NOT NULL,
    "chatId" TEXT NOT NULL,
    "role" "MessageRole" NOT NULL,
    "content" TEXT NOT NULL,
    "metadata" JSONB,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "Message_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TimeSeriesAnalysis" (
    "id" TEXT NOT NULL,
    "fileId" TEXT NOT NULL,
    "dateColumn" TEXT NOT NULL,
    "valueColumn" TEXT NOT NULL,
    "results" JSONB NOT NULL,
    "forecastIncluded" BOOLEAN NOT NULL DEFAULT false,
    "forecastPeriods" INTEGER,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "TimeSeriesAnalysis_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Prediction" (
    "id" TEXT NOT NULL,
    "fileId" TEXT NOT NULL,
    "targetColumn" TEXT NOT NULL,
    "featureColumns" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "modelType" TEXT NOT NULL,
    "config" JSONB NOT NULL,
    "results" JSONB NOT NULL,
    "metrics" JSONB NOT NULL,
    "testSize" DOUBLE PRECISION,
    "importance" JSONB,
    "visualization" JSONB,
    "createdAt" TEXT NOT NULL,
    "updatedAt" TEXT NOT NULL,

    CONSTRAINT "Prediction_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "FileColumn_fileId_name_key" ON "FileColumn"("fileId", "name");

-- CreateIndex
CREATE UNIQUE INDEX "Analysis_fileId_key" ON "Analysis"("fileId");

-- CreateIndex
CREATE UNIQUE INDEX "TimeSeriesAnalysis_fileId_dateColumn_valueColumn_key" ON "TimeSeriesAnalysis"("fileId", "dateColumn", "valueColumn");

-- AddForeignKey
ALTER TABLE "File" ADD CONSTRAINT "File_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "FileColumn" ADD CONSTRAINT "FileColumn_fileId_fkey" FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Analysis" ADD CONSTRAINT "Analysis_fileId_fkey" FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Insight" ADD CONSTRAINT "Insight_fileId_fkey" FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Visualization" ADD CONSTRAINT "Visualization_fileId_fkey" FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ChartRecommendation" ADD CONSTRAINT "ChartRecommendation_fileId_fkey" FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Chat" ADD CONSTRAINT "Chat_fileId_fkey" FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Chat" ADD CONSTRAINT "Chat_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Message" ADD CONSTRAINT "Message_chatId_fkey" FOREIGN KEY ("chatId") REFERENCES "Chat"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TimeSeriesAnalysis" ADD CONSTRAINT "TimeSeriesAnalysis_fileId_fkey" FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Prediction" ADD CONSTRAINT "Prediction_fileId_fkey" FOREIGN KEY ("fileId") REFERENCES "File"("id") ON DELETE CASCADE ON UPDATE CASCADE;
