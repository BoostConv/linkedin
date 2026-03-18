"""Anti-AI validator for LinkedIn posts.

Checks posts against all anti-AI rules before publication.
Returns a score (0-100, higher = more human) and a list of issues.
"""
import re


BANNED_EXPRESSIONS = [
    "dans un monde où",
    "la clé, c'est",
    "la clé c'est",
    "en fin de compte",
    "tout simplement",
    "véritablement",
    "fondamentalement",
    "indéniablement",
    "il est essentiel de",
    "game-changer",
    "game changer",
    "ce qui fait la différence",
    "parlons-en",
    "et voici pourquoi",
    "spoiler alert",
    "et ça change tout",
    "et c'est là que tout change",
    "personne n'en parle",
    "la vraie question c'est",
    "le vrai sujet c'est",
    "force est de constater",
    "il s'avère que",
    "autrement dit",
    "cela étant dit",
    "il convient de noter",
]

BANNED_MENT_WORDS = [
    "clairement",
    "absolument",
    "littéralement",
    "véritablement",
    "fondamentalement",
    "indéniablement",
    "concrètement",
]

DRAMATIC_ENDINGS = [
    r"et ça change tout\.\s*$",
    r"c'est là que tout bascule\.\s*$",
    r"personne n'en parle\.\s*$",
    r"et c'est là que tout change\.\s*$",
    r"ça change la donne\.\s*$",
]


def check_binary_structure(text: str) -> list[str]:
    """Check for 'Ce n'est pas X. C'est Y.' patterns."""
    issues = []
    patterns = [
        r"[Cc]e n'est pas .+?\. [Cc]'est .+?\.",
        r"[Cc]'est pas .+?\. [Cc]'est .+?\.",
        r"[Ll]a différence,? c'est pas .+?\. [Cc]'est .+?\.",
        r"[Ll]e problème,? c'est pas .+?\. [Cc]'est .+?\.",
        r"[Ll]e sujet,? c'est pas .+?\. [Cc]'est .+?\.",
        r"[Ii]l ne s'agit pas de .+?,? mais de .+?\.",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            issues.append({
                "rule": "Structure binaire interdite",
                "severity": "error",
                "detail": f"Structure 'pas X / c'est Y' détectée: '{match[:80]}...'",
            })
    return issues


def check_em_dashes(text: str) -> list[str]:
    """Check for em dashes (—)."""
    issues = []
    count = text.count("—")
    if count > 0:
        issues.append({
            "rule": "Tirets cadratins interdits",
            "severity": "error",
            "detail": f"{count} tiret(s) cadratin(s) détecté(s). Utiliser des virgules, points ou parenthèses.",
        })
    return issues


def check_consecutive_short_sentences(text: str) -> list[str]:
    """Check for more than 3 consecutive short sentences (<8 words)."""
    issues = []
    # Split into lines/sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    consecutive_short = 0
    for sentence in sentences:
        word_count = len(sentence.split())
        if word_count < 8:
            consecutive_short += 1
            if consecutive_short > 3:
                issues.append({
                    "rule": "Trop de phrases courtes consécutives",
                    "severity": "error",
                    "detail": f"Plus de 3 phrases courtes (<8 mots) à la suite détectées. Fusionner ou développer.",
                })
                break
        else:
            consecutive_short = 0

    return issues


def check_banned_expressions(text: str) -> list[str]:
    """Check for banned words and expressions."""
    issues = []
    text_lower = text.lower()

    for expr in BANNED_EXPRESSIONS:
        if expr.lower() in text_lower:
            issues.append({
                "rule": "Expression bannie",
                "severity": "error",
                "detail": f"Expression bannie détectée: '{expr}'",
            })

    for word in BANNED_MENT_WORDS:
        # Match as whole word (not part of another word)
        if re.search(rf'\b{re.escape(word)}\b', text_lower):
            issues.append({
                "rule": "Mot en -ment comme béquille",
                "severity": "warning",
                "detail": f"Mot béquille détecté: '{word}'",
            })

    return issues


def check_dramatic_endings(text: str) -> list[str]:
    """Check for dramatic one-line endings."""
    issues = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    dramatic_count = 0

    for line in lines:
        for pattern in DRAMATIC_ENDINGS:
            if re.search(pattern, line, re.IGNORECASE):
                dramatic_count += 1

    if dramatic_count > 1:
        issues.append({
            "rule": "Fins dramatiques excessives",
            "severity": "warning",
            "detail": f"{dramatic_count} fins de phrase dramatiques isolées détectées (max 1 par post).",
        })

    return issues


def check_bullet_lists(text: str) -> list[str]:
    """Check for formatted bullet lists with bold words."""
    issues = []
    # Pattern: line starting with bullet/dash/number + bold word + explanation
    pattern = r'^[\s]*[-•*]\s*\*\*\w+\*\*\s*[:—-]'
    matches = re.findall(pattern, text, re.MULTILINE)
    if matches:
        issues.append({
            "rule": "Liste à puces formatée IA",
            "severity": "error",
            "detail": "Liste à puces avec mot en gras + explication détectée. Intégrer dans le flux du texte.",
        })
    return issues


def check_tutoiement(text: str) -> list[str]:
    """Check for informal 'tu' usage."""
    issues = []
    # Common tutoiement patterns (avoiding false positives)
    tu_patterns = [
        r'\btu\s+(?:es|as|fais|veux|peux|dois|vas|sais|penses|crois|vois)\b',
        r'\bsi tu\b',
        r'\bquand tu\b',
        r'\bet toi\b',
        r'\bchez toi\b',
        r'\bpour toi\b',
    ]
    for pattern in tu_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            issues.append({
                "rule": "Tutoiement détecté",
                "severity": "error",
                "detail": "Le post contient du tutoiement. Utiliser 'vous', 'on', ou des formulations impersonnelles.",
            })
            break
    return issues


def check_sentence_length_variation(text: str) -> list[str]:
    """Check that sentence lengths are varied (not all the same)."""
    issues = []
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip().split()) > 1]

    if len(sentences) < 4:
        return issues

    lengths = [len(s.split()) for s in sentences]
    avg = sum(lengths) / len(lengths)

    # Check if all sentences are within 30% of the average
    uniform_count = sum(1 for l in lengths if abs(l - avg) < avg * 0.3)
    if uniform_count > len(lengths) * 0.8:
        issues.append({
            "rule": "Manque de variation de longueur",
            "severity": "warning",
            "detail": "Les phrases ont toutes une longueur similaire. Varier entre phrases courtes et longues.",
        })

    return issues


