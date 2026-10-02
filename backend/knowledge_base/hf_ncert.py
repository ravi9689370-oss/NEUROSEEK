"""
Hugging Face NCERT Dataset Integration
123,648 NCERT questions AI engine mein integrate karta hai
"""

import csv
import json
import os
import re
from typing import Optional, List, Dict
from datetime import datetime


class HFNCERTKnowledgeBase:
    """
    Hugging Face NCERT Dataset se trained knowledge base
    123,648 questions, answers, explanations ke saath
    """

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "hf_data")
        self.questions = []
        self.topics = {}
        self.subjects = {}
        self.grades = {}
        self._load_data()

    def _load_data(self):
        """NCERT dataset load karta hai"""
        filepath = os.path.join(self.data_dir, "ParthKadam2003_NCERT_Dataset.json")

        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.questions.append(row)

                    # Topics index
                    topic = row.get('Topic', '')
                    if topic:
                        if topic not in self.topics:
                            self.topics[topic] = []
                        self.topics[topic].append(row)

                    # Subjects index
                    subject = row.get('subject', '')
                    if subject:
                        if subject not in self.subjects:
                            self.subjects[subject] = []
                        self.subjects[subject].append(row)

                    # Grades index
                    grade = row.get('grade', '')
                    if grade:
                        if grade not in self.grades:
                            self.grades[grade] = []
                        self.grades[grade].append(row)

        except Exception as e:
            print(f"Error loading NCERT data: {e}")

    def search(self, query: str, max_results: int = 3) -> Optional[str]:
        """
        NCERT dataset mein search karta hai
        """
        if not self.questions:
            return None

        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score each question
        scored_questions = []
        for q in self.questions:
            score = 0
            question_text = q.get('Question', '').lower()
            topic_text = q.get('Topic', '').lower()
            explanation = q.get('Explanation', '').lower()
            answer = q.get('Answer', '').lower()
            subject = q.get('subject', '').lower()
            grade = q.get('grade', '').lower()

            # Question match
            for word in query_words:
                if word in question_text:
                    score += 10
                if word in topic_text:
                    score += 8
                if word in explanation:
                    score += 5
                if word in answer:
                    score += 3
                if word in subject:
                    score += 2

            # Exact phrase match
            if query_lower in question_text:
                score += 20
            if query_lower in topic_text:
                score += 15

            if score > 0:
                scored_questions.append((score, q))

        # Sort by score
        scored_questions.sort(key=lambda x: x[0], reverse=True)

        if not scored_questions:
            return None

        # Top results format karo
        results = []
        for score, q in scored_questions[:max_results]:
            results.append({
                'topic': q.get('Topic', 'N/A'),
                'question': q.get('Question', 'N/A'),
                'answer': q.get('Answer', 'N/A'),
                'explanation': q.get('Explanation', 'N/A'),
                'difficulty': q.get('Difficulty', 'N/A'),
                'subject': q.get('subject', 'N/A'),
                'grade': q.get('grade', 'N/A'),
                'score': score
            })

        # Format response
        response = f"📚 **NCERT Dataset Results** ({len(self.questions)} questions searched)\n\n"

        for i, r in enumerate(results, 1):
            response += f"**{i}. {r['topic']}** (Score: {r['score']})\n"
            response += f"   **Subject:** {r['subject']} | **Grade:** {r['grade']} | **Difficulty:** {r['difficulty']}\n"
            response += f"   **Q:** {r['question']}\n"
            response += f"   **A:** {r['answer']}\n"
            if r['explanation'] != 'N/A':
                response += f"   **Explanation:** {r['explanation'][:200]}...\n"
            response += "\n"

        response += "---\n📡 **Source:** Hugging Face NCERT Dataset (123,648 questions)\n🧠 **Domain:** NCERT Knowledge Base"

        return response

    def get_by_subject(self, subject: str, max_results: int = 5) -> Optional[str]:
        """Subject wise questions get karta hai"""
        if subject not in self.subjects:
            return None

        questions = self.subjects[subject][:max_results]
        response = f"📚 **NCERT {subject.title()} Questions**\n\n"

        for i, q in enumerate(questions, 1):
            response += f"**{i}. {q.get('Topic', 'N/A')}**\n"
            response += f"   **Q:** {q.get('Question', 'N/A')}\n"
            response += f"   **A:** {q.get('Answer', 'N/A')}\n"
            response += f"   **Grade:** {q.get('grade', 'N/A')} | **Difficulty:** {q.get('Difficulty', 'N/A')}\n\n"

        response += "---\n📡 **Source:** Hugging Face NCERT Dataset\n🧠 **Domain:** NCERT Knowledge Base"
        return response

    def get_by_grade(self, grade: str, max_results: int = 5) -> Optional[str]:
        """Grade wise questions get karta hai"""
        if grade not in self.grades:
            return None

        questions = self.grades[grade][:max_results]
        response = f"📚 **NCERT Grade {grade} Questions**\n\n"

        for i, q in enumerate(questions, 1):
            response += f"**{i}. {q.get('Topic', 'N/A')}**\n"
            response += f"   **Q:** {q.get('Question', 'N/A')}\n"
            response += f"   **A:** {q.get('Answer', 'N/A')}\n"
            response += f"   **Subject:** {q.get('subject', 'N/A')} | **Difficulty:** {q.get('Difficulty', 'N/A')}\n\n"

        response += "---\n📡 **Source:** Hugging Face NCERT Dataset\n🧠 **Domain:** NCERT Knowledge Base"
        return response

    def get_stats(self) -> dict:
        """Dataset statistics deta hai"""
        return {
            "total_questions": len(self.questions),
            "total_topics": len(self.topics),
            "total_subjects": len(self.subjects),
            "total_grades": len(self.grades),
            "subjects": list(self.subjects.keys()),
            "grades": list(self.grades.keys())
        }
