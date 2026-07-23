from api.models import Lesson, PronunciationWord, StoryPage, VisualActivityItem


def run():
    lesson = Lesson.objects.get(title="Lerato's Fruit Basket")
    lesson.thumbnail_image = "/static/img/lerato/Fruits.avif"
    lesson.save(update_fields=["thumbnail_image"])

    story_pages = [
        (1, "/static/img/lerato/story_page_1.png", "voiceover:page1", "apple,banana,orange"),
        (2, "/static/img/lerato/story_page_2.png", "voiceover:page2", "mango,market"),
        (3, "/static/img/lerato/story_page_3.png", "voiceover:page3", "fruit,healthy,strong"),
    ]
    for page_number, image_url, audio_url, highlighted_words in story_pages:
        StoryPage.objects.filter(lesson=lesson, page_number=page_number).update(
            image_url=image_url,
            audio_url=audio_url,
            highlighted_words=highlighted_words,
        )

    fruit_images = {
        "Apple": "/static/img/lerato/fruit_apple.png",
        "Banana": "/static/img/lerato/fruit_banana.png",
        "Orange": "/static/img/lerato/fruit_orange_user.webp",
        "Mango": "/static/img/lerato/fruit_mango_user.webp",
    }
    for word, image_url in fruit_images.items():
        VisualActivityItem.objects.filter(lesson=lesson, correct_word=word).update(image_url=image_url)
        PronunciationWord.objects.filter(lesson=lesson, word=word).update(
            image_url=image_url,
            english_audio=f"voiceover:{word.lower()}-english",
            isizulu_audio=f"voiceover:{word.lower()}-zulu",
        )

    print(f"Updated Lerato lesson assets for lesson {lesson.id}")


run()