def check_summary_conclusion(text: str) -> list[str]:
    """Check if the conclusion just summarizes the post."""
    issues = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 5:
        return issues

    last_lines = " ".join(lines[-3:]).lower()

    summary_markers = [
        "en résumé",
        "pour résumer",
        "en conclusion",
        "les 3 points",
        "les trois points",
        "retenez ces",
        "à retenir",
    ]

    for marker in summary_markers:
        if marker in last_lines:
            issues.append({
                "rule": "Conclusion qui résume",
                "severity": "warning",
                "detail": f"La conclusion semble résumer le post ('{marker}'). Ouvrir plutôt que fermer.",
            })
            break

    return issues


def validate_post(text: str) -> dict:
    """Run all anti-AI checks on a post.

    Returns:
        dict with keys: score (0-100), issues (list of dicts), passed (bool)
    """
    all_issues = []

    all_issues.extend(check_binary_structure(text))
    all_issues.extend(check_em_dashes(text))
    all_issues.extend(check_consecutive_short_sentences(text))
    all_issues.extend(check_banned_expressions(text))
    all_issues.extend(check_dramatic_endings(text))
    all_issues.extend(check_bullet_lists(text))
    all_issues.extend(check_tutoiement(text))
    all_issues.extend(check_sentence_length_variation(text))
    all_issues.extend(check_summary_conclusion(text))

    # Calculate score
    error_count = sum(1 for i in all_issues if i["severity"] == "error")
    warning_count = sum(1 for i in all_issues if i["severity"] == "warning")

    # Start at 100, deduct for issues
    score = max(0, 100 - (error_count * 20) - (warning_count * 5))

    return {
        "score": score,
        "issues": all_issues,
        "passed": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
    }
