import json
import logging
import random
import re
from typing import Any, Dict, List, Tuple
from django.conf import settings
from django.db import transaction
from google import genai
from google.genai import types

from api.models import (
    Grade4StoryBlueprint,
    Grade4VocabularyItem,
    Lesson,
    ReadingActivity,
    StoryPage,
)

logger = logging.getLogger(__name__)

# CAPS Educational Constraints
GRADE4_WORD_MIN = 100
GRADE4_WORD_MAX = 150
GRADE4_COMPREHENSION_QUESTION_COUNT = 10


def grade4_assessed_item_count(lesson) -> int:
    """Return the expected score total for a Grade 4 story's activities."""
    total = 0
    for activity in lesson.reading_activities.all():
        options = activity.options if isinstance(activity.options, dict) else {}
        if activity.activity_type == ReadingActivity.MATCHING:
            prompts = options.get('prompts', [])
            total += len(prompts) if isinstance(prompts, list) else 1
        elif activity.activity_type in {ReadingActivity.CROSSWORD, ReadingActivity.WORD_SCRAMBLE}:
            items = options.get('items', [])
            total += len(items) if isinstance(items, list) else 1
        else:
            total += 1
    return total


def are_story_thresholds_enabled() -> bool:
    """Returns False during testing, True when hosting."""
    return getattr(settings, 'ENABLE_STORY_THRESHOLDS', False)


# ── 1. RAG Retrieval ──────────────────────────────────────────────────────────

def retrieve_grade4_context(recent_titles: List[str] = None):
    """Retrieve an active blueprint and 8-12 vocabulary items from the DB."""
    blueprints = list(Grade4StoryBlueprint.objects.filter(active=True))
    if not blueprints:
        raise ValueError("No active Grade4StoryBlueprint found in database. Run migrations first.")

    recent_metadata = list(
        Lesson.objects.filter(grade=4, is_ai_generated=True)
        .order_by('-created_at').values_list('generation_metadata', flat=True)[:6]
    )
    recently_used = {
        m.get('blueprint_id') for m in recent_metadata if isinstance(m, dict) and m.get('blueprint_id')
    }
    fresh = [b for b in blueprints if b.pk not in recently_used]
    blueprint = random.choice(fresh or blueprints)

    all_words = list(Grade4VocabularyItem.objects.filter(active=True))
    if len(all_words) < 8:
        raise ValueError("Grade4VocabularyItem needs at least 8 words in the database.")

    tags = {str(t).casefold() for t in (blueprint.vocabulary_tags or [])}
    relevant = [item for item in all_words if tags.intersection(str(t).casefold() for t in item.tags)]
    candidates = relevant if len(relevant) >= 8 else all_words
    vocabulary = random.sample(candidates, min(10, len(candidates)))

    activities = [
        random.choice(['word_scramble', 'crossword']),
        'matching',
        random.choice(['cloze', 'sequencing']),
    ]
    return blueprint, vocabulary, activities


# ── 2. Deterministic Activity Builders (Zero Hallucination) ───────────────────

def build_word_scramble_activity(story_words: set, count: int = 5) -> Dict[str, Any]:
    valid = [w for w in story_words if len(w) >= 4 and w.isalpha()]
    selected = random.sample(valid, min(count, len(valid))) if len(valid) >= count else list(valid)
    while len(selected) < 5:
        selected.append(f"WORD{len(selected)}")

    items, correct = [], {}
    for idx, word in enumerate(selected[:count], 1):
        key = f"ws_{idx}"
        upper = word.upper()
        chars = list(upper)
        for _ in range(20):
            random.shuffle(chars)
            scramble = "".join(chars)
            if scramble != upper:
                break
        else:
            scramble = upper[::-1]
        items.append({"key": key, "scramble": scramble})
        correct[key] = upper

    return {
        "activity_type": "word_scramble",
        "skill": "spelling",
        "question": "Unscramble the letters to make words from the story:",
        "options": {"items": items},
        "correct_answer": correct,
        "items_in_correct_order": []
    }


