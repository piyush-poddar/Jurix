"""
Prompts for legal case processing and RAG optimization.
"""

# Fact Summarization Prompt
SUMMARIZE_FACTS_PROMPT = """You are a legal document analyst. Your task is to create a concise, RAG-optimized summary of the facts section from a legal judgment.

**Original Facts:**
{facts}

**Instructions:**
1. Write a coherent paragraph that captures the essential facts
2. Include: parties involved, key dates, events, and relevant background
3. Preserve legal terminology, case numbers, and proper nouns exactly
4. Present facts in chronological order
5. Focus on facts that are material to the legal issues
6. Remove procedural history unless directly relevant
7. Eliminate redundant language and verbose descriptions
8. Use dense, information-rich sentences
9. Keep total length between 100-250 words
10. Write for optimal semantic similarity matching - use precise legal language

**Output Format:**
Provide a single coherent paragraph without headings or formatting. Write in past tense, third person.

**Summary:**
"""
