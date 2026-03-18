"""Tests for the anti-AI validator.

These tests import the validator checks directly to avoid full DB deps.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai.validator import (
    validate_post,
    check_binary_structure,
    check_em_dashes,
    check_banned_expressions,
    check_tutoiement,
    check_bullet_lists,
    check_sentence_length_variation,
    check_summary_conclusion,
    check_dramatic_endings,
    check_consecutive_short_sentences,
)


class TestBinaryStructure:
    def test_detects_ce_nest_pas(self):
        issues = check_binary_structure("Ce n'est pas un problème de trafic. C'est un problème de conversion.")
        assert len(issues) > 0

    def test_clean_text(self):
        issues = check_binary_structure("Le CRO est sous-estimé par 90% des marques DTC.")
        assert len(issues) == 0


class TestEmDashes:
    def test_detects_em_dash(self):
        issues = check_em_dashes("Le CRO — contrairement à ce qu'on pense — est crucial.")
        assert len(issues) == 1
        assert "2" in issues[0]["detail"]

    def test_clean_text(self):
        issues = check_em_dashes("Le CRO, contrairement à ce qu'on pense, est crucial.")
        assert len(issues) == 0


class TestBannedExpressions:
    def test_detects_dans_un_monde_ou(self):
        issues = check_banned_expressions("Dans un monde où tout va vite.")
        found = [i for i in issues if "Expression bannie" in i["rule"]]
        assert len(found) > 0

    def test_detects_force_est_de_constater(self):
        issues = check_banned_expressions("Force est de constater que le marché évolue.")
        found = [i for i in issues if "Expression bannie" in i["rule"]]
        assert len(found) > 0

    def test_detects_ment_words(self):
        issues = check_banned_expressions("C'est clairement le meilleur choix.")
        found = [i for i in issues if "béquille" in i["rule"]]
        assert len(found) > 0

    def test_clean_text(self):
        issues = check_banned_expressions("J'ai analysé 47 landing pages.")
        assert len(issues) == 0


class TestTutoiement:
    def test_detects_tu(self):
        issues = check_tutoiement("Si tu veux des résultats, il faut investir.")
        assert len(issues) > 0

    def test_vouvoiement_ok(self):
        issues = check_tutoiement("Si vous voulez des résultats, il faut investir.")
        assert len(issues) == 0


class TestBulletLists:
    def test_detects_bold_bullets(self):
        text = "- **CTA** : visible au-dessus de la ligne de flottaison\n- **H1** : clarté en 3 secondes"
        issues = check_bullet_lists(text)
        assert len(issues) > 0

    def test_normal_text_ok(self):
        issues = check_bullet_lists("Le CTA doit être visible. Le H1 doit être clair.")
        assert len(issues) == 0


class TestDramaticEndings:
    def test_one_ok(self):
        issues = check_dramatic_endings("Et ça change tout.")
        assert len(issues) == 0  # 1 is allowed

    def test_multiple_flagged(self):
        text = "Et ça change tout.\nPersonne n'en parle."
        issues = check_dramatic_endings(text)
        assert len(issues) > 0


class TestConsecutiveShort:
    def test_many_short_flagged(self):
        text = "Court. Très court. Encore. Oui. Non. Stop."
        issues = check_consecutive_short_sentences(text)
        assert len(issues) > 0

    def test_mixed_ok(self):
        text = "Court. Une phrase beaucoup plus longue avec plein de détails sur le CRO et l'optimisation. Court."
        issues = check_consecutive_short_sentences(text)
        assert len(issues) == 0


class TestSummaryConclusion:
    def test_en_resume_flagged(self):
        text = "Ligne 1.\nLigne 2.\nLigne 3.\nLigne 4.\nLigne 5.\nEn résumé, voici les points."
        issues = check_summary_conclusion(text)
        assert len(issues) > 0

    def test_open_ending_ok(self):
        text = "Ligne 1.\nLigne 2.\nLigne 3.\nLigne 4.\nLigne 5.\nQu'en pensez-vous ?"
        issues = check_summary_conclusion(text)
        assert len(issues) == 0


class TestValidatePost:
    def test_clean_text_high_score(self):
        text = (
            "J'ai analysé 47 landing pages la semaine dernière.\n\n"
            "Le constat est sans appel. Les pages qui convertissent le mieux "
            "ne sont pas les plus belles.\n\n"
            "Elles sont les plus claires.\n\n"
            "Une proposition de valeur lisible en 3 secondes. "
            "Un CTA visible sans scroller. Zéro distraction.\n\n"
            "La plupart des marques DTC investissent dans le trafic "
            "mais négligent totalement ce qui se passe après le clic.\n\n"
            "Résultat : des taux de conversion à 1.2% quand on pourrait "
            "facilement atteindre 3-4% avec les bons ajustements."
        )
        result = validate_post(text)
        assert result["score"] >= 70
        assert result["passed"] is True

    def test_ai_sounding_text_low_score(self):
        text = (
            "Ce n'est pas un problème de trafic. C'est un problème de conversion.\n"
            "Le CRO — contrairement à ce qu'on pense — est crucial.\n"
            "Plongeons dans le vif du sujet et force est de constater que ça change tout."
        )
        result = validate_post(text)
        assert result["score"] < 50
        assert result["error_count"] >= 2

    def test_empty_text(self):
        result = validate_post("")
        assert result["score"] == 100
        assert result["passed"] is True

    def test_result_structure(self):
        result = validate_post("Un texte simple.")
        assert "score" in result
        assert "issues" in result
        assert "passed" in result
        assert "error_count" in result
        assert "warning_count" in result
        assert isinstance(result["issues"], list)
