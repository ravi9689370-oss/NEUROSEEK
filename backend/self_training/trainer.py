"""
Self-Training Engine — Background mein khud seekhta hai
123,648 NCERT questions ko automatically process karta hai
"""

import json
import os
import re
import time
import threading
from typing import Optional, List, Dict
from datetime import datetime
from collections import defaultdict


class SelfTrainingEngine:
    """
    Self-training engine jo:
    1. Background mein NCERT questions process karta hai
    2. Har question-answer pair ko samajhta hai
    3. User interactions se seekhta hai
    4. Continuous learning karta hai
    """

    def __init__(self, hf_ncert_kb, db):
        self.hf_ncert_kb = hf_ncert_kb
        self.db = db
        self.training_data = {}
        self.concept_graph = defaultdict(list)
        self.learning_stats = {
            "total_processed": 0,
            "total_learned": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": None
        }
        self.is_training = False
        self.training_thread = None

    def start_background_training(self):
        """Background training start karta hai"""
        if self.is_training:
            return

        self.is_training = True
        self.training_thread = threading.Thread(target=self._training_loop, daemon=True)
        self.training_thread.start()
        print("🧠 Self-training started in background...")

    def stop_background_training(self):
        """Background training stop karta hai"""
        self.is_training = False
        if self.training_thread:
            self.training_thread.join(timeout=5)
        print("🛑 Self-training stopped.")

    def _training_loop(self):
        """Background training loop"""
        while self.is_training:
            try:
                # NCERT questions process karo
                self._process_ncert_questions()

                # Concept graph update karo
                self._update_concept_graph()

                # Stats update karo
                self.learning_stats["last_update"] = datetime.now().isoformat()

                # 30 second wait karo
                time.sleep(30)

            except Exception as e:
                print(f"Training error: {e}")
                time.sleep(10)

    def _process_ncert_questions(self):
        """NCERT questions process karta hai"""
        if not self.hf_ncert_kb.questions:
            return

        # Process karo har question
        for q in self.hf_ncert_kb.questions:
            topic = q.get('Topic', '')
            question = q.get('Question', '')
            answer = q.get('Answer', '')
            explanation = q.get('Explanation', '')
            subject = q.get('subject', '')
            grade = q.get('grade', '')

            if not question or not answer:
                continue

            # Training data mein store karo
            key = f"{subject}_{grade}_{topic}"
            if key not in self.training_data:
                self.training_data[key] = []

            self.training_data[key].append({
                "question": question,
                "answer": answer,
                "explanation": explanation,
                "topic": topic,
                "subject": subject,
                "grade": grade,
                "processed_at": datetime.now().isoformat()
            })

            self.learning_stats["total_processed"] += 1

        self.learning_stats["total_learned"] = len(self.training_data)

    def _update_concept_graph(self):
        """Concept graph update karta hai"""
        for key, items in self.training_data.items():
            for item in items:
                topic = item.get('topic', '')
                subject = item.get('subject', '')

                if topic and subject:
                    self.concept_graph[subject].append({
                        "topic": topic,
                        "related": self._find_related_topics(topic, subject)
                    })

    def _find_related_topics(self, topic: str, subject: str) -> List[str]:
        """Related topics find karta hai"""
        related = []
        topic_words = set(topic.lower().split())

        for key, items in self.training_data.items():
            if subject in key:
                for item in items:
                    other_topic = item.get('topic', '')
                    if other_topic != topic:
                        other_words = set(other_topic.lower().split())
                        common = topic_words & other_words
                        if common:
                            related.append(other_topic)

        return list(set(related))[:5]

    def search(self, query: str, max_results: int = 3) -> Optional[str]:
        """
        Training data mein search karta hai
        """
        if not self.training_data:
            return None

        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score each item
        scored_items = []
        for key, items in self.training_data.items():
            for item in items:
                score = 0
                question = item.get('question', '').lower()
                answer = item.get('answer', '').lower()
                topic = item.get('topic', '').lower()
                explanation = item.get('explanation', '').lower()

                for word in query_words:
                    if word in question:
                        score += 10
                    if word in answer:
                        score += 8
                    if word in topic:
                        score += 6
                    if word in explanation:
                        score += 4

                if score > 0:
                    scored_items.append((score, item))

        # Sort by score
        scored_items.sort(key=lambda x: x[0], reverse=True)

        if not scored_items:
            return None

        # Top results format karo
        results = []
        for score, item in scored_items[:max_results]:
            results.append({
                'topic': item.get('topic', 'N/A'),
                'question': item.get('question', 'N/A'),
                'answer': item.get('answer', 'N/A'),
                'explanation': item.get('explanation', 'N/A'),
                'subject': item.get('subject', 'N/A'),
                'grade': item.get('grade', 'N/A'),
                'score': score
            })

        # Format response
        response = f"🧠 **Self-Trained AI Response**\n\n"
        response += f"**Training Stats:** {self.learning_stats['total_processed']} questions processed\n\n"

        for i, r in enumerate(results, 1):
            response += f"**{i}. {r['topic']}** (Score: {r['score']})\n"
            response += f"   **Subject:** {r['subject']} | **Grade:** {r['grade']}\n"
            response += f"   **Q:** {r['question']}\n"
            response += f"   **A:** {r['answer']}\n"
            if r['explanation'] != 'N/A':
                response += f"   **Explanation:** {r['explanation'][:150]}...\n"
            response += "\n"

        response += "---\n📡 **Source:** Self-Trained AI (NCERT Dataset)\n🧠 **Domain:** Universal Expert"

        return response

    def learn_from_user(self, query: str, response: str):
        """User interaction se seekhta hai"""
        # User query ko training data mein add karo
        key = f"user_{datetime.now().strftime('%Y%m%d')}"
        if key not in self.training_data:
            self.training_data[key] = []

        self.training_data[key].append({
            "question": query,
            "answer": response,
            "explanation": "User interaction",
            "topic": "User Query",
            "subject": "General",
            "grade": "All",
            "processed_at": datetime.now().isoformat()
        })

        self.learning_stats["total_processed"] += 1

    def get_stats(self) -> dict:
        """Training statistics deta hai"""
        return {
            "total_processed": self.learning_stats["total_processed"],
            "total_learned": self.learning_stats["total_learned"],
            "start_time": self.learning_stats["start_time"],
            "last_update": self.learning_stats["last_update"],
            "is_training": self.is_training,
            "concept_graph_size": len(self.concept_graph)
        }
