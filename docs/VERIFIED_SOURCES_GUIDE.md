# Verified Sources - Maintenance Guide

## 📋 Overview

This document explains the **Verified Sources** system in Health Action Squad and how to maintain it.

## 🎯 Purpose

The Verified Sources list ensures that:
1. **Planner Agent** uses only credible, working URLs when citing medical recommendations
2. **Guard Agent** can validate sources against known trustworthy organizations
3. **Users** receive links that actually work and lead to authoritative health information

## 📍 Location

Verified Sources are maintained in:
- **Primary List**: [`resources/prompts/planner_prompt.txt`](../resources/prompts/planner_prompt.txt) (Lines 71-128)
- **Validation Rules**: [`resources/prompts/guard_prompt.txt`](../resources/prompts/guard_prompt.txt) (Lines 83-101)

## 📊 Current Coverage (as of Nov 2024)

### Health Topics Covered (7 categories)

1. **Cardiovascular Health**
   - High Blood Pressure
   - DASH Diet
   - Cholesterol Management

2. **Metabolic Health & Diabetes**
   - Diabetes Basics
   - Blood Sugar Management
   - Prediabetes

3. **Nutrition & Weight Management**
   - Healthy Weight
   - Dietary Guidelines
   - Heart-Healthy Nutrition

4. **Physical Activity & Exercise**
   - Physical Activity Guidelines
   - Exercise Basics

5. **Sleep & Mental Health**
   - Sleep Health
   - Mental Health & Stress

6. **Preventive Care**
   - General Prevention

### Trusted Organizations (10+)

- CDC (Centers for Disease Control)
- WHO (World Health Organization)
- NIH (National Institutes of Health)
  - NHLBI (Heart, Lung, Blood Institute)
  - NIMH (Mental Health Institute)
- AHA (American Heart Association)
- ADA (American Diabetes Association)
- USDA (Agriculture - Nutrition)
- HHS (Health and Human Services)

## 🧪 Testing URLs

We provide an automated test script to validate all URLs:

```bash
# Run from project root
python tests/test_verified_sources.py
```

This script:
- Extracts all URLs from `planner_prompt.txt`
- Tests each URL for accessibility (HTTP status)
- Reports broken links with status codes
- Exits with error code if any URLs fail

### Recommended Testing Schedule

- **Weekly**: Run automated tests (in CI/CD)
- **Monthly**: Manual review for outdated content
- **Quarterly**: Check for updated guidelines (e.g., AHA releases annual updates)

## 🔧 Adding New Sources

### Step 1: Find Credible Source

Acceptable organizations:
- ✅ CDC, WHO, NIH, AHA, ADA
- ✅ Government health agencies
- ✅ Peer-reviewed journals
- ❌ Personal blogs
- ❌ Commercial websites
- ❌ Health content farms (WebMD, Healthline)

### Step 2: Test URL Accessibility

```bash
# Test the URL manually first
curl -I https://example.com/health-topic
```

Look for:
- `200 OK` status
- No redirects to unrelated content
- Stable URL pattern (avoid pages with dates/version numbers)

### Step 3: Add to planner_prompt.txt

Format:
```markdown
### [Category Name]
- **[Topic Name]**: 
  - `https://primary-source.gov/topic`
  - `https://backup-source.org/topic` (optional)
```

### Step 4: Update guard_prompt.txt (if new organization)

If the source is from a new organization not listed in Guard's acceptable sources, add it:

```markdown
- **[Organization Name]** - `domain.com`
```

### Step 5: Run Tests

```bash
python tests/test_verified_sources.py
```

Ensure all URLs pass before committing.

## 📝 URL Best Practices

### ✅ DO:
- Use top-level topic pages (stable URLs)
- Prefer `.gov`, `.org` domains for health topics
- Include backup sources (2 URLs per topic)
- Use HTTPS (not HTTP)

### ❌ DON'T:
- Use URLs with version numbers (`/2024/guideline`)
- Link to specific news articles (may expire)
- Use URLs with session IDs or tracking parameters
- Link to PDF downloads (may move)

## 🐛 Handling Broken Links

If a URL breaks (404, 403, etc.):

1. **Search for Updated URL**:
   - Check organization's sitemap
   - Use Google: `site:cdc.gov diabetes`

2. **Find Replacement**:
   - Look for updated guidelines
   - Find equivalent page from backup organization

3. **Update Prompt**:
   - Replace old URL with new one
   - Document change in commit message

4. **Test**:
   - Run `python tests/test_verified_sources.py`
   - Generate a test plan to verify Planner uses new URL

## 📅 Maintenance Checklist

### Weekly
- [ ] Run automated URL tests
- [ ] Review any CI/CD failures

### Monthly
- [ ] Check CDC, AHA, WHO for updated guidelines
- [ ] Review test plans for source usage patterns
- [ ] Update outdated URLs

### Quarterly
- [ ] Full audit of all sources
- [ ] Check for new relevant topics
- [ ] Update documentation
- [ ] Review Guard rejection logs for source issues

### Annually
- [ ] Major update: Review entire Verified Sources list
- [ ] Add new health topics based on user requests
- [ ] Archive deprecated guidelines
- [ ] Update organization list

## 🚨 Recent Changes

### November 2024 - Major Update
- **Fixed**: Replaced 3 broken URLs (75% failure rate)
- **Added**: Expanded from 4 topics to 7+ categories
- **Added**: Diabetes, cholesterol, mental health sources
- **Added**: 24+ verified URLs (up from 4)
- **Created**: Automated testing script

## 🔗 Related Files

- [`resources/prompts/planner_prompt.txt`](../resources/prompts/planner_prompt.txt) - Main Verified Sources list
- [`resources/prompts/guard_prompt.txt`](../resources/prompts/guard_prompt.txt) - Source validation rules
- [`tests/test_verified_sources.py`](../tests/test_verified_sources.py) - Automated URL testing
- [`docs/source_evaluation_report.md`](../../.gemini/antigravity/brain/5005bee4-3587-4b63-9051-9c425b67bc84/source_evaluation_report.md) - Detailed evaluation

## 📞 Questions?

If you encounter issues:
1. Check the evaluation report for detailed analysis
2. Run the automated tests
3. Review Guard Agent logs for source rejection patterns