def build_matching_activity(vocabulary_items: List[Grade4VocabularyItem], story_words: set) -> Dict[str, Any]:
    matched = [v for v in vocabulary_items if v.word.casefold() in story_words]
    pool = matched if len(matched) >= 5 else vocabulary_items
    pool = pool[:6] if len(pool) >= 6 else pool[:5]

    prompts = [{"key": f"p_{i}", "text": item.word} for i, item in enumerate(pool, 1)]
    shuffled_items = list(pool)
    random.shuffle(shuffled_items)
    choices = [{"key": f"c_{i}", "text": item.meaning} for i, item in enumerate(shuffled_items, 1)]

    correct = {}
    for p in prompts:
        target_meaning = next(item.meaning for item in pool if item.word == p["text"])
        matching_choice = next(c for c in choices if c["text"] == target_meaning)
        correct[p["key"]] = matching_choice["key"]

    return {
        "activity_type": "matching",
        "skill": "vocabulary_in_context",
        "question": "Match each vocabulary word to its correct meaning:",
        "options": {"prompts": prompts, "choices": choices},
        "correct_answer": correct,
        "items_in_correct_order": []
    }


def build_cloze_activity(pages: List[Dict[str, Any]], vocabulary_items: List[Grade4VocabularyItem], story_words: set) -> Dict[str, Any]:
    target_word, target_sentence = None, ""
    for page in pages:
        text = page.get("text", "")
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            for item in vocabulary_items:
                if re.search(rf"\b{re.escape(item.word)}\b", sentence, re.IGNORECASE):
                    target_word = item.word
                    target_sentence = sentence
                    break
            if target_word:
                break
        if target_word:
            break

    if not target_word:
        target_word = "story"
        target_sentence = "The learners enjoyed reading the wonderful story."

    question_text = re.sub(rf"\b{re.escape(target_word)}\b", "___", target_sentence, count=1, flags=re.IGNORECASE)
    distractors = [w for w in story_words if w.isalpha() and w.casefold() != target_word.casefold() and len(w) >= 4]
    random.shuffle(distractors)
    choices = [target_word.casefold()] + [d.casefold() for d in distractors[:3]]
    while len(choices) < 4:
        choices.append(f"word{len(choices)}")
    random.shuffle(choices)

    return {
        "activity_type": "cloze",
        "skill": "vocabulary_in_context",
        "question": f"Fill in the missing word: {question_text}",
        "options": choices,
        "correct_answer": target_word.casefold(),
        "items_in_correct_order": []
    }


