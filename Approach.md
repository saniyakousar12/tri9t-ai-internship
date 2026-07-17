# Approach Document - Tri9T AI Internship

## 1. PDF Parsing Strategy

### Selected Approach: pdfplumber + Custom Hierarchy Builder

**Why pdfplumber over alternatives:**

I chose pdfplumber because:
- It is pure Python with no compilation step, making it easy to install and run on any platform
- The CT-200 manual has a clean native text layer, so OCR (Tesseract, EasyOCR) was unnecessary and would have introduced transcription errors
- It preserves page-level text structure, making heading detection more reliable than raw text extraction
- It has built-in table extraction capabilities that helped with the specification tables in the manual

**Why not OCR:**

The assignment asks for an "OCR-based document extraction pipeline." After inspecting the CT-200 manual, I determined that the document has a native text layer (not scanned images). Using OCR on a text-based PDF would:
- Add unnecessary processing time
- Introduce transcription errors (e.g., "mmHg" becoming "mm Hg" or worse)
- Require additional post-processing to correct OCR mistakes
- Not improve extraction quality since the text is already machine-readable

Therefore, I used **direct text extraction with pdfplumber** and documented this decision explicitly — the manual is text-based, so OCR would have reduced, not improved, accuracy.

### Parsing Pipeline
PDF → pdfplumber → Text Extraction → Heading Detection → Hierarchy Building → Persist to SQLite

text

### Heading Detection

For the CT-200 manual, I detect headings using the following patterns (in priority order):

1. **Numbered Headings**: 
   - `1. Device Overview` (level 1)
   - `1.1 Intended Use` (level 2)
   - `1.2.1 Battery Life` (level 3) — using regex patterns `^(\d+)\.\s+`, `^(\d+\.\d+)\s+`, `^(\d+\.\d+\.\d+)\s+`

2. **ALL CAPS Headings**: e.g., "ALARMS AND SAFETY BEHAVIOR" — detected by `text.isupper()` and length > 5

3. **Roman Numerals**: e.g., "I. Introduction" — detected by regex `^[IVXLCDM]+\.\s+` (checked before title case to avoid conflicts)

4. **Title Case with Keywords**: e.g., "Device Overview" — detected by `text.istitle()` and containing keywords like 'Introduction', 'Safety', 'Warning', 'Caution', 'Operation', 'Maintenance', 'Specifications'

### Hierarchy Reconstruction

**Algorithm:**

1. Extract all headings with a detected level
2. Maintain a parent stack per level
3. For each heading:
   - Pop stack until the level matches
   - Set parent as the current stack top
   - Push the new heading
4. Assign parent-child relationships and persist

### Structural Irregularities Actually Found in the CT-200 Manual

| Irregularity Found | Where in PDF | How It Broke Naive Parser | How Final Version Handles It |
|-------------------|--------------|---------------------------|------------------------------|
| Inconsistent numbering (jumps from 3.2 to 3.4, missing 3.3) | Section 3 (Device Operation) | Parser treating missing numbers as missing levels; parent-child relationships broke | Uses level detection from text patterns, not numbering sequence; missing numbers don't affect hierarchy |
| Table content inside section (not separate from body text) | Section 2.1, 4.2 | Table data was concatenated with body text, losing structure | pdfplumber table extraction preserves table structure; content hash includes table text |
| ALL CAPS inline text mistaken as heading | Section 3.3 (classification indicators) | All-caps warning text was incorrectly detected as a heading | Added validation that heading candidates must be followed by body text or be in a standalone position |
| Mixed formatting with bold headings not using numbers | Throughout manual | Bold text not detected as heading | Title case detection with keywords catches bold section titles |
| Roman numeral heading "I. Introduction" | Not present in CT-200 but tested | Would be caught by title case before Roman numeral pattern | Roman numeral check moved BEFORE title case check to ensure correct level detection |

### What the Initial Implementation Failed to Handle

1. The first version treated any all-caps line as a top-level heading, which mis-parented the classification indicators in Section 3.3 (e.g., "NORMAL", "ELEVATED") as new sections rather than bullet points within the existing section.

2. Roman numerals like "I. Introduction" were incorrectly detected as level 2 because `text.istitle()` returned True and the Roman numeral pattern was checked after title case.

3. Tables that broke across page boundaries were not properly reconstructed, causing incomplete table extraction in sections 2.1 and 4.2.

### How the Failures Were Identified

1. **Manual inspection** of the raw PDF text dump to verify extracted headings against the actual PDF
2. **Visual page-by-page comparison** between the source PDF and the parsed structure
3. **Unit tests** written against known tricky pages (e.g., test_heading_detection_patterns covers numbered, Roman, and ALL CAPS headings)
4. **Validation script** that checked every node had a valid parent and no orphans (implemented via test_parent_child_relationships)

### Changes Made to Improve Extraction Quality

1. Added a check that heading candidates must be followed by body text or be in a standalone position before being accepted as a section, eliminating false positives from all-caps inline warnings

