# Functional Architecture

The AI Log Incident Analyzer follows a modular pipeline architecture.

## Pipeline Overview

1. Log files are provided as input.
2. The log reader loads raw log content.
3. The parser extracts structured log events.
4. The event extractor identifies relevant warnings, errors, timestamps, and system messages.
5. Detection modules identify rule-based incidents and abnormal patterns.
6. The incident classifier groups events into incident categories.
7. The severity evaluator assigns an impact level.
8. The recommendation engine generates engineering actions.
9. The report generator produces a markdown incident report.

## Main Components

- Log Reader
- Log Parser
- Event Extractor
- Rule-Based Detector
- Anomaly Detector
- Incident Classifier
- Severity Evaluator
- Recommendation Engine
- Markdown Report Generator

## Architecture Principle

The system is designed as a simple, testable, and extensible processing pipeline.
EOFrm projects/ai-log-incident-analyzer/docs/architecture/functional-architecture.mmd

cat > projects/ai-log-incident-analyzer/docs/architecture/architecture-description.md << 'EOF'
# Functional Architecture

The AI Log Incident Analyzer follows a modular pipeline architecture.

## Pipeline Overview

1. Log files are provided as input.
2. The log reader loads raw log content.
3. The parser extracts structured log events.
4. The event extractor identifies relevant warnings, errors, timestamps, and system messages.
5. Detection modules identify rule-based incidents and abnormal patterns.
6. The incident classifier groups events into incident categories.
7. The severity evaluator assigns an impact level.
8. The recommendation engine generates engineering actions.
9. The report generator produces a markdown incident report.

## Main Components

- Log Reader
- Log Parser
- Event Extractor
- Rule-Based Detector
- Anomaly Detector
- Incident Classifier
- Severity Evaluator
- Recommendation Engine
- Markdown Report Generator

## Architecture Principle

The system is designed as a simple, testable, and extensible processing pipeline.
