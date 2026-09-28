"""
AI Interview Coach - plain Python, runs in the terminal
---------------------------------------------------------
How to run:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here     (Windows: set ANTHROPIC_API_KEY=your_key_here)
    python interview_coach.py

What it does:
    1. Asks which job role you're interviewing for
    2. Generates interview questions with Claude
    3. Asks you each question, you type your answer
    4. Gives a score (1-10), strengths, improvements and a model answer
    5. Shows your average score and saves a report to interview_report.txt
"""

import json
import os
import sys
from datetime import datetime

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"


def get_client() -> Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Missing ANTHROPIC_API_KEY. Set it first, then run again.")
        sys.exit(1)
    return Anthropic()


def ask_claude_json(client: Anthropic, prompt: str) -> dict:
    """Send a prompt to Claude and parse the reply as JSON."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()

    # Remove ```json fences if Claude added them
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()

    return json.loads(text)


def generate_questions(client: Anthropic, role: str, level: str, count: int) -> list[str]:
    prompt = f"""
    Generate {count} realistic interview questions for a {level} {role} position.
    Mix behavioral and technical questions.

    Respond ONLY with valid JSON, no other text:
    {{"questions": ["question 1", "question 2"]}}
    """
    return ask_claude_json(client, prompt)["questions"]


def evaluate_answer(client: Anthropic, role: str, question: str, answer: str) -> dict:
    prompt = f"""
    You are an honest but encouraging interview coach for {role} candidates.

    Question: "{question}"
    Candidate's answer: "{answer}"

    Respond ONLY with valid JSON, no other text:
    {{
      "score": <integer 1-10>,
      "strengths": ["...", "..."],
      "improvements": ["...", "..."],
      "model_answer": "a short example of a strong answer"
    }}
    """
    return ask_claude_json(client, prompt)


def print_feedback(feedback: dict) -> None:
    print(f"\n  Score: {feedback['score']}/10")
    print("  Strengths:")
    for item in feedback["strengths"]:
        print(f"    + {item}")
    print("  To improve:")
    for item in feedback["improvements"]:
        print(f"    - {item}")
    print(f"  Model answer: {feedback['model_answer']}\n")


def save_report(role: str, level: str, results: list[dict], average: float) -> str:
    filename = "interview_report.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(f"Interview Report - {role} ({level})\n")
        file.write(f"Date: {datetime.now():%Y-%m-%d %H:%M}\n")
        file.write(f"Average score: {average:.1f}/10\n")
        file.write("=" * 60 + "\n\n")
        for number, result in enumerate(results, start=1):
            file.write(f"Q{number}. {result['question']}\n")
            file.write(f"Your answer: {result['answer']}\n")
            file.write(f"Score: {result['feedback']['score']}/10\n")
            file.write("Strengths: " + "; ".join(result["feedback"]["strengths"]) + "\n")
            file.write("Improvements: " + "; ".join(result["feedback"]["improvements"]) + "\n")
            file.write(f"Model answer: {result['feedback']['model_answer']}\n\n")
    return filename


def main() -> None:
    client = get_client()

    print("=== AI Interview Coach ===\n")
    role = input("Job role (e.g. Data Analyst): ").strip() or "Software Engineer"
    level = input("Level (entry-level / mid-level / senior) [mid-level]: ").strip() or "mid-level"
    count_text = input("Number of questions [5]: ").strip()
    count = int(count_text) if count_text.isdigit() and int(count_text) > 0 else 5

    print("\nGenerating your questions...\n")
    try:
        questions = generate_questions(client, role, level, count)
    except Exception as error:
        print(f"Couldn't generate questions: {error}")
        sys.exit(1)

    results = []
    for number, question in enumerate(questions, start=1):
        print(f"Question {number}/{len(questions)}: {question}")
        answer = input("Your answer (type 'skip' to skip, 'quit' to stop): ").strip()

        if answer.lower() == "quit":
            break
        if answer.lower() == "skip" or not answer:
            print("Skipped.\n")
            continue

        print("Evaluating...")
        try:
            feedback = evaluate_answer(client, role, question, answer)
        except Exception as error:
            print(f"Couldn't evaluate that answer: {error}\n")
            continue

        print_feedback(feedback)
        results.append({"question": question, "answer": answer, "feedback": feedback})

    if not results:
        print("No answers were scored. See you next time!")
        return

    average = sum(r["feedback"]["score"] for r in results) / len(results)
    print("=" * 40)
    print(f"Interview finished. Average score: {average:.1f}/10 across {len(results)} answers.")
    filename = save_report(role, level, results, average)
    print(f"Full report saved to {filename}")


if __name__ == "__main__":
    main()