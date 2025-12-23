"""
AI Prompt Templates for Generation
Contains all prompts used for flashcard and quiz generation
"""

# =====================================================
# EXTRACTION PROMPTS
# =====================================================

EXTRACT_FACTS_PROMPT = """You are an expert educational content analyzer. Your task is to extract key facts, concepts, and learning points from the following study material.

CONTENT:
{content}

CONTEXT:
- Heading: {heading_context}
- Page(s): {page_range}
- Content Type: {content_type}

INSTRUCTIONS:
1. Identify all key facts, definitions, concepts, processes, and formulas
2. For each item, note:
   - The type (definition, concept, process, formula, fact)
   - The main term or concept name
   - The core content/explanation
   - Any related examples or applications
   - Difficulty level (1=basic recall, 3=application, 5=advanced reasoning)

3. Be precise and factual - only extract what is explicitly stated or directly implied
4. Maintain academic accuracy
5. Note any potential ambiguities

OUTPUT FORMAT (JSON):
{{
    "facts": [
        {{
            "type": "definition|concept|process|formula|fact",
            "term": "main term or concept",
            "content": "the core information",
            "example": "example if present, null otherwise",
            "difficulty": 1-5,
            "source_quote": "exact quote from content (max 200 chars)"
        }}
    ],
    "topics": ["list", "of", "topics", "covered"],
    "ambiguities": ["any unclear or potentially confusing content"]
}}

Extract all relevant facts from the content:"""

# =====================================================
# FLASHCARD GENERATION PROMPTS
# =====================================================

GENERATE_FLASHCARDS_PROMPT = """You are an expert educational content creator specializing in effective flashcard design. Create flashcards from the extracted facts below.

EXTRACTED FACTS:
{facts_json}

USER PREFERENCES:
- Difficulty preference: {difficulty}
- Include ELI5 explanations: {include_eli5}
- Include examples: {include_examples}
- Include mnemonics: {include_mnemonics}
- Card types to include: {card_types}

FLASHCARD DESIGN PRINCIPLES:
1. One concept per card (atomic)
2. Front should be a clear question or prompt
3. Back should be concise but complete
4. Include context clues without giving away the answer
5. For cloze deletions, remove a key term that tests understanding

CREATE FLASHCARDS:
For each fact, create an appropriate flashcard. Choose the best card type based on the content:
- BASIC: Simple question → answer
- DEFINITION: Term → definition with example
- CONCEPT: Concept question → explanation with "why it matters"
- PROCESS: Step/process question → ordered steps
- FORMULA: When to use → formula with variables explained
- CLOZE: Statement with [BLANK] → missing term
- ELI5: Complex concept → simple explanation

OUTPUT FORMAT (JSON):
{{
    "cards": [
        {{
            "card_type": "basic|definition|concept|process|formula|cloze|eli5",
            "front": "question or prompt",
            "back": "answer",
            "extra_explanation": "additional context if helpful",
            "example": "concrete example",
            "mnemonic": "memory aid if applicable",
            "cloze_text": "for cloze cards: 'The [BLANK] is...'",
            "cloze_answer": "for cloze cards: the missing word",
            "difficulty": 1-5,
            "source_quote": "supporting quote from original content",
            "source_fact_index": 0
        }}
    ]
}}

Generate high-quality flashcards:"""

# =====================================================
# QUIZ GENERATION PROMPTS
# =====================================================

GENERATE_QUIZ_PROMPT = """You are an expert educational assessment designer. Create quiz questions from the extracted facts below.

EXTRACTED FACTS:
{facts_json}

QUIZ SETTINGS:
- Target question count: {question_count}
- Difficulty preference: {difficulty}
- Question types to include: {question_types}

QUESTION DESIGN PRINCIPLES:
1. Questions should test understanding, not just memorization
2. All options in MCQ should be plausible
3. Avoid "all of the above" or "none of the above"
4. Short answer questions should have clear, specific expected answers
5. True/False statements should be unambiguous
6. Match difficulty to content complexity

QUESTION TYPES:
- MCQ: Multiple choice with 4 options (A, B, C, D)
- MULTI_SELECT: Multiple correct answers possible
- TRUE_FALSE: Statement that is clearly true or false
- SHORT_ANSWER: Brief text response expected
- FILL_BLANK: Complete the sentence
- MATCHING: Match items from two columns

OUTPUT FORMAT (JSON):
{{
    "questions": [
        {{
            "question_type": "mcq|multi_select|true_false|short_answer|fill_blank|matching",
            "question_text": "the question",
            "options": [
                {{"id": "a", "text": "Option A"}},
                {{"id": "b", "text": "Option B"}},
                {{"id": "c", "text": "Option C"}},
                {{"id": "d", "text": "Option D"}}
            ],
            "correct_answer": "a",
            "explanation": "why this is correct and others are wrong",
            "difficulty": 1-5,
            "topic": "topic this question covers",
            "source_quote": "supporting evidence from content",
            "source_fact_index": 0
        }}
    ]
}}

NOTES FOR SPECIFIC TYPES:
- For multi_select: correct_answer is a list like ["a", "c"]
- For true_false: correct_answer is "true" or "false", options not needed
- For short_answer: correct_answer is the expected text, options not needed
- For fill_blank: question_text contains "___" for the blank
- For matching: options has "left" and "right" arrays, correct_answer is mapping like {{"1": "a", "2": "b"}}

Generate quiz questions:"""

