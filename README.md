# BBPlus Local Viewer

A local SAT practice question viewer and extraction toolkit.

## Requirements
- Python 3
- Git

## Installation

Clone the repository:

    git clone https://github.com/HrishikeshLenin13/bbplus-extractor.git

Enter the folder:

    cd bbplus-extractor

Start the local server:

    bash setup.sh

Open in your browser:

    http://localhost:8000/output/viewer.html

## Features
- SAT Reading and Writing questions
- SAT Math questions
- Local browser viewer
- JSON and CSV support

## Data
Third-party question content is not included.
Users must provide their own authorized question data.

## Disclaimer
Independent educational project.
Not affiliated with College Board or BlueBookPlusPlus.


### Validate extracted JSONL offline

Run `python validate_jsonl.py PATH` to check record IDs, duplicate IDs, and answer
indexes without downloading or modifying data. For large files, add
`--max-errors 20` to keep only the first 20 record diagnostics while still
scanning every record and reporting the full `error_count`. Use `--max-errors 0`
for a count-only report. Invalid input still exits with status 1.
