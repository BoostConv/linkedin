"""Seed the database with initial pillars, templates, and writing rules."""
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base
from app.models.pillar import Pillar
from app.models.template import PostTemplate
from app.models.writing_rule import WritingRule

settings = get_settings()


PILLARS = [
    {
        "name": "Landing pages & post-clic",
        "description": "Tout ce qui se passe après le clic : message match, UX de conversion, structure de LP, erreurs fréquentes, parcours utilisateur. Le coeur de l'expertise Boost Conversion.",
        "weight": 3.0,
        "display_order": 1,
        "preferred_templates": json.dumps(["gafam", "etude", "big_statement", "fable"]),
    },
    {
        "name": "Tests A/B & résultats clients",
        "description": "Études de cas chiffrées : avant/après, screenshots, ce qui a marché et pourquoi.",
        "weight": 2.5,
        "display_order": 2,
        "preferred_templates": json.dumps(["big_fact", "post_histoire", "etude"]),
    },
    {
        "name": "Créa & statics IA",
        "description": "La révolution des assets publicitaires générés par IA, testing créatif, ce que ça change pour les marques DTC.",
        "weight": 2.0,
        "display_order": 3,
        "preferred_templates": json.dumps(["gafam", "big_statement", "etude"]),
    },
    {
        "name": "Opinions tranchées e-commerce",
        "description": "Prises de position clivantes sur le marketing digital, les tendances, les pratiques qui marchent (ou pas).",
        "weight": 2.0,
        "display_order": 4,
        "preferred_templates": json.dumps(["big_statement", "fable", "vanne_rebours"]),
    },
    {
        "name": "CRO & conversion (frameworks)",
        "description": "Méthodologies : ICE scoring, Master Persona, quiz funnels, segmentation. Contenu éducatif qui positionne comme expert de référence.",
        "weight": 1.5,
        "display_order": 5,
        "preferred_templates": json.dumps(["curation", "etude", "gafam"]),
    },
    {
        "name": "Coulisses & entrepreneuriat",
        "description": "Vie d'agence, décisions business, recrutement, erreurs, chiffres de Boost Conversion. Le 20% perso qui humanise le profil.",
        "weight": 1.5,
        "display_order": 6,
        "preferred_templates": json.dumps(["post_histoire", "big_fact", "investissements", "heros", "portrait"]),
    },
]


