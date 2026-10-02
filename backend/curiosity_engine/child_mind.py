"""
Child Curiosity Engine — Bachche Jaisi Soch
Pure curiosity, zero bias, self-questioning system
"""

import json
import os
import re
from typing import Optional, List, Dict
from datetime import datetime


class ChildCuriosityEngine:
    """
    Child-like curiosity engine jo:
    1. Pure curiosity se sawal poochta hai
    2. Zero bias ke saath jawab deta hai
    3. Self-questioning karta hai
    4. NCERT books se seekhta hai
    5. YouTube se bhi seekh sakta hai
    """

    def __init__(self):
        self.question_words = self._get_all_question_words()
        self.mental_models = {}
        self.learning_history = []
        self.curiosity_level = 1.0  # 0.0 to 1.0

    def _get_all_question_words(self) -> dict:
        """Saare question words ki list"""
        return {
            "core": {
                "kya": "What — kisi cheez ki pehchaan",
                "kyun": "Why — kaaran, uddeshy, tark",
                "kaise": "How — prakriya, tareeka",
                "kab": "When — samay, kshan, avsar",
                "kahan": "Where — sthan, jagah, sthiti",
                "kaun": "Who — vyakt, jeev, karta"
            },
            "relationship": {
                "kiska": "Whose — adhikar, swamitva",
                "kiske_liye": "For whom — uddeshy, upyog, labharthi",
                "kiske_saath": "With whom — sangat, judav, sahbhagita",
                "kiske_bare_mein": "About — vishay, sandarbh",
                "kiske_dwara": "By whom — sadhan, madhyam, tool",
                "kisse": "From whom — srot, samvad ka madhyam"
            },
            "quantity": {
                "kitna": "How much — sankhya, matra, vajan, map",
                "kaunsa": "Which one — vikalp mein se chunav",
                "kaisa": "How — gun, svabhav, sthiti, rup-rang"
            },
            "spatial": {
                "kidhar": "Which way — disha",
                "kahan_se": "From where — shuruaat, utpatti",
                "kahan_tak": "Up to where — seema, gantavya",
                "kab_se": "Since when — shuruaat ka samay",
                "kab_tak": "Until when — samay ki seema",
                "kis_had_tak": "To what extent — prabhav ki gehrai",
                "kis_vajah_se": "Due to what — visht sthiti ki jad"
            }
        }

    def analyze_question(self, user_input: str) -> dict:
        """
        User input ko child-like curiosity se analyze karta hai
        """
        user_lower = user_input.lower()

        # Detect question type
        question_type = self._detect_question_type(user_lower)

        # Detect subject
        subject = self._detect_subject(user_lower)

        # Detect class level
        class_level = self._detect_class_level(user_lower)

        # Generate child-like curiosity questions
        curiosity_questions = self._generate_curiosity_questions(user_lower, question_type)

        return {
            "question_type": question_type,
            "subject": subject,
            "class_level": class_level,
            "curiosity_questions": curiosity_questions,
            "curiosity_level": self.curiosity_level
        }

    def _detect_question_type(self, query: str) -> str:
        """Question type detect karta hai"""
        for category, words in self.question_words.items():
            for word in words:
                if word in query:
                    return category
        return "general"

    def _detect_subject(self, query: str) -> Optional[str]:
        """Subject detect karta hai"""
        subjects = {
            "mathematics": ["math", "mathematics", "ganit", "number", "addition", "subtraction", "multiplication", "division", "algebra", "geometry", "trigonometry", "calculus", "equation", "fraction", "decimal"],
            "science": ["science", "vigyan", "physics", "chemistry", "biology", "cell", "atom", "molecule", "force", "energy", "light", "sound", "plant", "animal", "human body"],
            "social_science": ["social", "history", "geography", "civics", "economics", "politics", "constitution", "democracy", "war", "empire", "king", "revolution"],
            "english": ["english", "grammar", "essay", "story", "poem", "writing", "reading", "comprehension", "literature"],
            "hindi": ["hindi", "vyakran", "nibandh", "kahani", "kavita", "shabd", "vaky"]
        }

        for subject, keywords in subjects.items():
            if any(kw in query for kw in keywords):
                return subject

        return None

    def _detect_class_level(self, query: str) -> Optional[str]:
        """Class level detect karta hai"""
        class_patterns = {
            "class_1": ["class 1", "class one", "1st class", "pehli class"],
            "class_2": ["class 2", "class two", "2nd class", "doosri class"],
            "class_3": ["class 3", "class three", "3rd class", "teesri class"],
            "class_4": ["class 4", "class four", "4th class", "chauthi class"],
            "class_5": ["class 5", "class five", "5th class", "panchvi class"],
            "class_6": ["class 6", "class six", "6th class", "chhathi class"],
            "class_7": ["class 7", "class seven", "7th class", "saatvi class"],
            "class_8": ["class 8", "class eight", "8th class", "aathvi class"],
            "class_9": ["class 9", "class nine", "9th class", "nauvi class"],
            "class_10": ["class 10", "class ten", "10th class", "dasvi class"],
            "class_11": ["class 11", "class eleven", "11th class", "gyarahvi class"],
            "class_12": ["class 12", "class twelve", "12th class", "barahvi class"]
        }

        for class_level, patterns in class_patterns.items():
            if any(pattern in query for pattern in patterns):
                return class_level

        return None

    def _generate_curiosity_questions(self, query: str, question_type: str) -> List[str]:
        """Child-like curiosity questions generate karta hai"""
        questions = []

        # Core curiosity questions
        if "kya" in query or "what" in query:
            questions.append("Yeh kya hai?")
            questions.append("Iska kya matlab hai?")
            questions.append("Yeh kaise kaam karta hai?")

        if "kyun" in query or "why" in query:
            questions.append("Aisa kyun hota hai?")
            questions.append("Iska kya kaaran hai?")
            questions.append("Kya aur koi kaaran ho sakta hai?")

        if "kaise" in query or "how" in query:
            questions.append("Yeh kaise hota hai?")
            questions.append("Isme kya prakriya hoti hai?")
            questions.append("Kya isme koi aur tareeka hai?")

        if "kab" in query or "when" in query:
            questions.append("Yeh kab hota hai?")
            questions.append("Iska samay kya hai?")
            questions.append("Kya yeh kabhi bhi ho sakta hai?")

        if "kahan" in query or "where" in query:
            questions.append("Yeh kahan hota hai?")
            questions.append("Iska sthan kya hai?")
            questions.append("Kya yeh kahin bhi ho sakta hai?")

        if "kaun" in query or "who" in query:
            questions.append("Yeh kaun hai?")
            questions.append("Iska karta kaun hai?")
            questions.append("Kya koi aur ho sakta hai?")

        # Add subject-specific curiosity
        subject = self._detect_subject(query)
        if subject:
            questions.append(f"{subject.title()} mein aur kya jaanna hai?")
            questions.append(f"Kya {subject} se judi koi aur cheez hai?")

        return questions[:5]  # Max 5 questions

    def generate_child_response(self, user_input: str, ncert_data: str = None) -> str:
        """
        Child-like curiosity se response generate karta hai
        """
        analysis = self.analyze_question(user_input)

        # Agar NCERT data hai toh use karo
        if ncert_data:
            response = f"🧒 **Child Curiosity Response**\n\n"
            response += f"**Aapne poochha:** {user_input}\n\n"
            response += f"**NCERT Knowledge:**\n{ncert_data}\n\n"
            response += f"**Curiosity Questions:**\n"
            for i, q in enumerate(analysis["curiosity_questions"], 1):
                response += f"{i}. {q}\n"
            response += f"\n---\n📡 **Source:** NCERT + Child Curiosity Engine\n🧠 **Domain:** {analysis['subject'] or 'Universal'}"
            return response

        # General child curiosity response
        response = f"🧒 **Child Curiosity Response**\n\n"
        response += f"**Aapne poochha:** {user_input}\n\n"
        response += f"**Curiosity Analysis:**\n"
        response += f"- Question Type: {analysis['question_type']}\n"
        response += f"- Subject: {analysis['subject'] or 'General'}\n"
        response += f"- Class Level: {analysis['class_level'] or 'All'}\n\n"
        response += f"**Curiosity Questions:**\n"
        for i, q in enumerate(analysis["curiosity_questions"], 1):
            response += f"{i}. {q}\n"
        response += f"\n---\n📡 **Source:** Child Curiosity Engine\n🧠 **Domain:** {analysis['subject'] or 'Universal'}"

        return response

    def learn_from_interaction(self, query: str, response: str, feedback: str = None):
        """Interaction se seekhta hai"""
        self.learning_history.append({
            "query": query,
            "response": response,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        })

        # Curiosity level adjust karo
        if feedback == "positive":
            self.curiosity_level = min(1.0, self.curiosity_level + 0.1)
        elif feedback == "negative":
            self.curiosity_level = max(0.1, self.curiosity_level - 0.1)

    def get_learning_stats(self) -> dict:
        """Learning statistics deta hai"""
        return {
            "total_interactions": len(self.learning_history),
            "curiosity_level": self.curiosity_level,
            "recent_interactions": self.learning_history[-10:] if self.learning_history else []
        }