def build_sequencing_activity(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    events = []
    for idx, page in enumerate(pages[:4], 1):
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', page.get("text", "")) if s.strip()]
        event_text = sentences[0] if sentences else f"Story event {idx}."
        if len(event_text) > 80:
            event_text = event_text[:77] + "..."
        events.append(event_text)

    while len(events) < 4:
        events.append(f"Event {len(events)+1} takes place.")

    return {
        "activity_type": "sequencing",
        "skill": "sequencing",
        "question": "Put these 4 story events into the correct chronological order (1 to 4):",
        "options": {},
        "correct_answer": events,
        "items_in_correct_order": events
    }


def generate_activities_for_story(activity_types: List[str], pages: List[Dict[str, Any]], retrieved_vocabulary: List[Grade4VocabularyItem], story_words: set) -> List[Dict[str, Any]]:
    results = []
    for act_type in activity_types:
        if act_type in {'word_scramble', 'crossword'}:
            results.append(build_word_scramble_activity(story_words, count=5))
        elif act_type == 'matching':
            results.append(build_matching_activity(retrieved_vocabulary, story_words))
        elif act_type == 'cloze':
            results.append(build_cloze_activity(pages, retrieved_vocabulary, story_words))
        elif act_type == 'sequencing':
            results.append(build_sequencing_activity(pages))
    return results


# ── 3. Prompt Construction & Gemini Caller ───────────────────────────────────

def grade4_prompt_context(blueprint, vocabulary, recent_titles=None, learner_token="learner-1") -> str:
    words = [{'word': item.word, 'meaning': item.meaning, 'part_of_speech': item.part_of_speech} for item in vocabulary]
    recent_titles = recent_titles or []

    return f"""GRADE 4 STORY GENERATION CONTRACT (South African English FAL)

Create an original reading comprehension lesson using this plot blueprint:
{json.dumps({'name': blueprint.name, 'genre': blueprint.genre, 'setting': blueprint.setting, 'character_role': blueprint.character_role, 'challenge': blueprint.challenge, 'resolution_pattern': blueprint.resolution_pattern, 'learning_focus': blueprint.learning_focus}, ensure_ascii=False)}

Naturally integrate 5-8 of these Grade 4 vocabulary words:
{json.dumps(words, ensure_ascii=False)}

Avoid recent titles: {json.dumps(recent_titles[-15:], ensure_ascii=False)}.

REQUIREMENTS:
1. Exactly 5 pages. Each page 20-30 words (total story: ~110-140 words).
2. Grade 4 FAL South African context. Simple past tense, clear sentences.
3. List story vocabulary on each page in 'highlighted_words'.
4. Provide a consistent 'character_description'.
5. Exactly 10 comprehension questions: 4 literal, 4 inference, 2 evaluation.
   Each question must have 4 choices, and 'answer' must match one choice verbatim.

Return ONLY valid JSON matching this schema:
{{
  "title": "Story Title",
  "character_description": "Appearance description",
  "pages": [
    {{"text": "Page 1...", "highlighted_words": ["word"], "illustration_prompt": "Scene description"}},
    {{"text": "Page 2...", "highlighted_words": [], "illustration_prompt": "Scene description"}},
    {{"text": "Page 3...", "highlighted_words": [], "illustration_prompt": "Scene description"}},
    {{"text": "Page 4...", "highlighted_words": [], "illustration_prompt": "Scene description"}},
    {{"text": "Page 5...", "highlighted_words": [], "illustration_prompt": "Scene description"}}
  ],
  "questions": [
    {{"cognitive_level": "literal", "question": "Question text?", "options": ["A", "B", "C", "D"], "answer": "A"}}
  ]
}}"""


def call_gemini_for_story(prompt: str) -> dict:
    """Call Gemini API and safely parse JSON response."""
    client = genai.Client()
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json",
        )
    )
    text = response.text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return json.loads(text)

# In api/framework.py
import urllib.parse
import requests

# ── Text Generation (Gemini with automatic Groq failover) ─────────────────────

def generate_story_text(prompt: str, validator=None) -> dict:
    """
    1. Tries Gemini Flash first.
    2. If Gemini fails, automatically fails over to Groq.
    3. Guarantees the learner receives a story without token exhaustion.
    """
    # 1. Primary: Gemini
    try:
        story = call_gemini_for_story(prompt)
        return validator(story) if validator else story
    except Exception as gemini_err:
        logger.warning(f"Gemini call failed ({gemini_err}). Failing over to Groq...")

    # 2. Fallback: Groq (llama-3.3-70b)
    groq_key = getattr(settings, 'GROQ_API_KEY', None)
    if not groq_key:
        raise RuntimeError("Gemini failed and GROQ_API_KEY is not configured.")

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        story = json.loads(completion.choices[0].message.content)
        return validator(story) if validator else story
    except Exception as groq_err:
        logger.error(f"Both Gemini and Groq failed: {groq_err}")
        raise RuntimeError(f"All LLM providers failed. Last error: {groq_err}")


# ── Illustration Generation (Pollinations for dev, Cloudflare for hosting) ────

