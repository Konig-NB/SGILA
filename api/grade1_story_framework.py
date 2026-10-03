"""CAPS-grounded retrieval, validation, and assessments for Grade 1 AI stories."""

import json
import random
import re
from django.db import transaction

from api.grade1_activity_blueprints import (
    GRADE_ONE_ACTIVITY_BLUEPRINTS,
)
from api.models import Lesson, ReadingActivity


GRADE1_PAGE_COUNT = 3
GRADE1_WORDS_PER_PAGE = (12, 22)
GRADE1_ACTIVITY_GROUPS = (
    (1, 'Phonics & Story-Word Spelling'),
    (2, 'Short Sentences & Picture Matching'),
    (3, 'Story Sentence Completion'),
)

# Short source extracts distilled from the supplied South African CAPS English
# FAL document. These are retrieval material for the generator, not learner text.
CAPS_KNOWLEDGE = [
    {
        'id': 'caps-g1-additional-language-foundation',
        'source': 'CAPS English First Additional Language Grades 1-3',
        'section': 'Introducing the First Additional Language; Listening and Speaking',
        'text': (
            'Grade 1 English FAL learners need a strong oral foundation and lots of '
            'simple spoken English they can understand from context. Illustrated '
            'stories and shared reading provide meaningful support; learners should '
            'hear, talk about, and understand language without unnecessary pressure.'
        ),
        'constraints': ['simple contextual language', 'illustrations support meaning', 'oral comprehension'],
    },
    {
        'id': 'caps-g1-term1-phonics-reading',
        'source': 'CAPS English First Additional Language Grades 1-3',
        'section': 'Grade 1, Term 1, Reading and Phonics',
        'document_page': 50,
        'text': (
            'Revise single-letter sounds and build short, familiar words from known '
            'sounds. Learners distinguish easily confused sounds, identify common '
            'letter-sound relationships, and build and break down three-letter words. '
            'Guided texts should be very simple, repeat structures and vocabulary, '
            'and use pictures to support the text.'
        ),
        'constraints': ['short familiar words', 'single-letter sound awareness', 'three-letter word building', 'repetition', 'picture support'],
    },
    {
        'id': 'caps-g1-shared-reading',
        'source': 'CAPS English First Additional Language Grades 1-3',
        'section': 'Shared Reading and Comprehension',
        'text': (
            'Shared reading gives Grade 1 learners meaningful, supportive exposure '
            'to English. The teacher discusses the text and asks questions to check '
            'understanding. Use familiar settings, visible actions, and language '
            'children can understand from context.'
        ),
        'constraints': ['familiar contexts', 'clear visible events', 'literal questions', 'teacher-supported comprehension'],
    },
]

THEMES = [
    'a child building a paper boat', 'a lost button found at school',
    'painting a bright picture with a friend', 'planting seeds in a pot',
    'making music with kitchen objects', 'a library book returned on time',
    'a child helping at a community soup kitchen', 'a family making bead bracelets',
    'finding a ladybird in the garden', 'a classroom shadow puppet show',
    'a market visit to choose fresh vegetables', 'a child learning to skip rope',
    'a windy day flying a handmade kite', 'sharing a story with a younger cousin',
    'a child caring for a hurt bird', 'making a cardboard town together',
    'a school art show with clay animals', 'a family sorting bright socks',
    'finding a safe path through a puddle', 'a child baking bread with an aunt',
    'a friend teaching a new clapping game', 'a small seed growing after rain',
    'a child helping at a neighbourhood garden', 'a family picnic beside a stream',
    'a child fixing a wobbly toy', 'a school day with a surprise visitor',
    'a child collecting fallen leaves for art', 'a friendly race with toy cars',
]

GRADE1_ACTIVITY_VARIANTS = ('phonics', 'visual_vocabulary', 'mixed')


