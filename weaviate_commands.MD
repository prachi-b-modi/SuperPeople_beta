# Resume Builder CLI Command Reference Guide

This document provides a comprehensive list of important function calls with their arguments that you can use to manage your resume database.

## Adding Experiences

```bash
# Add a new experience with text and company
resume-builder add-experience --text "Your experience description here" --company "Company Name"

# Add with additional options
resume-builder add-experience --text "Your experience description" --company "Company Name" --role "Your Role" --duration "Jan 2020 - Dec 2022" --no-extraction
```

## Viewing Experiences

```bash
# List all experiences
resume-builder list-experiences

# Search experiences by query
resume-builder search --query "Python development"

# Show database statistics
resume-builder stats
```

## Database Management

```bash
# Initialize the database schema
resume-builder init-db

# Check system health
resume-builder health-check

# Backup experiences to a JSON file
resume-builder backup --output experiences_backup.json

# Restore experiences from a backup file
resume-builder restore --input experiences_backup.json

# Delete a specific experience by ID
resume-builder delete-experience --id "experience-uuid"

# Delete without confirmation prompt
resume-builder delete-experience --id "experience-uuid" --no-confirm
```

## Job Matching

```bash
# Match experiences to a job URL
resume-builder match-job --url "https://www.example.com/job-posting"

# Test job extraction from URL
resume-builder test-job-extraction --url "https://www.example.com/job-posting"
```

## Configuration and Information

```bash
# Show current configuration
resume-builder config-info

# Show version information
resume-builder version

# Run with custom config file
resume-builder --config custom_config.yaml [COMMAND]

# Enable debug logging
resume-builder --debug [COMMAND]
```

## Experience Refinement

```bash
# Refine specific experiences with AI
resume-builder refine-experience --id "experience-uuid"
```

## Help

You can get detailed help for any command by adding `--help` after the command:

```bash
resume-builder add-experience --help
```

## Examples

### Adding a new experience

```bash
resume-builder add-experience --text "Led a team of 5 developers to build a scalable microservices architecture using Python and Docker, resulting in 40% improved system performance." --company "TechCorp"
```

### Searching for experiences

```bash
resume-builder search --query "Python development"
```

### Matching experiences to a job posting

```bash
resume-builder match-job --url "https://www.linkedin.com/jobs/view/software-engineer-at-company-123456"
```

### Backing up experiences

```bash
resume-builder backup --output my_experiences.json
```