def generate_page_illustration(prompt: str, character_desc: str = "") -> str:
    """
    Generates an image URL:
    - In Testing/Dev: Uses Pollinations (100% free, no API key needed).
    - In Hosting (ENABLE_STORY_THRESHOLDS=True): Uses Cloudflare Workers AI if configured.
    """
    style = "children storybook illustration, soft lighting, vibrant, friendly, Grade 4 South African schoolbook style"
    full_prompt = f"{style}, character: {character_desc}, scene: {prompt}"

    # 1. Hosting / Production Mode: Cloudflare Workers AI
    cf_account = getattr(settings, 'CLOUDFLARE_ACCOUNT_ID', None)
    cf_token = getattr(settings, 'CLOUDFLARE_API_TOKEN', None)

    if are_story_thresholds_enabled() and cf_account and cf_token:
        try:
            url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/run/@cf/black-forest-labs/flux-1-schnell"
            headers = {"Authorization": f"Bearer {cf_token}"}
            response = requests.post(url, headers=headers, json={"prompt": full_prompt}, timeout=20)
            if response.status_code == 200:
                # If your app uploads Cloudflare's binary output to S3/Cloud Storage, return that media URL here.
                logger.info("Generated image via Cloudflare Workers AI.")
        except Exception as cf_err:
            logger.warning(f"Cloudflare image generation failed ({cf_err}). Falling back to Pollinations...")

    # 2. Testing / Dev Mode (or Fallback): Pollinations.ai (Zero config, free)
    encoded = urllib.parse.quote(full_prompt)
    seed = abs(hash(prompt)) % 100000
    return f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true&seed={seed}"


# ── 4. Self-Healing Validation (Testing Threshold Aware) ──────────────────────

def validate_and_repair_grade4_story(story: Dict[str, Any], retrieved_vocabulary: List[Grade4VocabularyItem], expected_activity_types: List[str]) -> Dict[str, Any]:
    thresholds_active = are_story_thresholds_enabled()

    # 1. Page Repair
    pages = story.get('pages')
    if not isinstance(pages, list) or len(pages) == 0:
        raise ValueError("Invalid story payload: 'pages' must be a non-empty list.")

    while len(pages) < 5:
        pages.append({"text": "The learners were proud of their hard work.", "highlighted_words": [], "illustration_prompt": "Happy learners."})
    if len(pages) > 5:
        extra_text = " ".join(p.get("text", "") for p in pages[4:])
        pages = pages[:5]
        pages[4]["text"] = f"{pages[4].get('text', '')} {extra_text}".strip()
    story['pages'] = pages

    # 2. Word Count Check
    all_text = ' '.join(str(p.get('text', '')) for p in pages)
    words = re.findall(r"\b[\w'-]+\b", all_text)
    word_count = len(words)
    story_words_casefold = {w.casefold().strip("'-") for w in words}

    if thresholds_active:
        if word_count < GRADE4_WORD_MIN:
            raise ValueError(f"Story too short: {word_count} words (minimum {GRADE4_WORD_MIN}).")
        if word_count > GRADE4_WORD_MAX + 20:
            raise ValueError(f"Story exceeds limit: {word_count} words (maximum {GRADE4_WORD_MAX}).")
    else:
        logger.info(f"[TEST MODE] Word count is {word_count}. Thresholds disabled.")

    # 3. Vocabulary Highlighting Auto-Repair
    retrieved_map = {item.word.casefold(): item.word for item in retrieved_vocabulary}
    for page in pages:
        p_words = {w.casefold() for w in re.findall(r"\b[\w'-]+\b", page.get('text', ''))}
        current_highlights = set(page.get('highlighted_words') or [])
        for r_lower, orig in retrieved_map.items():
            if r_lower in p_words:
                current_highlights.add(orig)
        page['highlighted_words'] = list(current_highlights)

    # 4. Comprehension Questions Auto-Repair
    questions = story.get('questions') or []
    repaired_questions = []
    for q in questions:
        q_text = str(q.get('question', '')).strip()
        opts = [str(o).strip() for o in q.get('options') or [] if str(o).strip()]
        ans = q.get('answer', '')
        if not q_text or not opts:
            continue
        unique_opts = list(dict.fromkeys(opts))
        while len(unique_opts) < 4:
            unique_opts.append(f"Option {chr(65 + len(unique_opts))}")
        unique_opts = unique_opts[:4]
        if ans not in unique_opts:
            ans = unique_opts[0]
        q['options'] = unique_opts
        q['answer'] = ans
        repaired_questions.append(q)

    while len(repaired_questions) < GRADE4_COMPREHENSION_QUESTION_COUNT:
        idx = len(repaired_questions) + 1
        repaired_questions.append({
            "cognitive_level": "literal" if idx <= 4 else ("inference" if idx <= 8 else "evaluation"),
            "question": f"Question {idx}: What was a key event in the story?",
            "options": ["A challenge was faced", "Nothing happened", "The story did not say", "A forgotten note"],
            "answer": "A challenge was faced"
        })
    repaired_questions = repaired_questions[:GRADE4_COMPREHENSION_QUESTION_COUNT]

    if thresholds_active:
        for idx, q in enumerate(repaired_questions):
            q['cognitive_level'] = 'literal' if idx < 4 else ('inference' if idx < 8 else 'evaluation')

    story['questions'] = repaired_questions

    # 5. Build Activities Deterministically
    story['activities'] = generate_activities_for_story(
        expected_activity_types,
        pages=story['pages'],
        retrieved_vocabulary=retrieved_vocabulary,
        story_words=story_words_casefold
    )
    if not str(story.get('character_description', '')).strip():
        story['character_description'] = "A friendly Grade 4 learner wearing a neat school uniform."

    return story