def grade1_generation_preferences():
    recent_metadata = list(
        Lesson.objects.filter(grade=1, is_ai_generated=True)
        .order_by('-created_at').values_list(
            'generation_metadata', 'character_description',
        )[:12]
    )
    recent_themes = []
    recent_variants = []
    recent_characters = []
    for metadata, character_description in recent_metadata:
        if not isinstance(metadata, dict):
            metadata = {}
        rag = metadata.get('rag') or {}
        if rag.get('theme'):
            recent_themes.append(str(rag['theme']))
        if metadata.get('activity_variant'):
            recent_variants.append(str(metadata['activity_variant']))
        if character_description:
            recent_characters.append(str(character_description))

    fresh_themes = [theme for theme in THEMES if theme not in recent_themes[:8]]
    theme = random.choice(fresh_themes or THEMES)
    fresh_variants = [variant for variant in GRADE1_ACTIVITY_VARIANTS
                      if variant not in recent_variants[:1]]
    activity_variant = random.choice(fresh_variants or GRADE1_ACTIVITY_VARIANTS)
    return theme, recent_themes, recent_characters, activity_variant


def grade1_vocabulary_page_indices(variant):
    if variant == 'visual_vocabulary':
        return set(range(GRADE1_PAGE_COUNT))
    if variant == 'mixed':
        return {1}
    return set()


def _tokens(value):
    return set(re.findall(r"[a-z]+", str(value).casefold()))


def retrieve_grade1_context(theme, recent_titles=None):
    """Retrieve relevant CAPS guidance and Grade 1 workbook assessment examples."""
    query = _tokens(theme)
    docs = []
    for doc in CAPS_KNOWLEDGE:
        score = len(query & _tokens(doc['text'] + ' ' + doc['section'] + ' ' + ' '.join(doc['constraints'])) )
        docs.append((score, doc))

    # The supplied Grade 1 reader is represented by the existing Grade 1 lesson
    # corpus. Retrieve examples for level and assessment design only; never copy
    # their characters, plots, or wording into a new story.
    recent_title_set = {str(title).casefold() for title in (recent_titles or [])}
    for lesson in Lesson.objects.filter(grade=1, is_ai_generated=False).prefetch_related('pages', 'reading_activities'):
        pages = list(lesson.pages.all())
        if not pages or lesson.title.casefold() in recent_title_set:
            continue
        body = ' '.join(page.text for page in pages)
        score = len(query & _tokens(lesson.title + ' ' + body))
        if score:
            docs.append((score, {
                'id': f'workbook-{lesson.pk}',
                'source': 'Existing Grade 1 English workbook story corpus',
                'section': lesson.title,
                'text': f'Learner-level example: {body[:900]}',
                'constraints': ['style and level reference only; create an original plot'],
            }))

    docs.sort(key=lambda item: (item[0], item[1]['id']), reverse=True)
    cap_docs = [doc for _, doc in docs if doc['id'].startswith('caps-')]
    workbook_docs = [doc for _, doc in docs if doc['id'].startswith('workbook-')]
    retrieved = cap_docs + workbook_docs[:1]
    recent_titles = [str(title) for title in (recent_titles or []) if title]
    assessment_reference = {
        'groups': [
            {'number': number, 'title': title, 'count': 3}
            for number, title in GRADE1_ACTIVITY_GROUPS
        ],
        'existing_grade1_story_count': len(GRADE_ONE_ACTIVITY_BLUEPRINTS),
    }
    return retrieved, assessment_reference, recent_titles