TEMPLATES = [
    {
        "name": "L'effet Google (GAFAM)",
        "slug": "gafam",
        "description": "Post basé sur une pratique ou un fait d'un GAFAM pour capturer la curiosité et en tirer une leçon entrepreneuriale.",
        "structure": {
            "steps": [
                {"name": "intro", "description": "Phrase d'accroche catchy avec un fait ou une stat sur un GAFAM / figure tech"},
                {"name": "contexte", "description": "Description du contexte ou de la stratégie adoptée"},
                {"name": "lecon", "description": "Leçon ou principe entrepreneurial tiré de cette pratique"},
                {"name": "conclusion", "description": "Invitation à l'action ou conclusion polémique/touchante"},
            ]
        },
        "prompt_instructions": "Commence par un fait choc et vérifiable sur un GAFAM ou une figure tech (Google, Amazon, Apple, Meta, Elon Musk, Jeff Bezos...). Développe le contexte de manière factuelle. Tire une leçon applicable aux fondateurs e-commerce / CMO. Termine par une conclusion qui fait réagir (polémique douce ou touchante). Suggère une photo de la figure tech en accompagnement.",
        "when_to_use": "Pour rattacher un concept CRO/post-clic à une pratique d'un géant tech et capter la curiosité.",
        "display_order": 1,
    },
    {
        "name": "Le héros",
        "slug": "heros",
        "description": "Portrait d'une personne inspirante avec données chiffrées, obstacles et progression.",
        "structure": {
            "steps": [
                {"name": "accroche", "description": "Phrase choc sur la personne avec une donnée chiffrée"},
                {"name": "nom", "description": "Donner le nom de la personne"},
                {"name": "obstacles", "description": "Raconter les obstacles franchis"},
                {"name": "progression", "description": "Où elle a progressé jusqu'à aujourd'hui"},
                {"name": "cta", "description": "Demander un like / soutien"},
            ]
        },
        "prompt_instructions": "Commence par une stat impressionnante sur la personne sans la nommer. Puis révèle le nom. Raconte chronologiquement les obstacles puis la progression. Photo portrait suggérée. CTA pour soutenir.",
        "when_to_use": "Pour mettre en avant un client, un entrepreneur inspirant, ou une interview.",
        "display_order": 2,
    },
    {
        "name": "Le post histoire",
        "slug": "post_histoire",
        "description": "Storytelling personnel pour appuyer un point. Commencer par une anecdote avec tension narrative.",
        "structure": {
            "steps": [
                {"name": "anecdote", "description": "Hier j'ai... / La semaine dernière... - situation avec tension narrative"},
                {"name": "point", "description": "Le point qui a marqué ou la leçon"},
                {"name": "developpement", "description": "Développer l'idée (optionnel: en 3 points)"},
                {"name": "conclusion", "description": "Conclusion"},
            ]
        },
        "prompt_instructions": "Commence in medias res avec une anecdote datée et située. Crée de la tension narrative dès la première phrase. Le point principal doit être lié à l'expertise CRO/post-clic/e-commerce. Développe avec des détails spécifiques (noms d'outils, chiffres, dates). Conclure sans résumer.",
        "when_to_use": "Pour appuyer un point CRO avec une expérience vécue chez un client ou dans la vie de l'agence.",
        "display_order": 3,
    },
    {
        "name": "Les investissements en vous",
        "slug": "investissements",
        "description": "Liste des meilleurs investissements personnels ou professionnels.",
        "structure": {
            "steps": [
                {"name": "intro", "description": "Voici les meilleurs achats/décisions que j'ai faits..."},
                {"name": "liste", "description": "5 items avec quelques mots de développement chacun"},
                {"name": "conclusion", "description": "Conclusion légère ou humoristique"},
            ]
        },
        "prompt_instructions": "Liste 5 investissements personnels ou pro avec un ton décontracté. Chaque item doit avoir 1-2 phrases de développement (pas un simple mot). Varier entre pro (formations, outils, recrutement) et perso (bien-être, routines). L'humour est bienvenu. Ne pas faire de liste à puces formatée IA.",
        "when_to_use": "Personal branding, montrer ses valeurs et son mode de vie. Bon pour humaniser le profil.",
        "display_order": 4,
    },
    {
        "name": "Le post portrait",
        "slug": "portrait",
        "description": "Portrait d'un entrepreneur avec parcours, pivots, résultats et leçon.",
        "structure": {
            "steps": [
                {"name": "accroche", "description": "Accroche percutante avec chiffres ou accomplissement"},
                {"name": "origines", "description": "Débuts et premiers obstacles"},
                {"name": "pivots", "description": "Moments clés et décisions qui ont tout changé"},
                {"name": "resultats", "description": "Résultats obtenus (chiffres impressionnants)"},
                {"name": "lecon", "description": "Leçon ou morale tirée du parcours"},
            ]
        },
        "prompt_instructions": "Commence avec les chiffres qui impressionnent (CA, valorisation, nombre d'utilisateurs). Puis remonte aux origines humbles. Identifie 1-2 pivots clés. Termine par une leçon applicable à l'audience DTC/e-com. Photo de la personne suggérée. Tagger la personne si pertinent.",
        "when_to_use": "Pour illustrer une stratégie via le parcours d'un entrepreneur. Bon pour les posts portrait/curation.",
        "display_order": 5,
    },
    {
        "name": "Curation de contenu",
        "slug": "curation",
        "description": "Prendre un contenu tiers et en tirer N apprentissages.",
        "structure": {
            "steps": [
                {"name": "source", "description": "J'ai lu/écouté X de Y, voici les N leçons"},
                {"name": "lecons", "description": "Liste numérotée des apprentissages"},
                {"name": "tag", "description": "Taguer l'auteur original"},
            ]
        },
        "prompt_instructions": "Nommer la source précise (podcast, newsletter, article, conférence). Lister 3-5 leçons en les reliant à l'expertise CRO/e-commerce. Chaque leçon doit avoir 1-2 phrases de contexte (pas juste un titre). Taguer l'auteur. Variante possible: prendre un seul propos et le développer.",
        "when_to_use": "Pour se positionner comme curateur dans l'écosystème CRO/e-commerce. Bon quand on a lu/vu quelque chose d'inspirant.",
        "display_order": 6,
    },
    {
        "name": "Big statement",
        "slug": "big_statement",
        "description": "Arriver avec une provocation forte puis argumenter.",
        "structure": {
            "steps": [
                {"name": "provocation", "description": "Affirmation provocatrice en phrase 1"},
                {"name": "argument", "description": "Développement de l'argument principal"},
                {"name": "critique", "description": "Critique des idées opposées"},
                {"name": "nuance", "description": "Reconnaissance des limites ou nuances"},
                {"name": "conclusion", "description": "Conclusion forte + appel au débat"},
            ]
        },
        "prompt_instructions": "La première phrase doit être clivante et donner envie de lire la suite. Argumenter avec des faits, des observations terrain, des données clients. Montrer qu'on a réfléchi aux contre-arguments. Terminer en ouvrant le débat (question ouverte). Le ton doit être celui de quelqu'un qui assume son opinion mais qui est ouvert à la discussion.",
        "when_to_use": "Pour les sujets clivants dans le CRO/e-commerce/marketing digital. Quand on a une opinion forte à défendre.",
        "display_order": 7,
    },
    {
        "name": "La vanne à rebours",
        "slug": "vanne_rebours",
        "description": "Phrase incroyable en accroche puis chute humoristique.",
        "structure": {
            "steps": [
                {"name": "accroche", "description": "Phrase incroyable qui attire le lecteur"},
                {"name": "chute", "description": "Chute royale immédiate et humoristique"},
            ]
        },
        "prompt_instructions": "Post court. L'accroche doit sembler sérieuse et impressionnante. La chute doit être drôle et inattendue. L'humour doit être en lien avec le monde CRO/e-commerce/entrepreneuriat si possible. Ne pas forcer la blague. Format très court (5-10 lignes max).",
        "when_to_use": "Pour casser le rythme et montrer le côté humain. Utiliser avec parcimonie (1x par mois max).",
        "display_order": 8,
    },
    {
        "name": "Le post étude",
        "slug": "etude",
        "description": "Donner une étude surprenante dès la phrase 1 pour appuyer un point.",
        "structure": {
            "steps": [
                {"name": "etude", "description": "Introduction de l'étude/recherche avec stat surprenante"},
                {"name": "resultats", "description": "Développement des résultats ou conclusions principales"},
                {"name": "comportements", "description": "Liste des comportements ou traits observés"},
                {"name": "lecon", "description": "Conclusion ou leçons tirées"},
                {"name": "question", "description": "Invitation à l'engagement"},
            ]
        },
        "prompt_instructions": "Commencer par la stat la plus surprenante de l'étude. Citer la source (année, institution si possible). Développer les résultats avec des chiffres précis. Relier les conclusions à l'univers CRO/e-commerce. Terminer par une question ouverte qui invite au débat. L'étude doit être réelle et vérifiable.",
        "when_to_use": "Pour appuyer un point avec de la data scientifique. Quand on a trouvé une étude qui challenge les idées reçues.",
        "display_order": 9,
    },
    {
        "name": "La fable (à prénom)",
        "slug": "fable",
        "description": "Anecdote réelle avec prénom fictif pour illustrer un comportement.",
        "structure": {
            "steps": [
                {"name": "situation", "description": "Hier/récemment, j'ai rencontré quelqu'un... Appelons-le [prénom]"},
                {"name": "comportements", "description": "Décrire les comportements spécifiques du personnage"},
                {"name": "morale", "description": "Leçon ou morale tirée du comportement"},
                {"name": "conclusion", "description": "Invitation à la réflexion"},
            ]
        },
        "prompt_instructions": "Donner un prénom fictif mémorable au personnage. Décrire des comportements très précis et visuels (le lecteur doit pouvoir s'imaginer la scène). Le prénom doit être répété plusieurs fois pour que les commentateurs le reprennent. La morale doit être liée au business/CRO/e-commerce. Ton entre l'amusement et la leçon.",
        "when_to_use": "Pour illustrer un bon ou mauvais comportement client/entrepreneur/marketeur.",
        "display_order": 10,
    },
    {
        "name": "Big fact",
        "slug": "big_fact",
        "description": "Fait personnel chiffré surprenant en ouverture puis dérouler la pelote.",
        "structure": {
            "steps": [
                {"name": "fait", "description": "Fait marquant ou chiffré surprenant en phrase 1"},
                {"name": "contexte", "description": "Contexte et histoire derrière le fait"},
                {"name": "lecon", "description": "Leçon ou morale tirée de l'expérience"},
                {"name": "cta", "description": "Appel à l'action ou réflexion finale"},
            ]
        },
        "prompt_instructions": "Le fait d'ouverture doit être chiffré et surprenant (un salaire, un nombre de clients, un chiffre d'affaires, un refus). Raconter l'histoire derrière avec des détails concrets. La leçon doit être applicable et pas moralisatrice. Terminer en ouvrant (question, invitation à partager son expérience).",
        "when_to_use": "Pour les milestones, célébrations, et leçons personnelles. Quand on a un chiffre ou un fait impressionnant à partager.",
        "display_order": 11,
    },
]


