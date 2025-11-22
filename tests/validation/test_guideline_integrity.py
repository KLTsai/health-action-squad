"""Medical Guideline Integrity Tests

Validates that medical_guidelines.yaml is up-to-date and contains
evidence-based thresholds. Enforces quarterly review cycle.

Tests:
- Guideline expiry check (fails if >90 days old)
- Known medical threshold validation
- File structure integrity
"""

import yaml
from datetime import datetime, timedelta
from pathlib import Path


class TestGuidelineIntegrity:
    """Test suite for medical_guidelines.yaml integrity"""

    @staticmethod
    def load_guidelines():
        """Load medical guidelines YAML file"""
        guideline_path = Path("resources/policies/medical_guidelines.yaml")
        assert guideline_path.exists(), "medical_guidelines.yaml not found"

        with open(guideline_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_guidelines_not_expired(self):
        """CRITICAL: Fail if guidelines are >90 days old (quarterly review required)"""
        guidelines = self.load_guidelines()

        last_reviewed_str = guidelines.get("last_reviewed")
        assert last_reviewed_str, "Missing 'last_reviewed' field in guidelines"

        last_reviewed = datetime.fromisoformat(last_reviewed_str)
        max_age = timedelta(days=90)
        age = datetime.now() - last_reviewed

        assert age < max_age, (
            f"Medical guidelines expired! "
            f"Last reviewed: {last_reviewed_str} ({age.days} days ago). "
            f"REQUIRED: Review and update medical_guidelines.yaml within 90 days. "
            f"Next review due: {guidelines.get('next_review_due', 'NOT SET')}"
        )

    def test_version_field_exists(self):
        """Ensure version tracking is present"""
        guidelines = self.load_guidelines()
        assert "version" in guidelines, "Missing 'version' field"
        assert guidelines["version"], "Version field is empty"

    def test_required_sections_exist(self):
        """Validate that all required medical sections are present"""
        guidelines = self.load_guidelines()

        required_sections = [
            "lipid_panel",
            "blood_pressure",
            "glucose_metabolism",
            "anthropometry",
            "lifestyle_factors",
        ]

        for section in required_sections:
            assert section in guidelines, f"Missing required section: {section}"

    def test_lipid_thresholds_are_evidence_based(self):
        """Validate known evidence-based thresholds for lipid panel"""
        guidelines = self.load_guidelines()
        lipid = guidelines["lipid_panel"]

        # NCEP ATP III threshold: Total cholesterol ≥200 is borderline high
        cholesterol_ranges = lipid["total_cholesterol"]["reference_ranges"]
        assert "<200" in cholesterol_ranges["optimal"], (
            "Total cholesterol optimal range should be <200 (NCEP ATP III)"
        )

        # NCEP ATP III: LDL ≥130 is borderline high
        ldl_ranges = lipid["ldl_cholesterol"]["reference_ranges"]
        assert "130-159" in ldl_ranges["borderline_high"], (
            "LDL borderline high should be 130-159 (NCEP ATP III)"
        )

        # HDL low thresholds
        hdl_ranges = lipid["hdl_cholesterol"]["reference_ranges"]
        assert "<40" in hdl_ranges["low_men"], "HDL low for men should be <40"
        assert "<50" in hdl_ranges["low_women"], "HDL low for women should be <50"

    def test_blood_pressure_thresholds_are_evidence_based(self):
        """Validate ACC/AHA 2017 blood pressure guidelines"""
        guidelines = self.load_guidelines()
        bp = guidelines["blood_pressure"]

        # ACC/AHA 2017: Hypertension starts at 130/80 (changed from 140/90)
        systolic_ranges = bp["systolic"]["reference_ranges"]
        assert "130-139" in systolic_ranges["stage1_hypertension"], (
            "Systolic Stage 1 HTN should be 130-139 (ACC/AHA 2017)"
        )

        diastolic_ranges = bp["diastolic"]["reference_ranges"]
        assert "80-89" in diastolic_ranges["stage1_hypertension"], (
            "Diastolic Stage 1 HTN should be 80-89 (ACC/AHA 2017)"
        )

    def test_glucose_thresholds_are_evidence_based(self):
        """Validate ADA diabetes diagnostic criteria"""
        guidelines = self.load_guidelines()
        glucose = guidelines["glucose_metabolism"]

        # ADA: Fasting glucose ≥126 indicates diabetes
        fasting_ranges = glucose["fasting_glucose"]["reference_ranges"]
        assert "≥126" in fasting_ranges["diabetes"], (
            "Fasting glucose diabetes threshold should be ≥126 (ADA)"
        )

        # ADA: HbA1c ≥6.5% indicates diabetes
        hba1c_ranges = glucose["hba1c"]["reference_ranges"]
        assert "≥6.5" in hba1c_ranges["diabetes"], (
            "HbA1c diabetes threshold should be ≥6.5% (ADA)"
        )

        # ADA: Prediabetes HbA1c 5.7-6.4%
        assert "5.7-6.4" in hba1c_ranges["prediabetes"], (
            "HbA1c prediabetes should be 5.7-6.4% (ADA)"
        )

    def test_asian_bmi_cutoffs_present(self):
        """Ensure Asian-specific BMI cutoffs are included (critical for Taiwan)"""
        guidelines = self.load_guidelines()
        bmi = guidelines["anthropometry"]["bmi"]

        # WHO Expert Consultation 2004: Asian overweight ≥23 (not ≥25)
        asian_ranges = bmi["reference_ranges_asian"]
        assert "23.0-24.9" in asian_ranges["overweight"], (
            "Asian overweight should be 23.0-24.9 (WHO 2004)"
        )

        # Ensure international ranges also exist for comparison
        assert "reference_ranges_international" in bmi, (
            "International BMI ranges should also be present"
        )

    def test_sources_are_documented(self):
        """Ensure all major sections cite medical guideline sources"""
        guidelines = self.load_guidelines()

        sections_requiring_sources = [
            ("lipid_panel", "total_cholesterol"),
            ("blood_pressure", "systolic"),
            ("glucose_metabolism", "fasting_glucose"),
        ]

        for section, subsection in sections_requiring_sources:
            source_info = guidelines[section][subsection].get("source")
            assert source_info, f"Missing source citation in {section}.{subsection}"
            assert "guideline" in source_info, f"Missing guideline name in {section}.{subsection}"
            assert "year" in source_info, f"Missing year in {section}.{subsection}"

    def test_legal_disclaimer_exists(self):
        """Ensure legal disclaimer is present"""
        guidelines = self.load_guidelines()
        assert "legal_disclaimer" in guidelines, "Missing legal disclaimer"
        disclaimer = guidelines["legal_disclaimer"]
        assert "NOT FOR DIAGNOSTIC USE" in disclaimer, (
            "Legal disclaimer must include 'NOT FOR DIAGNOSTIC USE' warning"
        )

    def test_maintenance_protocol_documented(self):
        """Ensure maintenance protocol is documented"""
        guidelines = self.load_guidelines()
        assert "maintenance_protocol" in guidelines, "Missing maintenance protocol"
        protocol = guidelines["maintenance_protocol"]
        assert "QUARTERLY REVIEW" in protocol, (
            "Maintenance protocol must mention quarterly review"
        )


class TestKnownClinicalCases:
    """Test against known clinical scenarios to validate threshold logic"""

    @staticmethod
    def load_guidelines():
        """Load medical guidelines YAML file"""
        guideline_path = Path("resources/policies/medical_guidelines.yaml")
        with open(guideline_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_metabolic_syndrome_criteria_complete(self):
        """Validate IDF metabolic syndrome diagnostic criteria"""
        guidelines = self.load_guidelines()
        metabolic_syndrome = guidelines["composite_scores"]["metabolic_syndrome"]

        assert metabolic_syndrome["diagnostic_criteria"]["criteria_needed"] == 3, (
            "Metabolic syndrome requires 3 out of 5 criteria (IDF 2006)"
        )

        components = metabolic_syndrome["diagnostic_criteria"]["components"]
        assert len(components) == 5, "Should have 5 metabolic syndrome components"

        # Verify key components are present
        component_text = " ".join(components)
        assert "Waist" in component_text, "Missing waist circumference criterion"
        assert "Triglycerides" in component_text, "Missing triglycerides criterion"
        assert "HDL" in component_text, "Missing HDL criterion"
        assert "Blood pressure" in component_text, "Missing blood pressure criterion"
        assert "glucose" in component_text, "Missing glucose criterion"