def grade1_prompt_context(theme, recent_titles=None, recent_themes=None, recent_characters=None):
    retrieved, assessment_reference, recent_titles = retrieve_grade1_context(theme, recent_titles)
    curriculum = [{key: doc.get(key) for key in ('source', 'section', 'document_page', 'text', 'constraints')} for doc in retrieved]
    prompt = f'''Create an original English First Additional Language reading story for a South African Grade 1 learner.
Fresh story idea: {theme}.
Avoid these recent titles: {json.dumps(recent_titles[-12:], ensure_ascii=False)}.
Avoid repeating these recent story ideas: {json.dumps((recent_themes or [])[:8], ensure_ascii=False)}.
Use a different main character from these recent appearance descriptions: {json.dumps((recent_characters or [])[:6], ensure_ascii=False)}.

Use these retrieved CAPS and workbook references as age-level and learning guidance. Workbook references are examples only: do not reuse their characters, plots, titles, or sentences.
{json.dumps(curriculum, ensure_ascii=False)}

LEARNING REQUIREMENTS:
- Use simple, familiar English, short sentences, and an everyday safe setting.
- Make the story understandable from context and easy to illustrate. Keep one main character consistent.
- Exactly 3 story pages, 12-22 words per page, with at least 2 short sentences on every page.
- Use 2-3 short sentences per page. Aim for 5-9 words per sentence and avoid long descriptions.
- Follow the fresh story idea closely. Do not add a dog, a walk, or a father by default unless the idea asks for one.
- Do not reuse a recent character, animal, family role, central object, or main action.
- Include a clear beginning, middle, and ending, with 3-5 concrete story words that can be sounded out or matched to pictures.
- Return exactly 3 simple concrete object words in 'vocabulary_words', one from each page, that can be shown alone in a picture.
- Make exactly 3 picture_match items. Each has a short sentence copied exactly from that page and its page_number (1-3).
- Make exactly 3 phonics_words, one for each page in page order. Each is a distinct 3-5 letter alphabetic word appearing on its corresponding page.
- Return exactly this JSON shape; do not include Markdown or extra keys:
{{"title":"Short title","character_description":"One consistent child-friendly appearance sentence","pages":[{{"text":"Two or three short sentences...","highlighted_words":["..."],"illustration_prompt":"One simple scene"}}],"phonics_words":["...","...","..."],"vocabulary_words":["...","...","..."],"picture_match":[{{"sentence":"Exact sentence from page 1","page_number":1}},{{"sentence":"Exact sentence from page 2","page_number":2}},{{"sentence":"Exact sentence from page 3","page_number":3}}]}}

The learner activities will use one of these Grade 1 group-one formats: phonics letter completion, picture-based story vocabulary, or a mix of both. Group 2 uses short sentence and picture matching. Group 3 uses a missing story word and two answer choices. Picture vocabulary must use the supplied story words and one clear object image per question.'''
    return prompt, retrieved, assessment_reference


def _sentences(text):
    return [sentence.strip() for sentence in re.split(r'(?<=[.!?])\s+', str(text).strip()) if sentence.strip()]


def _word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def _find_sentence_word(pages, word):
    pattern = re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE)
    for page_index, page in enumerate(pages):
        for sentence in _sentences(page['text']):
            match = pattern.search(sentence)
            if match:
                return page_index, sentence, match
    return None


def _repair_grade1_page_text(text):
    sentences = _sentences(str(text or '').strip())
    if not sentences:
        raise ValueError('Every story page needs text.')
    if len(sentences) < 2:
        raise ValueError('Each Grade 1 page must contain 2-3 short sentences.')
    if len(sentences) > 3:
        remaining = ' '.join(sentence.rstrip('.!?') for sentence in sentences[2:])
        sentences = sentences[:2] + [f'{remaining}.']

    def sentence_word_count(sentence):
        return len(sentence.split())

    while sum(sentence_word_count(sentence) for sentence in sentences) > GRADE1_WORDS_PER_PAGE[1]:
        sentence_index = max(range(len(sentences)), key=lambda index: sentence_word_count(sentences[index]))
        words = sentences[sentence_index].split()
        if len(words) <= 2:
            break
        words.pop()
        sentences[sentence_index] = f"{' '.join(words).rstrip('.!?')}."

    if sum(sentence_word_count(sentence) for sentence in sentences) < GRADE1_WORDS_PER_PAGE[0]:
        raise ValueError('Each Grade 1 page must contain 12-22 words.')

    return ' '.join(sentences)


