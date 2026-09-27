"""Helpers for reports that follow the skills each lesson actually assesses."""


ASSESSMENT_META = {
    'grade3_comprehension_check': ('Comprehension check', 'C', 'Look back at the story for details that answer each question.'),
    'grade3_visual_match': ('Picture match', 'P', 'Study the story pictures and match them to what happened.'),
    'grade3_true_false': ('True or False', 'T', 'Listen closely and decide whether each statement matches the story.'),
    'grade3_word_detective': ('Word detective', 'W', 'Use the story clues to choose the word that completes each sentence.'),
    'grade3_listen_spell': ('Listen and spell', 'S', 'Listen carefully and practise spelling each story word.'),
    'grade3_word_balloon': ('Word Balloon Pop', 'B', 'Listen to each clue and find the matching story word.'),
    'literal_comprehension': ('Comprehension', 'C', 'Re-read the story and look for details that answer each question.'),
    'inference': ('Inference', 'I', 'Use story clues to explain ideas that are not stated directly.'),
    'character_motivation': ('Character understanding', 'H', 'Notice how a character feels, changes, and makes decisions.'),
    'summarising': ('Main idea', 'M', 'Retell the most important events and lesson in your own words.'),
    'vocabulary_in_context': ('Vocabulary', 'V', 'Use the sentence and story context to work out word meanings.'),
    'spelling': ('Spelling', 'S', 'Practise building and writing the target words accurately.'),
    'sequencing': ('Sequencing', 'Q', 'Put story events in the order in which they happened.'),
    'prediction': ('Prediction', 'P', 'Use story clues to predict what is likely to happen next.'),
    'fact_vs_opinion': ('Fact and opinion', 'F', 'Check whether a statement can be proved from the story.'),
    'text_to_self': ('Story connection', 'T', 'Connect the story to an experience or idea you already know.'),
    'visual_literacy': ('Visual matching', 'V', 'Look closely at each picture before choosing the matching word.'),
    'emotional_literacy': ('Feelings', 'E', 'Use actions and story clues to identify how characters feel.'),
    'cause_effect': ('Cause and effect', 'C', 'Explain what happened and what caused it to happen.'),
    'reading': ('Reading', 'R', 'Re-read the story and use its details to answer questions.'),
}

ASSESSMENT_ORDER = (
    'reading',
    'literal_comprehension',
    'inference',
    'character_motivation',
    'summarising',
    'sequencing',
    'prediction',
    'fact_vs_opinion',
    'text_to_self',
    'emotional_literacy',
    'cause_effect',
    'vocabulary_in_context',
    'visual_literacy',
    'spelling',
)


def _safe_number(value):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def assessment_row(key, values):
    label, initial, tip = ASSESSMENT_META.get(
        key,
        (key.replace('_', ' ').title(), key[:1].upper() or 'A', 'Keep practising this skill.'),
    )
    score = _safe_number((values or {}).get('score'))
    total = _safe_number((values or {}).get('total'))
    score = min(score, total) if total else 0
    pct = round((score / total) * 100) if total else 0
    return {
        'key': key,
        'label': label,
        'initial': initial,
        'tip': tip,
        'score': score,
        'total': total,
        'pct': pct,
    }


def rows_from_scores(scores):
    rows = [assessment_row(key, values) for key, values in (scores or {}).items()]
    rows = [row for row in rows if row['total']]
    order = {key: index for index, key in enumerate(ASSESSMENT_ORDER)}
    rows.sort(key=lambda row: (order.get(row['key'], len(order)), row['label']))
    return rows


def scores_for_record(record):
    if record.assessment_scores:
        scores = {
            key: dict(values or {})
            for key, values in record.assessment_scores.items()
        }
        lesson = record.lesson
        valid_skills = set(
            lesson.reading_activities.values_list('skill', flat=True)
        )
        if lesson.questions.exists() or lesson.reading_activities.exists():
            valid_skills.add('reading')
        if lesson.visual_items.exists():
            valid_skills.add('visual_literacy')
        if lesson.spelling_activities.exists():
            valid_skills.add('spelling')
        legacy_activity_skills = {
            'sequencing': lesson.sequencing_activities.exists(),
            'inference': lesson.inference_questions.exists(),
            'emotional_literacy': lesson.feelings_questions.exists(),
            'cause_effect': lesson.cause_effect_pairs.exists(),
            'summarising': lesson.theme_questions.exists(),
            'prediction': lesson.prediction_questions.exists(),
        }
        valid_skills.update(
            key for key, exists in legacy_activity_skills.items() if exists
        )
        if lesson.grade == 3:
            valid_skills.update(key for key in scores if key.startswith('grade3_'))
        scores = {
            key: values
            for key, values in scores.items()
            if key in valid_skills
        }
        if record.lesson.grade == 3:
            scores = {key: values for key, values in scores.items() if key.startswith('grade3_')}
        elif not record.lesson.sequencing_activities.exists():
            scores.pop('sequencing', None)
        return scores

    lesson = record.lesson
    reading_total = lesson.reading_activities.count() or lesson.questions.count()
    scores = {}
    if reading_total:
        scores['reading'] = {'score': record.comprehension_score, 'total': reading_total}
    visual_total = lesson.visual_items.count()
    if visual_total:
        scores['visual_literacy'] = {'score': record.visual_score, 'total': visual_total}
    spelling_total = lesson.spelling_activities.count()
    if spelling_total:
        scores['spelling'] = {'score': record.spelling_score, 'total': spelling_total}
    return scores


def rows_for_record(record):
    return rows_from_scores(scores_for_record(record))


def aggregate_rows(records):
    totals = {}
    for record in records:
        for key, values in scores_for_record(record).items():
            bucket = totals.setdefault(key, {'score': 0, 'total': 0})
            bucket['score'] += _safe_number((values or {}).get('score'))
            bucket['total'] += _safe_number((values or {}).get('total'))
    return rows_from_scores(totals)
