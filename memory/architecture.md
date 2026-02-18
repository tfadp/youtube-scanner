# YouTube Outperformance Scanner - Architecture

## Overview
Scans ~100+ YouTube channels daily to find videos where views exceed subscriber count, analyzes title/theme patterns, and generates content ideas for Overtime properties using Claude.

## System Diagram
```mermaid
graph TB
    subgraph "Input"
        A[channels.json] --> B[Channel List]
    end

    subgraph "Scanner Pipeline"
        B --> C[YouTubeClient]
        C -->|forHandle lookup| D[Get Subscriber Counts]
        C -->|playlistItems API| E[Get Recent Videos]
        E --> F[Scanner]
        F -->|ratio >= 1.0| G[Filter Outperformers]
        G --> H[Calculate Velocity Score]
        H --> I[Classify: Trend-Jacker / Authority / Standard]
    end

    subgraph "Analysis"
        I --> J[Analyzer]
        J --> K[Title Patterns]
        J --> L[Theme Detection]
    end

    subgraph "Output"
        K --> M[Idea Generator]
        L --> M
        M -->|Claude API| N[Content Ideas]
        N --> O[Console Report]
        N --> P[output/*.txt]
    end
```

## Stack
- Language: Python 3.11+
- YouTube API: google-api-python-client
- AI: Anthropic Claude API
- Config: python-dotenv
