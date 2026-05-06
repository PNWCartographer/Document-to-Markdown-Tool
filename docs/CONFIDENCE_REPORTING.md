# Confidence Reporting

## Purpose
Confidence reporting helps users trust the output and understand where manual review may be needed.

The tool should not pretend every conversion is perfect. It should clearly report strengths, weaknesses, warnings, and uncertain sections.

## Required Confidence Areas
The confidence report should include:
- Overall conversion confidence
- Text extraction confidence
- OCR confidence when applicable
- Table structure confidence
- Image extraction confidence
- Image placement confidence
- Document order confidence
- Manual review recommendation

## Suggested Confidence Levels
Use plain language levels:
- High
- Medium
- Low
- Failed
- Not Applicable

## Example Report

```text
Conversion Confidence Report

Source file: example.pdf
Overall confidence: Medium

Text extraction: High
Table structure: Medium
Image placement: High
OCR confidence: Low on pages 4 and 7
Manual review recommended: Yes

Notes:
- Page 4 contained an electrical drawing with low OCR confidence.
- Page 7 contained a complex table that may need review.
```

## Markdown Integration
The Markdown file may include a short confidence summary at the top or bottom when the user enables this option.

Example:

```markdown
> Conversion confidence: Medium. Manual review recommended for pages 4 and 7.
```

## Low Confidence Stop Gaps
When confidence is low, the tool should recommend a review action.

Examples:
- Review extracted OCR text
- Compare table against source document
- Keep original image reference
- Re run with OCR fallback
- Re run with alternate extraction mode