def validate_grade1_story(story):
    if not isinstance(story, dict):
        raise ValueError('Story must be a JSON object.')
    pages = story.get('pages')
    if not isinstance(pages, list) or not pages:
        raise ValueError('Grade 1 stories need at least one page.')
    repaired_pages = []
    for page in pages[:GRADE1_PAGE_COUNT]:
        page = dict(page) if isinstance(page, dict) else {}
        page['text'] = _repair_grade1_page_text(page.get('text'))
        repaired_pages.append(page)
    if len(pages) > GRADE1_PAGE_COUNT:
        extra_text = ' '.join(
            str(page.get('text', '')) for page in pages[GRADE1_PAGE_COUNT:]
            if isinstance(page, dict)
        )
        repaired_pages[-1]['text'] = _repair_grade1_page_text(
            f"{repaired_pages[-1]['text']} {extra_text}"
        )
    filler_pages = (
        'The child smiles at the end. It is a happy day, too.',
        'The child goes home. The kind day ends with a warm smile.',
    )
    while len(repaired_pages) < GRADE1_PAGE_COUNT:
        filler_index = len(repaired_pages) - len(pages)
        repaired_pages.append({'text': filler_pages[filler_index]})
    pages = repaired_pages
    story['pages'] = pages
    for page in pages:
        page.setdefault('highlighted_words', [])
        page.setdefault('illustration_prompt', page['text'])
    story['title'] = str(story.get('title') or '').strip() or 'A Helpful Day'
    story['character_description'] = str(
        story.get('character_description') or ''
    ).strip() or 'A friendly young learner with a warm smile.'
    if story.get('_activity_variant') not in GRADE1_ACTIVITY_VARIANTS:
        story['_activity_variant'] = 'phonics'

    text = ' '.join(page['text'] for page in pages)
    story_words = {word.casefold() for word in re.findall(r'\b[A-Za-z]+\b', text)}
    phonics_words = story.get('phonics_words')
    normalized = []
    if isinstance(phonics_words, list):
        normalized = [str(word).strip().casefold() for word in phonics_words[:GRADE1_PAGE_COUNT]]
    for page_index, page in enumerate(pages):
        page_words = {
            word.casefold() for word in re.findall(r'\b[A-Za-z]+\b', page['text'])
        }
        valid_word = (
            normalized[page_index]
            if page_index < len(normalized)
            and re.fullmatch(r'[a-z]{3,5}', normalized[page_index])
            and normalized[page_index] in page_words
            and normalized[page_index] not in normalized[:page_index]
            else None
        )
        if not valid_word:
            valid_word = next(
                (word for word in page_words if re.fullmatch(r'[a-z]{3,5}', word)
                 and word not in normalized[:page_index]),
                None,
            )
        if not valid_word:
            raise ValueError('Could not find a distinct 3-5 letter phonics word on each page.')
        if page_index < len(normalized):
            normalized[page_index] = valid_word
        else:
            normalized.append(valid_word)
    normalized = normalized[:GRADE1_PAGE_COUNT]
    story['phonics_words'] = normalized

    vocabulary_words = story.get('vocabulary_words')
    normalized_vocabulary = []
    if isinstance(vocabulary_words, list):
        normalized_vocabulary = [
            str(word).strip().casefold() for word in vocabulary_words[:GRADE1_PAGE_COUNT]
        ]
    for page_index, page in enumerate(pages):
        page_words = {
            word.casefold() for word in re.findall(r'\b[A-Za-z]+\b', page['text'])
        }
        vocabulary_word = (
            normalized_vocabulary[page_index]
            if page_index < len(normalized_vocabulary)
            and re.fullmatch(r'[a-z]{3,8}', normalized_vocabulary[page_index])
            and normalized_vocabulary[page_index] in page_words
            and normalized_vocabulary[page_index] not in normalized_vocabulary[:page_index]
            else None
        )
        if not vocabulary_word:
            vocabulary_word = next(
                (word for word in page_words
                 if re.fullmatch(r'[a-z]{3,8}', word)
                 and word not in normalized_vocabulary[:page_index]),
                None,
            )
        if not vocabulary_word:
            raise ValueError('Could not find a distinct 3-8 letter story word on each page.')
        if page_index < len(normalized_vocabulary):
            normalized_vocabulary[page_index] = vocabulary_word
        else:
            normalized_vocabulary.append(vocabulary_word)
    story['vocabulary_words'] = normalized_vocabulary

    picture_match = story.get('picture_match')
    repaired_picture_match = []
    if isinstance(picture_match, list):
        for item in picture_match:
            if not isinstance(item, dict):
                continue
            try:
                page_index = int(item['page_number']) - 1
                sentence = str(item['sentence']).strip()
            except (KeyError, TypeError, ValueError):
                continue
            if (0 <= page_index < len(pages)
                    and sentence.casefold() in pages[page_index]['text'].casefold()
                    and page_index not in {entry['page_number'] - 1 for entry in repaired_picture_match}):
                repaired_picture_match.append({'sentence': sentence, 'page_number': page_index + 1})
    for page_index, page in enumerate(pages):
        if page_index not in {entry['page_number'] - 1 for entry in repaired_picture_match}:
            sentences = _sentences(page['text'])
            if not sentences:
                raise ValueError('Every story page needs a sentence for picture matching.')
            repaired_picture_match.append({
                'sentence': sentences[0],
                'page_number': page_index + 1,
            })
    story['picture_match'] = sorted(repaired_picture_match, key=lambda item: item['page_number'])
    picture_match = story['picture_match']
    for item in picture_match:
        try:
            page_index = int(item['page_number']) - 1
            sentence = str(item['sentence']).strip()
        except (KeyError, TypeError, ValueError):
            raise ValueError('Each picture-match item needs a sentence and page number.')
        if not 0 <= page_index < len(pages) or sentence.casefold() not in pages[page_index]['text'].casefold():
            raise ValueError('Picture-match sentences must be copied from their referenced page.')
        item['page_number'] = page_index + 1
    if len({item['page_number'] for item in picture_match}) != 3:
        raise ValueError('Picture-match items must cover all three pages.')

    for page in pages:
        words = {word.casefold() for word in re.findall(r'\b[A-Za-z]+\b', page['text'])}
        page['highlighted_words'] = [
            word for word in normalized + normalized_vocabulary if word in words
        ]
    story['_story_words'] = sorted(story_words)
    return story