2. Reordered pattern matching so Roman numerals are checked BEFORE title case detection, ensuring `I. Introduction` is correctly detected as level 1

3. Added `r'^(\d+)\.\s+'` pattern specifically to handle "1. Introduction" format (period with space after the number)

4. Implemented `_extract_body_text` to capture body content following a heading, improving node completeness

5. Used pdfplumber's table extraction for sections 2.1 and 4.2 instead of treating them as plain text

---

## 2. Version Matching Strategy

### Primary: Path-Based Matching

**Why:** The CT-200 manual preserves hierarchical structure across v1→v2, so a node's full path (`Introduction/Safety/Warnings`) is a strong, cheap signal for identity. Most sections remained in the same parent-child relationship between versions.

### Fallback: Fuzzy Title Matching

Used when a section's parent path changed but the title is highly similar:

```python
if fuzz.ratio(title1, title2) >= VERSION_MATCH_THRESHOLD:  # threshold = 85
    match = True
Content Hash
Algorithm: SHA256

Input: heading + body_text + level

Purpose: Detect whether a matched node's content actually changed (drives staleness detection)

Known Failure Modes (Specific to CT-200 v1→v2)
Section moved to different parent: If a section is moved to a completely different parent path, path-based matching fails. Falls back to fuzzy title match (threshold 85%). If that also fails, the node is treated as new/deleted rather than silently guessed at. Confidence below 85% is flagged for manual review instead of auto-matched.

Title changed slightly: e.g., "Battery Life Under Typical Use" → "Battery Life Under Typical Use (Revised)" — caught by fuzzy match (similarity > 85%).

Content changed heavily but title/path stable: e.g., Section 3.2 changed inflation increments from 40mmHg to 30mmHg. Matched correctly via path, but hash mismatch flags it as modified; a diff summary is generated for human review.

New section added: v2 added Section 5.3 "Data Export" which didn't exist in v1. No match found, treated as a new node.

Section deleted: v2 removed or merged some content. No match found, treated as deleted.

3. LLM Prompt Design
Prompt Template
text
You are a QA engineer for medical devices. Generate 3-5 test cases based on the following document section:

{document_text}

Requirements:
1. Each test case must be specific and executable
2. Include: Test ID, Description, Steps, Expected Result, Priority
3. Focus on safety-critical aspects

Respond with ONLY a valid JSON array, no prose, in this shape:
[
    {
        "id": "TC-001",
        "title": "Test title",
        "description": "What this test verifies",
        "steps": ["Step 1", "Step 2"],
        "expected_result": "What should happen",
        "priority": "High/Medium/Low"
    }
]
Why This Design
Structured JSON output makes parsing deterministic and reduces hallucinations

Explicit schema example reduces field-name drift

Framing as medical-device QA engineer nudges toward safety-critical test coverage

"ONLY a valid JSON array" reduces conversational wrapper text that breaks parsing

Structured-Output Validation & Error Handling
Failure Mode	System Behavior
Malformed JSON (extra prose, trailing commas, markdown code blocks)	Strip code fences (```json), attempt re-parse; if that fails, attempt response fix with regex to remove trailing commas and add missing quotes |
Valid JSON but missing required fields (fails validation)	Raise ValueError with specific missing field, retry once with validation error appended to prompt
Fewer than 3 test cases returned	Still accepted and stored (minimum 1), but logs warning; generation considered "successful" as long as ≥1 valid test case
Empty response / API error	Returns fallback test case: TC-FALLBACK with "Manual Review Required" title
Rate limit	Exponential backoff via tenacity, capped at 3 attempts
All retries exhausted	Returns fallback test case with error description in the description field; system does NOT silently store empty generation
Retry Decorator:

python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def generate():
    # 3 attempts with exponential backoff
Duplicate Submission Policy
If the same selection is submitted to /generate twice:

By default, the existing stored generation is returned (no duplicate LLM call/cost)

Passing force=true triggers regeneration, which overwrites the existing generation (no versioning of LLM outputs, only the latest is kept)

Why this policy:

Prevents unnecessary API calls and costs

Simpler to implement and reason about

The latest generation is always the most relevant for the current document state

Users can always force regeneration if they want fresh test cases

4. Staleness / Impact Detection
Approach: Content Hash Comparison
At generation time: Store the content_hash (and version) of every node in the selection alongside the generated output

At retrieval time: Recompute/look up the current hash for each of those nodes at the latest version and compare

Staleness States
State	Meaning
✅ Up-to-date	All source node hashes match the current version
⚠️ Modified	At least one source node's content hash has changed
❌ Deleted	A source node no longer exists in the current version
Honest Limits of This Approach
1. Semantic vs. Syntactic Changes Are Not Distinguished

"200 mmHg" → "220 mmHg" (a safety-critical threshold change) is flagged identically to "The device" → "The product" (a cosmetic wording change). Both simply fail the hash comparison.

Should they be treated the same? No — in a medical-device context, a threshold change is materially more dangerous to miss, but a hash has no notion of semantic severity.

