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

## Confidence for PowerPoint (PPTX)

PowerPoint files are digital-native, so most confidence dimensions are straightforward.

| Dimension | Typical Score | Notes |
|-----------|--------------|-------|
| Text Extraction | High | Text is read directly from shapes, no OCR needed |
| Table Structure | High | Tables are structured objects in PPTX format |
| Image Extraction | High | Images are embedded as discrete objects |
| Image Placement | Medium | Reading order depends on shape position sorting |
| Document Order | High | Slides have a defined sequence |
| OCR Confidence | N/A | PPTX text is already digital |

Notes added to confidence report:
- "python-pptx engine used" when that engine processes the file
- SmartArt or grouped shape extraction may add warnings about best-effort text recovery

## Confidence for EPUB

EPUB files are HTML-based e-books with well-defined structure.

| Dimension | Typical Score | Notes |
|-----------|--------------|-------|
| Text Extraction | High | HTML content parsed directly |
| Table Structure | Medium | HTML tables converted to Markdown, complex tables may lose formatting |
| Image Extraction | High | Images extracted from EPUB archive |
| Image Placement | High | Images are inline in chapter HTML |
| Document Order | High | Spine order defines reading sequence |
| OCR Confidence | N/A | EPUB text is already digital |

Notes added to confidence report:
- "ebooklib + BeautifulSoup engine used" when that engine processes the file
- Complex CSS-styled content may not preserve all visual formatting

## Post-Processor Impact on Confidence

Post-processors modify extracted text after conversion. Some processors can affect confidence reporting:

### Header and Footer Removal
- Does not reduce confidence when working correctly (removes noise, not content)
- If headers or footers contain meaningful content that the user wants to keep, turning this off prevents content loss
- Confidence notes may mention "headers/footers removed from N pages" for transparency

### Equation Detection
- Mathematical content wrapped in LaTeX notation is a best-effort conversion
- Complex equations with nested structures may not be perfectly represented
- The confidence report does not change based on equation detection, but conversion notes may flag sections where equation patterns were detected

### Code Block Detection
- Code block wrapping is heuristic-based and may occasionally wrap non-code content
- Confidence is not affected, but false positives can be addressed by turning off detection

### Footnote Detection
- Footnote detection uses pattern matching and may miss unconventional footnote formats
- Confidence is not affected, but the conversion log notes how many footnotes were detected
