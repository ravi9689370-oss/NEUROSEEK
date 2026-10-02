"""
NCERT Knowledge Base — Class 1-12
Offline knowledge base jo NCERT curriculum cover karta hai
Self-learning system jo sawal se seekhta hai
"""

import json
import os
import re
from typing import Optional, List, Dict
from datetime import datetime


class NCERTKnowledgeBase:
    """
    NCERT Knowledge Base jo:
    1. Class 1-12 ki sari subjects cover karta hai
    2. Har chapter ke concepts store karta hai
    3. Self-learning karta hai sawal se
    4. Offline kaam karta hai
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "ncert_data.json")
        self.knowledge = self._load_knowledge()
        self.learning_log = []

    def _load_knowledge(self) -> dict:
        """NCERT knowledge load karta hai"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return self._create_default_knowledge()

    def _create_default_knowledge(self) -> dict:
        """Default NCERT knowledge create karta hai"""
        return {
            "mathematics": {
                "class_1": {
                    "numbers": "Numbers 1-100 tak count karna, basic addition aur subtraction",
                    "shapes": "Basic shapes - circle, square, triangle, rectangle",
                    "patterns": "Number patterns aur color patterns"
                },
                "class_2": {
                    "numbers": "Numbers 1-1000, place value, comparing numbers",
                    "addition": "2-digit aur 3-digit addition with carry",
                    "subtraction": "2-digit aur 3-digit subtraction with borrowing",
                    "multiplication": "Multiplication tables 1-10"
                },
                "class_3": {
                    "numbers": "4-digit numbers, place value, rounding",
                    "multiplication": "Multiplication tables 1-12",
                    "division": "Basic division, division facts",
                    "fractions": "Introduction to fractions - half, quarter, third"
                },
                "class_4": {
                    "numbers": "Large numbers, Roman numerals",
                    "factors": "Factors and multiples, prime numbers",
                    "fractions": "Equivalent fractions, comparing fractions",
                    "decimals": "Introduction to decimals"
                },
                "class_5": {
                    "numbers": "Large numbers up to 10 lakhs",
                    "fractions": "Addition and subtraction of fractions",
                    "decimals": "Decimal operations",
                    "geometry": "Angles, triangles, quadrilaterals",
                    "measurement": "Length, weight, capacity, time"
                },
                "class_6": {
                    "numbers": "Whole numbers, integers, playing with numbers",
                    "fractions": "Fraction operations",
                    "decimals": "Decimal operations",
                    "algebra": "Introduction to algebra, variables",
                    "geometry": "Basic geometrical ideas, symmetry",
                    "mensuration": "Perimeter and area"
                },
                "class_7": {
                    "integers": "Integer operations, properties",
                    "fractions": "Fraction and decimal operations",
                    "algebra": "Simple equations, algebraic expressions",
                    "geometry": "Lines, angles, triangles, congruence",
                    "mensuration": "Area and perimeter of plane figures",
                    "data": "Data handling, mean, median, mode"
                },
                "class_8": {
                    "rational": "Rational numbers and operations",
                    "algebra": "Linear equations in one variable",
                    "geometry": "Quadrilaterals, polygons",
                    "mensuration": "Surface area and volume",
                    "exponents": "Exponents and powers",
                    "graphs": "Introduction to graphs"
                },
                "class_9": {
                    "numbers": "Number systems, real numbers",
                    "algebra": "Polynomials, linear equations in two variables",
                    "geometry": "Coordinate geometry, Euclid's geometry",
                    "mensuration": "Surface areas and volumes",
                    "statistics": "Statistics and probability"
                },
                "class_10": {
                    "numbers": "Real numbers, Euclid's division lemma",
                    "algebra": "Polynomials, pair of linear equations, quadratic equations",
                    "geometry": "Triangles, circles, constructions",
                    "trigonometry": "Introduction to trigonometry",
                    "mensuration": "Areas related to circles, surface areas and volumes",
                    "statistics": "Statistics and probability"
                },
                "class_11": {
                    "sets": "Sets and their representations",
                    "algebra": "Relations and functions, complex numbers, linear inequalities",
                    "geometry": "Straight lines, conic sections",
                    "trigonometry": "Trigonometric functions",
                    "calculus": "Limits and derivatives",
                    "statistics": "Statistics and probability"
                },
                "class_12": {
                    "relations": "Relations and functions, inverse trigonometric functions",
                    "algebra": "Matrices, determinants",
                    "calculus": "Continuity and differentiability, applications of derivatives, integrals",
                    "vectors": "Vector algebra, three dimensional geometry",
                    "probability": "Probability and distributions"
                }
            },
            "science": {
                "class_1": {
                    "plants": "Plants around us, parts of plants",
                    "animals": "Animals around us, habitats",
                    "food": "Food we eat, sources of food",
                    "water": "Water around us, uses of water",
                    "weather": "Weather and seasons"
                },
                "class_2": {
                    "plants": "Plants - herbs, shrubs, trees",
                    "animals": "Animals - domestic and wild",
                    "food": "Food and its sources",
                    "housing": "Types of houses",
                    "clothing": "Types of clothes",
                    "festivals": "Festivals we celebrate"
                },
                "class_3": {
                    "plants": "Plant life, photosynthesis",
                    "animals": "Animal life, adaptations",
                    "matter": "States of matter",
                    "force": "Force and motion",
                    "energy": "Forms of energy"
                },
                "class_4": {
                    "plants": "Plant reproduction, dispersal of seeds",
                    "animals": "Animal reproduction, life cycles",
                    "matter": "Properties of matter",
                    "force": "Force, work and energy",
                    "light": "Light, shadows and reflections"
                },
                "class_5": {
                    "plants": "Plant kingdom, classification",
                    "animals": "Animal kingdom, adaptations",
                    "matter": "Atoms and molecules",
                    "force": "Gravitation, pressure",
                    "energy": "Work, power and energy"
                },
                "class_6": {
                    "food": "Food and its components",
                    "fibers": "Fiber to fabric",
                    "matter": "Sorting materials, separation of substances",
                    "changes": "Changes around us",
                    "body": "Body movements, organ systems",
                    "motion": "Motion and measurement of distances",
                    "light": "Light, shadows and reflections",
                    "electricity": "Electric circuits, magnets",
                    "environment": "Water, air around us"
                },
                "class_7": {
                    "nutrition": "Nutrition in plants and animals",
                    "heat": "Heat and temperature",
                    "acids": "Acids, bases and salts",
                    "weather": "Weather, climate and adaptations",
                    "soil": "Soil and its types",
                    "reproduction": "Reproduction in plants and animals",
                    "motion": "Motion and time",
                    "electricity": "Electric current and its effects"
                },
                "class_8": {
                    "crop": "Crop production and management",
                    "microorganisms": "Microorganisms - useful and harmful",
                    "coal": "Coal and petroleum",
                    "conservation": "Conservation of plants and animals",
                    "cell": "Cell - structure and functions",
                    "reproduction": "Reproduction in animals",
                    "force": "Force and pressure",
                    "friction": "Friction",
                    "sound": "Sound",
                    "electricity": "Chemical effects of electric current",
                    "light": "Light"
                },
                "class_9": {
                    "matter": "Matter in our surroundings, is matter around us pure",
                    "atoms": "Atoms and molecules, structure of atom",
                    "cell": "The fundamental unit of life, tissues",
                    "diversity": "Diversity in living organisms",
                    "motion": "Motion, force and laws of motion",
                    "gravitation": "Gravitation",
                    "energy": "Work and energy, sound"
                },
                "class_10": {
                    "chemical": "Chemical reactions and equations",
                    "acids": "Acids, bases and salts",
                    "metals": "Metals and non-metals",
                    "carbon": "Carbon and its compounds",
                    "life": "Life processes, control and coordination",
                    "reproduction": "How do organisms reproduce",
                    "heredity": "Heredity and evolution",
                    "light": "Light - reflection and refraction",
                    "electricity": "Electricity, magnetic effects of electric current",
                    "environment": "Our environment, management of natural resources"
                },
                "class_11": {
                    "world": "The living world, biological classification",
                    "plants": "Plant kingdom, morphology of flowering plants",
                    "animals": "Animal kingdom, structural organisation in animals",
                    "cell": "Cell, biomolecules, cell cycle",
                    "transport": "Transport in plants, mineral nutrition",
                    "photosynthesis": "Photosynthesis in higher plants",
                    "respiration": "Respiration in plants",
                    "growth": "Plant growth and development",
                    "digestion": "Digestion and absorption",
                    "breathing": "Breathing and exchange of gases",
                    "circulation": "Body fluids and circulation",
                    "excretion": "Excretory products and their elimination",
                    "locomotion": "Locomotion and movement",
                    "neural": "Neural control and coordination",
                    "chemical": "Chemical coordination and integration"
                },
                "class_12": {
                    "reproduction": "Reproduction in organisms, sexual reproduction in flowering plants",
                    "genetics": "Principles of inheritance and variation, molecular basis of inheritance",
                    "evolution": "Evolution",
                    "health": "Human health and disease, strategies for enhancement in food production",
                    "microbes": "Microbes in human welfare",
                    "biotechnology": "Biotechnology - principles and processes, biotechnology and its applications",
                    "ecology": "Organisms and populations, ecosystem, biodiversity and conservation"
                }
            },
            "social_science": {
                "class_6": {
                    "earth": "The earth in the solar system",
                    "globe": "Globe - latitudes and longitudes",
                    "motions": "Motions of the earth",
                    "maps": "Maps",
                    "major": "Major domains of the earth",
                    "history": "What, where, how and when",
                    "hunter": "From hunting-gathering to growing food",
                    "farming": "In the earliest cities"
                },
                "class_7": {
                    "environment": "Environment",
                    "earth": "Inside our earth",
                    "climate": "Our changing earth",
                    "water": "Water",
                    "history": "Tracing changes through a thousand years",
                    "kings": "New kings and kingdoms",
                    "delhi": "The Delhi Sultans"
                },
                "class_8": {
                    "resources": "Resources",
                    "land": "Land, soil, water, natural vegetation and wildlife resources",
                    "history": "How, when and where",
                    "establishment": "Establishment of company power",
                    "colonialism": "Colonialism and the city",
                    "tribals": "Tribals, dikus and the vision of a golden age"
                },
                "class_9": {
                    "french": "The French Revolution",
                    "socialism": "Socialism in Europe and the Russian Revolution",
                    "nazism": "Nazism and the rise of Hitler",
                    "india": "India - size and location, physical features of India",
                    "democracy": "What is democracy, why democracy",
                    "constitution": "Constitutional design"
                },
                "class_10": {
                    "nationalism": "The rise of nationalism in Europe",
                    "india": "Nationalism in India",
                    "global": "The making of a global world",
                    "industrialization": "The age of industrialization",
                    "resources": "Resources and development",
                    "agriculture": "Agriculture",
                    "federalism": "Federalism",
                    "gender": "Gender, religion and caste",
                    "political": "Political parties"
                },
                "class_11": {
                    "history": "The story of the first cities, an empire across three continents",
                    "sociology": "Introducing sociology, understanding society",
                    "political": "Indian constitution at work, political theory",
                    "geography": "Fundamentals of physical geography, India - physical environment"
                },
                "class_12": {
                    "history": "The story of the first cities, kings, farmers and towns",
                    "sociology": "Introducing Indian society, social institutions",
                    "political": "Contemporary world politics, politics in India since independence",
                    "geography": "Fundamentals of human geography, India - people and economy",
                    "economics": "Introductory microeconomics, introductory macroeconomics"
                }
            },
            "english": {
                "class_1": {
                    "stories": "Simple stories with moral lessons",
                    "poems": "Simple poems and rhymes",
                    "grammar": "Basic grammar - nouns, verbs, adjectives"
                },
                "class_2": {
                    "stories": "Short stories with simple vocabulary",
                    "poems": "Poems with rhythm and rhyme",
                    "grammar": "Tenses, pronouns, prepositions"
                },
                "class_3": {
                    "stories": "Stories with characters and plot",
                    "poems": "Poems with imagery",
                    "grammar": "Sentence types, conjunctions"
                },
                "class_4": {
                    "stories": "Stories with moral values",
                    "poems": "Poems with figurative language",
                    "grammar": "Active and passive voice"
                },
                "class_5": {
                    "stories": "Stories with complex plots",
                    "poems": "Poems with literary devices",
                    "grammar": "Direct and indirect speech"
                },
                "class_6": {
                    "stories": "Stories with themes and messages",
                    "poems": "Poems with deeper meanings",
                    "grammar": "Clauses, phrases"
                },
                "class_7": {
                    "stories": "Stories with character development",
                    "poems": "Poems with various forms",
                    "grammar": "Transformation of sentences"
                },
                "class_8": {
                    "stories": "Stories with social themes",
                    "poems": "Poems with cultural significance",
                    "grammar": "Reported speech, modals"
                },
                "class_9": {
                    "stories": "Stories with literary merit",
                    "poems": "Poems with poetic devices",
                    "grammar": "Advanced grammar concepts"
                },
                "class_10": {
                    "stories": "Stories with complex themes",
                    "poems": "Poems with literary analysis",
                    "grammar": "Advanced writing skills"
                },
                "class_11": {
                    "prose": "Prose with literary analysis",
                    "poetry": "Poetry with critical appreciation",
                    "writing": "Advanced writing skills"
                },
                "class_12": {
                    "prose": "Prose with deep analysis",
                    "poetry": "Poetry with critical evaluation",
                    "writing": "Professional writing skills"
                }
            },
            "hindi": {
                "class_1": {
                    "varnmala": "Varnmala - vowels and consonants",
                    "shabd": "Simple words and sentences",
                    "kahani": "Simple stories"
                },
                "class_2": {
                    "shabd": "Word formation",
                    "vaky": "Sentence formation",
                    "kahani": "Short stories"
                },
                "class_3": {
                    "shabd": "Vocabulary building",
                    "vaky": "Complex sentences",
                    "kahani": "Stories with moral lessons"
                },
                "class_4": {
                    "shabd": "Advanced vocabulary",
                    "vaky": "Paragraph writing",
                    "kahani": "Stories with themes"
                },
                "class_5": {
                    "shabd": "Idioms and phrases",
                    "vaky": "Essay writing",
                    "kahani": "Stories with character development"
                },
                "class_6": {
                    "shabd": "Advanced vocabulary",
                    "vaky": "Letter writing",
                    "kahani": "Stories with social themes"
                },
                "class_7": {
                    "shabd": "Literary vocabulary",
                    "vaky": "Article writing",
                    "kahani": "Stories with literary merit"
                },
                "class_8": {
                    "shabd": "Advanced literary vocabulary",
                    "vaky": "Report writing",
                    "kahani": "Stories with complex themes"
                },
                "class_9": {
                    "shabd": "Classical vocabulary",
                    "vaky": "Advanced writing skills",
                    "kahani": "Stories with deep analysis"
                },
                "class_10": {
                    "shabd": "Advanced classical vocabulary",
                    "vaky": "Professional writing",
                    "kahani": "Stories with critical evaluation"
                },
                "class_11": {
                    "shabd": "Literary criticism vocabulary",
                    "vaky": "Advanced literary writing",
                    "kahani": "Stories with literary analysis"
                },
                "class_12": {
                    "shabd": "Advanced literary vocabulary",
                    "vaky": "Research writing",
                    "kahani": "Stories with deep literary analysis"
                }
            }
        }

    def search(self, query: str, class_level: str = None, subject: str = None) -> Optional[str]:
        """
        NCERT knowledge base mein search karta hai
        """
        query_lower = query.lower()

        # Subject detect karo
        if not subject:
            subject = self._detect_subject(query_lower)

        # Class level detect karo
        if not class_level:
            class_level = self._detect_class_level(query_lower)

        # Search in knowledge
        if subject and subject in self.knowledge:
            subject_data = self.knowledge[subject]

            # Specific class search
            if class_level and class_level in subject_data:
                class_data = subject_data[class_level]
                for chapter, content in class_data.items():
                    if any(word in content.lower() for word in query_lower.split()):
                        return f"📚 **NCERT {subject.title()} - {class_level.replace('_', ' ').title()}**\n\n**Chapter:** {chapter.replace('_', ' ').title()}\n\n**Content:** {content}\n\n---\n📡 **Source:** NCERT Knowledge Base\n🧠 **Domain:** {subject.title()}"

            # General subject search
            for class_key, class_data in subject_data.items():
                for chapter, content in class_data.items():
                    if any(word in content.lower() for word in query_lower.split()):
                        return f"📚 **NCERT {subject.title()} - {class_key.replace('_', ' ').title()}**\n\n**Chapter:** {chapter.replace('_', ' ').title()}\n\n**Content:** {content}\n\n---\n📡 **Source:** NCERT Knowledge Base\n🧠 **Domain:** {subject.title()}"

        return None

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

    def learn_from_query(self, query: str, response: str):
        """Sawal se seekhta hai aur memory mein save karta hai"""
        self.learning_log.append({
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

        # Learning log save karo
        log_path = os.path.join(os.path.dirname(__file__), "learning_log.json")
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(self.learning_log, f, ensure_ascii=False, indent=2)
        except:
            pass

    def get_learning_stats(self) -> dict:
        """Learning statistics deta hai"""
        return {
            "total_queries": len(self.learning_log),
            "recent_queries": self.learning_log[-10:] if self.learning_log else []
        }