def build_grade1_activities(story, illustration_urls, vocabulary_image_urls=None):
    """Build nine single-answer activities in the canonical Grade 1 groups."""
    pages = story['pages']
    activities = []
    variant = story.get('_activity_variant', 'phonics')
    vocabulary_image_urls = vocabulary_image_urls or []
    vocabulary_pages = grade1_vocabulary_page_indices(variant)
    vocabulary_group_title = 'Story Word Detective'
    phonics_group_title = GRADE1_ACTIVITY_GROUPS[0][1]

    for index, word in enumerate(story['phonics_words']):
        word = str(word).strip().lower()
        if index in vocabulary_pages:
            if len(vocabulary_image_urls) != GRADE1_PAGE_COUNT:
                raise ValueError('Picture vocabulary activities need one image per story word.')
            options = list(dict.fromkeys(story['vocabulary_words']))
            random.shuffle(options)
            activities.append({
                'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                'skill': 'vocabulary_in_context',
                'question': 'Which word names this picture?',
                'options': {
                    'presentation': 'grade1_vocabulary',
                    'choices': options,
                    'prompt_image': vocabulary_image_urls[index],
                    'prompt_alt': f'A story object: {story["vocabulary_words"][index]}',
                    'audio_text': 'Look at the picture. Choose and say the word that names it.',
                    'instruction': 'Look at the picture. Choose and say the word that names it.',
                },
                'correct_answer': story['vocabulary_words'][index],
                'group_number': 1,
                'group_title': vocabulary_group_title,
            })
            continue
        char_index = min(max(1, len(word) // 2), len(word) - 2)
        correct_letter = word[char_index].upper()
        masked = word[:char_index] + '_' + word[char_index + 1:]
        other_letters = [letter for letter in 'AEIOUBCDFGHJKLMNPQRSTVWXYZ' if letter != correct_letter]
        random.shuffle(other_letters)
        letters = [correct_letter] + other_letters[:2]
        random.shuffle(letters)
        page_index, _, _ = _find_sentence_word(pages, word)
        activities.append({
            'activity_type': ReadingActivity.CLOZE,
            'skill': 'spelling',
            'question': f'Complete the word: {" ".join(masked.upper())}',
            'options': {
                'presentation': 'grade1_phonics', 'choices': letters,
                'audio_text': word, 'display_word': ' '.join(masked.upper()),
                'prompt_image': illustration_urls[page_index], 'prompt_alt': word,
                'instruction': 'Listen to the word and choose the missing letter.',
            },
            'correct_answer': correct_letter,
            'group_number': 1,
            'group_title': phonics_group_title,
        })

    picture_options = [
        {'image_url': illustration_urls[index], 'alt': str(page.get('illustration_prompt') or page['text'])[:180],
         'value': f'Picture {index + 1}', 'label': f'Picture {index + 1}'}
        for index, page in enumerate(pages)
    ]
    for item in story['picture_match']:
        options = [dict(option) for option in picture_options]
        activities.append({
            'activity_type': ReadingActivity.MULTIPLE_CHOICE,
            'skill': 'literal_comprehension',
            'question': item['sentence'],
            'options': {
                'presentation': 'visual_choice', 'choices': options,
                'audio_text': item['sentence'],
                'instruction': 'Listen to or read the sentence, then choose the matching picture.',
            },
            'correct_answer': f"Picture {item['page_number']}",
            'group_number': 2,
            'group_title': GRADE1_ACTIVITY_GROUPS[1][1],
        })

    used_words = set()
    candidates = list(story['phonics_words'])
    for page_index, page in enumerate(pages):
        found = None
        for word in candidates:
            if word.casefold() in used_words:
                continue
            found = _find_sentence_word([page], word)
            if found:
                used_words.add(word.casefold())
                break
        if not found:
            raise ValueError('Could not build three story sentence-completion items.')
        _, sentence, match = found
        answer = match.group(0)
        question = sentence[:match.start()] + '........' + sentence[match.end():]
        distractor = next((word for word in candidates if word.casefold() != answer.casefold()), None)
        choices = [answer.title(), distractor.title()]
        correct = answer.title()
        random.shuffle(choices)
        activities.append({
            'activity_type': ReadingActivity.MULTIPLE_CHOICE,
            'skill': 'vocabulary_in_context',
            'question': question,
            'options': {
                'choices': choices, 'audio_text': question,
                'prompt_image': illustration_urls[page_index],
                'prompt_alt': str(page.get('illustration_prompt') or page['text'])[:180],
                'instruction': 'Listen to the sentence, then choose the missing word.',
            },
            'correct_answer': correct,
            'group_number': 3,
            'group_title': GRADE1_ACTIVITY_GROUPS[2][1],
        })
    return activities


@transaction.atomic
def save_grade1_activities(lesson, story, illustration_urls, vocabulary_image_urls=None):
    for order, activity in enumerate(
        build_grade1_activities(story, illustration_urls, vocabulary_image_urls), start=1,
    ):
        ReadingActivity.objects.create(lesson=lesson, order=order, **activity)


def story_generation_metadata(theme, retrieved, assessment_reference, story):
    return {
        'rag': {
            'theme': theme,
            'sources': [
                {'id': doc['id'], 'source': doc['source'], 'section': doc['section'],
                 'document_page': doc.get('document_page')}
                for doc in retrieved
            ],
        },
        'assessment_structure': assessment_reference,
        'activity_variant': story.get('_activity_variant', 'phonics'),
        'validated_page_word_counts': [_word_count(page['text']) for page in story['pages']],
        'phonics_words': story['phonics_words'],
        'vocabulary_words': story['vocabulary_words'],
        'picture_match_count': len(story['picture_match']),
    }