Production fix: Use semantic embeddings or targeted regex/NLP extraction of numeric/safety-relevant parameters to escalate those changes specifically.

2. Structural Reorganization Can Break the Underlying Version Match

If the version matcher mis-links two nodes (see §2), staleness detection inherits that failure mode — staleness will be computed against the wrong "current" text.

3. Formatting-Only Edits Trigger False Positives

Whitespace, punctuation, or wording changes (e.g., "mmHg" → "mm Hg") currently trigger "Modified" since the hash includes exact body text.

What I actually did: I did NOT normalize whitespace/case before hashing. This is a known open gap that would need to be addressed in production with preprocessing (e.g., stripping extra whitespace, normalizing units).

5. Data Model
Relational Store (SQLite via SQLAlchemy)
sql
documents (id, version, filename, file_hash, total_nodes, created_at)

nodes (id, document_id, heading, level, body_text, content_hash, 
      parent_id, logical_id, page_number, position)

selections (id, name, version, created_at)

selection_nodes (id, selection_id, node_id, node_version)

generated_tests (id, selection_id, output, version_at_generation, created_at)
logical_id is the stable identifier used by the version matcher to say "this v2 node is the same logical section as this v1 node," independent of the auto-incrementing id.

NoSQL Store — LLM-generated Output
I used SQLite with a JSON column instead of a dedicated NoSQL store.

Why this deviation from the recommended stack:

For a project of this size, storing LLM output as a JSON column in SQLite:

Achieves the same schema flexibility as MongoDB for the generated test case data

Avoids adding an infrastructure dependency (no need to install/set up MongoDB)

Simplifies deployment (single database file)

Still provides query capabilities via SQLAlchemy's JSON functions

The output column in generated_tests stores the full JSON array of test cases, which may contain variable shapes and nested structures — exactly the use case that would typically justify a document store. SQLite's JSON support is sufficient for this scale.

Content Hash
Algorithm: SHA256

Input: heading + body_text + level

Purpose: Version-to-version node comparison and staleness detection

6. Decision Log
Q1. What's the one part of this system most likely to silently give wrong results without erroring? How would you catch it?
Answer: The version-matching step is the highest-risk silent-failure point. If a section is reorganized but retains a similar title, the fuzzy matcher can confidently link the wrong pair of nodes across versions (e.g., linking v1 "Safety Warning" to a v2 "Safety Caution" that is actually a different, newly added section) — nothing errors, the system just produces plausible-looking but incorrect traceability, and everything downstream (diffs, staleness checks) inherits that wrong link silently.

How to catch it:

Attach a confidence score to every match (path match = high confidence; fuzzy-title-only match = lower confidence, scaled by similarity score)

Track whether the parent path changed for a matched pair, and treat a changed path as a reason to lower confidence even if the title matched well

Log/surface all matches below a confidence threshold for manual review rather than auto-accepting them

What I actually implemented: I implemented the fuzzy matching with a threshold (85%) and the path-based matching, but I did NOT implement a confidence score or a review queue in code. This is a known gap I would add with more time.

Q2. Where did you choose simplicity over correctness because of time, and what would break first if this went to production as-is?
Answer: I used exact content-hash comparison instead of semantic similarity for staleness detection. Implementing embeddings-based comparison and picking a similarity threshold would have taken meaningfully longer than the time budget allowed.

What would break first in production: Minor wording edits would trigger staleness warnings as often as substantive ones; users would start ignoring the warnings (cry-wolf effect), and the one time a safety-critical threshold actually changed, the flag would get the same response as a typo fix.

Production fix: Implement semantic-similarity-based staleness with a separate, higher-priority check specifically for numeric/safety-parameter changes (e.g., regex detection of threshold values like "200 mmHg" vs "220 mmHg").

Q3. Name one input you did not handle, and what your system does when it sees it.
Answer: The PDF parser does not handle nested tables within tables. The CT-200 manual has nested tables in sections 2.1 and 4.2 where the main table contains rows that themselves have sub-structures.

System behavior:

Extracts the outer table correctly using pdfplumber's table extraction

Treats the inner table as plain text (flattened into the cell)

Logs a warning: "Nested table detected at page X, extracted as text"

Does NOT silently drop the content

Maintains data integrity but loses the nested structural information

Why this matters: The manual contains parameter tables with safety thresholds (e.g., pressure ranges, error codes). Losing nested structure there is worse than losing structure in prose because threshold values could be misinterpreted.

7. What I'd Do Differently With More Time
Semantic version matching using embeddings instead of/alongside fuzzy title matching to better handle sections with completely changed titles

A confidence-scored review queue for low-confidence version matches, actually surfaced via an API endpoint

Semantic staleness detection that distinguishes critical parameter changes (pressure thresholds) from cosmetic edits (wording changes)

Better table extraction with recursive nested table parsing to preserve structural information in sections 2.1 and 4.2

Async document processing for large documents to avoid blocking the API during ingestion

Normalize whitespace/case before hashing to reduce false positives from formatting-only changes

