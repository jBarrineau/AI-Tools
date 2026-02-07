---
name: prompt-coach
description: Review the current session to provide actionable feedback on prompting. Use this skill when the user asks for recommendations, tips, or a review of their instructions to improve clarity and efficiency in future sessions.
---

# Prompt Coach

This skill helps users refine their prompting technique by analyzing the current session's history and identifying areas for improvement based on industry best practices.

## Workflow: Session Review

When triggered, follow these steps to conduct a thorough prompting audit:

1.  **Analyze History**: Review the user's prompts throughout the session. Look for:
    *   Instructions that led to errors or "incorrect" outputs.
    *   Vague requests (e.g., "fix this", "make it better").
    *   Prompts that required you to ask for clarification.
    *   Instructions that lacked necessary context (file paths, variable names).
2.  **Consult Benchmarks**: Use the standards defined in the "Best Practices & Benchmarks" section below to evaluate each prompt.
3.  **Identify Patterns**: Look for recurring issues (e.g., consistently forgetting to specify file paths, using ambiguous pronouns like "it").
4.  **Generate Feedback**: Provide a structured report focusing on the highest-impact improvements.

## Feedback Structure

For each identified improvement, provide:

*   **Original Prompt**: The exact (or summarized) text of the prompt.
*   **Critique**: A clear explanation of why the prompt was suboptimal (e.g., "Too vague", "Missing constraints").
*   **Impact**: How this affected the session (e.g., "Led to a 404 error", "Caused two rounds of clarification").
*   **Recommendation**: A rewritten version of the prompt that follows best practices.
*   **The "Why"**: A brief tip on the underlying principle (e.g., "Always specify the target file to avoid ambiguity").

## Best Practices & Benchmarks

This reference guide provides benchmarks and standards for high-quality prompting. Use these principles to evaluate user instructions and provide constructive feedback.

### Core Principles

#### 1. Specificity & Precision
*   **The Goal**: Eliminate ambiguity.
*   **Good**: "In `auth.js`, update the `login` function to handle 401 errors by redirecting to `/login?error=unauthorized`."
*   **Bad**: "Fix the login bug."
*   **Benchmark**: Does the prompt specify *what*, *where*, and *how*?

#### 2. Contextual Completeness
*   **The Goal**: Provide all necessary information (files, variables, environment).
*   **Good**: "Using the `User` model defined in `models/user.py`, add a `full_name` property that concatenates `first_name` and `last_name`."
*   **Bad**: "Add a full name property to the user."
*   **Benchmark**: Could a developer perform this task without asking for missing files or definitions?

#### 3. Intent & Goal Alignment
*   **The Goal**: Explain *why* a change is being made.
*   **Good**: "Refactor the database connection to use a singleton pattern to prevent multiple active connections during high traffic."
*   **Bad**: "Change the database connection to a singleton."
*   **Benchmark**: Is the ultimate objective clear?

#### 4. Constraints & Requirements
*   **The Goal**: Set boundaries (performance, library usage, style).
*   **Good**: "Implement a sorting algorithm without using external libraries, keeping time complexity to O(n log n)."
*   **Bad**: "Write a fast sorting function."
*   **Benchmark**: Are there explicit "dos" and "dont's"?

### Advanced Techniques

#### Chain-of-Thought (CoT)
Encourage the agent to "think out loud" for complex tasks.
*   **Prompting Strategy**: "Think step-by-step through the logic of this multi-stage data transformation before writing any code."

#### Few-Shot Prompting
Provide examples of the desired output format or style.
*   **Prompting Strategy**: "Format the logs like this: [TIMESTAMP] [LEVEL] [MESSAGE]. Example: 2023-10-27 INFO: Server started."

#### Negative Constraints
Explicitly state what should *not* be done.
*   **Prompting Strategy**: "Update the UI but do NOT use any new CSS frameworks; stick to pure Tailwind."

### Common Anti-Patterns

| Anti-Pattern | Description | Recommendation |
| :--- | :--- | :--- |
| **Vague Verbs** | Using "fix", "update", "change" without detail. | Specify the exact logic or line to be modified. |
| **Ambiguous Pronouns** | Using "it", "that", "this" for multiple objects. | Repeat the name of the file, function, or variable. |
| **Missing Scope** | Not defining the boundaries of the task. | Use file paths and line numbers where possible. |
| **Hidden Assumptions** | Assuming the agent knows the project structure. | Always verify the structure using `ls` or `grep` first. |
| **Mega-Prompts** | Combining 10 unrelated tasks into one prompt. | Break tasks into atomic, sequential instructions. |

## Example Usage

**User**: "How can I improve my prompts for the next session?"

**Agent**: "I've reviewed our session. Here are three ways you can improve your prompting:
1. **Be more specific with file paths**: In turn 3, you said 'Update the CSS', which led me to search multiple files. A better prompt would be 'Update the button styles in src/styles/main.css'.
2. ..."