# =====================================================
# VERIFICATION PROMPTS
# =====================================================

VERIFY_CARD_PROMPT = """You are a quality assurance expert for educational content. Verify that the following flashcard is accurate and supported by the source material.

FLASHCARD:
- Front: {front}
- Back: {back}
- Type: {card_type}

SOURCE CONTENT:
{source_content}

CITED QUOTE:
{source_quote}

VERIFICATION CHECKLIST:
1. Is the answer factually accurate according to the source?
2. Is the answer fully supported by the cited content?
3. Are there any hallucinations or unsupported claims?
4. Is the question clear and unambiguous?
5. Does the difficulty rating match the content?

OUTPUT FORMAT (JSON):
{{
    "is_verified": true|false,
    "confidence": 0.0-1.0,
    "issues": ["list of issues if any"],
    "suggested_fix": "correction if needed, null if verified",
    "verification_notes": "explanation of verification decision"
}}

Verify this flashcard:"""

VERIFY_QUESTION_PROMPT = """You are a quality assurance expert for educational assessments. Verify that the following quiz question is accurate, fair, and supported by the source material.

QUESTION:
- Type: {question_type}
- Text: {question_text}
- Options: {options}
- Correct Answer: {correct_answer}
- Explanation: {explanation}

SOURCE CONTENT:
{source_content}

CITED QUOTE:
{source_quote}

VERIFICATION CHECKLIST:
1. Is the correct answer actually correct according to the source?
2. Are all incorrect options clearly wrong (no ambiguity)?
3. Is the question fair and answerable from the source content?
4. Is the explanation accurate and helpful?
5. Are there any trick questions or unfair elements?
6. Does the difficulty match the question complexity?

OUTPUT FORMAT (JSON):
{{
    "is_verified": true|false,
    "confidence": 0.0-1.0,
    "issues": ["list of issues if any"],
    "suggested_fix": "correction if needed, null if verified",
    "verification_notes": "explanation of verification decision"
}}

Verify this question:"""

# =====================================================
# DIFFICULTY CALIBRATION PROMPT
# =====================================================

CALIBRATE_DIFFICULTY_PROMPT = """Analyze the difficulty of this educational item based on cognitive complexity.

ITEM:
{item_content}

CONTENT TYPE: {item_type}

DIFFICULTY CRITERIA:
- Level 1 (Easy): Direct recall, simple definitions, basic facts
- Level 2 (Easy-Medium): Recognition, simple comparisons
- Level 3 (Medium): Application, understanding relationships
- Level 4 (Medium-Hard): Analysis, comparing multiple concepts
- Level 5 (Hard): Synthesis, evaluation, multi-step reasoning

OUTPUT FORMAT (JSON):
{{
    "difficulty": 1-5,
    "reasoning": "why this difficulty level",
    "cognitive_skills": ["recall", "understand", "apply", "analyze", "evaluate", "create"]
}}

Assess difficulty:"""

# =====================================================
# TOPIC EXTRACTION PROMPT
# =====================================================

EXTRACT_TOPICS_PROMPT = """Extract key topics and subtopics from this educational content.

CONTENT:
{content}

HEADING CONTEXT: {heading}

Extract a hierarchical list of topics covered.

OUTPUT FORMAT (JSON):
{{
    "main_topic": "primary topic",
    "subtopics": ["list", "of", "subtopics"],
    "key_terms": ["important", "vocabulary", "terms"],
    "related_concepts": ["concepts", "that", "connect", "to", "other", "material"]
}}

Extract topics:"""