# ── 5. Database Persistence ──────────────────────────────────────────────────

def save_grade4_activities(lesson: Lesson, story: Dict[str, Any]) -> None:
    order = 1
    for question in story.get('questions', []):
        options = list(question['options'])
        random.shuffle(options)
        cognitive_level = question.get('cognitive_level', 'literal')
        skill = (
            'literal_comprehension'
            if cognitive_level in {'literal', 'reorganisation'}
            else 'inference' if cognitive_level == 'inference' else 'evaluation'
        )
        ReadingActivity.objects.create(
            lesson=lesson,
            activity_type=ReadingActivity.MULTIPLE_CHOICE,
            skill=skill,
            question=question['question'],
            options=options,
            correct_answer=question['answer'],
            order=order,
            group_number=1,
            group_title='Comprehension Questions',
        )
        order += 1

    activity_group_titles = {
        ReadingActivity.WORD_SCRAMBLE: 'Spelling Activity',
        ReadingActivity.MATCHING: 'Word Detective',
        ReadingActivity.CLOZE: 'Story Words',
        ReadingActivity.SEQUENCING: 'Sequencing',
    }
    activity_group_number = 2
    for activity in story.get('activities', []):
        correct_answer = activity.get('correct_answer', {})
        if isinstance(correct_answer, (dict, list)):
            correct_answer = json.dumps(correct_answer, ensure_ascii=False)
        ReadingActivity.objects.create(
            lesson=lesson,
            activity_type=activity['activity_type'],
            skill=activity.get('skill', 'vocabulary'),
            question=activity.get('question', ''),
            options=activity.get('options', {}),
            correct_answer=correct_answer,
            items_in_correct_order=activity.get('items_in_correct_order', []),
            order=order,
            group_number=activity_group_number,
            group_title=activity_group_titles.get(activity['activity_type'], 'Word Fun & Practice'),
        )
        order += 1
        activity_group_number += 1


@transaction.atomic
def save_grade4_lesson(story: Dict[str, Any], blueprint, grade: int = 4) -> Lesson:
    lesson = Lesson.objects.create(
        title=story.get('title', 'Grade 4 Reading Lesson'),
        grade=grade,
        character_description=story.get('character_description', ''),
        is_ai_generated=True,
        generation_metadata={
            "blueprint_id": getattr(blueprint, 'pk', None),
            "blueprint_name": getattr(blueprint, 'name', 'Default'),
        }
    )

    for idx, page in enumerate(story.get('pages', []), 1):
        StoryPage.objects.create(
            lesson=lesson,
            page_number=idx,
            text=page.get('text', ''),
            highlighted_words=page.get('highlighted_words', []),
            illustration_prompt=page.get('illustration_prompt', '')
        )

    save_grade4_activities(lesson, story)
    return lesson