WRITING_RULES = [
    # Tone rules
    {
        "category": "tone",
        "name": "Entrepreneur qui pense à voix haute",
        "content": "Le ton est celui d'un entrepreneur qui pense à voix haute devant son audience. Pas une conclusion polie. Le lecteur doit avoir l'impression de regarder par-dessus l'épaule de Sébastien.",
        "severity": "error",
        "display_order": 1,
    },
    {
        "category": "tone",
        "name": "Conversation entre potes entrepreneurs",
        "content": "Écrire comme quelqu'un qui parle à un pote entrepreneur autour d'un café. Des vraies phrases, avec du souffle, des digressions, des parenthèses.",
        "example_good": "On a lancé ce test en pensant que ça allait être un quick win facile et en fait c'est la version la plus moche visuellement qui a gagné, ce qui nous a forcés à revoir pas mal de nos certitudes.",
        "example_bad": "On a lancé ce test. Le résultat nous a surpris. La version la plus moche a gagné. On a tout remis en question.",
        "severity": "error",
        "display_order": 2,
    },
    {
        "category": "tone",
        "name": "Pas de tutoiement",
        "content": "Pas de tutoiement dans les posts (audience pro). Vouvoiement possible mais pas systématique. Privilégier 'on' ou formulations impersonnelles.",
        "severity": "error",
        "display_order": 3,
    },
    # Anti-AI rules
    {
        "category": "anti_ai",
        "name": "Structure binaire interdite",
        "content": "INTERDICTION de 'Ce n'est pas X. C'est Y.' et toutes ses variantes. Marqueur IA n°1. Tolérance zéro.",
        "example_bad": "Ce n'est pas une question de budget. C'est une question de stratégie.",
        "severity": "error",
        "display_order": 10,
    },
    {
        "category": "anti_ai",
        "name": "Tirets cadratins interdits",
        "content": "0 tiret cadratin (—) par post. Utiliser des points, des virgules, des parenthèses, ou reformuler.",
        "severity": "error",
        "display_order": 11,
    },
    {
        "category": "anti_ai",
        "name": "Max 3 phrases courtes consécutives",
        "content": "Jamais plus de 3 phrases courtes (<8 mots) à la suite. Fusionner ou développer. Ce pattern est le marqueur IA/copywriter LinkedIn le plus visible.",
        "example_bad": "Les statics IA. C'est notre pari. Les résultats sont là. Le doute aussi.",
        "severity": "error",
        "display_order": 12,
    },
    {
        "category": "anti_ai",
        "name": "Pas de listes à puces formatées",
        "content": "Pas de listes à puces avec un mot en gras suivi d'une explication. Intégrer dans le flux du texte.",
        "example_good": "on a trouvé trois trucs : premier truc, deuxième truc, et troisième truc qui nous a le plus surpris",
        "severity": "error",
        "display_order": 13,
    },
    {
        "category": "anti_ai",
        "name": "Fins dramatiques limitées",
        "content": "Max 1 fin de phrase dramatique isolée sur une ligne par post ('Et ça change tout.' / 'C'est là que tout bascule.').",
        "severity": "warning",
        "display_order": 14,
    },
    # Banned words
    {
        "category": "banned_words",
        "name": "Expressions bannies",
        "content": "dans un monde où...|la clé c'est...|en fin de compte|tout simplement|véritablement|fondamentalement|indéniablement|il est essentiel de|game-changer|ce qui fait la différence|parlons-en|et voici pourquoi|spoiler alert|et ça change tout|et c'est là que tout change|personne n'en parle|la vraie question c'est|le vrai sujet c'est|concrètement|force est de constater|il s'avère que|autrement dit",
        "severity": "error",
        "display_order": 20,
    },
    {
        "category": "banned_words",
        "name": "Mots en -ment comme béquille",
        "content": "Éviter les mots en '-ment' utilisés comme béquille rhétorique : clairement, absolument, littéralement, véritablement, fondamentalement.",
        "severity": "warning",
        "display_order": 21,
    },
    {
        "category": "banned_words",
        "name": "Transitions pompeuses",
        "content": "Interdiction de : 'Cela étant dit', 'Force est de constater', 'Il convient de noter'.",
        "severity": "error",
        "display_order": 22,
    },
    # Variation rules
    {
        "category": "tone",
        "name": "Varier la longueur des phrases",
        "content": "Alterner entre des phrases courtes (5 mots) et des phrases plus longues (25 mots) qui développent une idée. Le mélange des deux crée un rythme naturel.",
        "severity": "error",
        "display_order": 4,
    },
]


def seed_database():
    engine = create_engine(settings.database_url_sync)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Seed pillars
        existing_pillars = session.query(Pillar).count()
        if existing_pillars == 0:
            for p in PILLARS:
                session.add(Pillar(**p))
            print(f"Seeded {len(PILLARS)} pillars")

        # Seed templates
        existing_templates = session.query(PostTemplate).count()
        if existing_templates == 0:
            for t in TEMPLATES:
                session.add(PostTemplate(**t))
            print(f"Seeded {len(TEMPLATES)} templates")

        # Seed writing rules
        existing_rules = session.query(WritingRule).count()
        if existing_rules == 0:
            for r in WRITING_RULES:
                session.add(WritingRule(**r))
            print(f"Seeded {len(WRITING_RULES)} writing rules")

        session.commit()
        print("Seed complete!")


if __name__ == "__main__":
    seed_database()
