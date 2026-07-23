from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "diagrams" / "sgila_ui_flow_orderly.pdf"
KOALY = ROOT / "static" / "img" / "koaly_cutout.png"

PAGE_W, PAGE_H = landscape(A4)

COLORS = {
    "red": colors.HexColor("#ff5a66"),
    "orange": colors.HexColor("#ff9f1c"),
    "yellow": colors.HexColor("#ffd22e"),
    "green": colors.HexColor("#31ca83"),
    "cyan": colors.HexColor("#5bdad4"),
    "blue": colors.HexColor("#83a8f6"),
    "purple": colors.HexColor("#a37cf3"),
    "pink": colors.HexColor("#f77cbd"),
    "ink": colors.HexColor("#14213d"),
    "muted": colors.HexColor("#5f6b86"),
    "line": colors.HexColor("#d9e0ee"),
    "paper": colors.HexColor("#fff8ef"),
    "soft": colors.HexColor("#f8fbff"),
}


def rr(c, x, y, w, h, r, fill, stroke=None, sw=1):
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.setLineWidth(sw)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1 if stroke else 0)


def wrap_lines(value, font, size, max_width):
    words = value.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_text(c, value, x, y, size=10, color=None, font="Helvetica", max_width=None, leading=None):
    c.setFillColor(color or COLORS["ink"])
    c.setFont(font, size)
    leading = leading or size * 1.25
    if max_width:
        for line in wrap_lines(value, font, size, max_width):
            c.drawString(x, y, line)
            y -= leading
        return y
    c.drawString(x, y, value)
    return y - leading


def page_title(c, title, subtitle, page_label):
    c.setFillColor(COLORS["paper"])
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    rr(c, 34, PAGE_H - 76, 46, 46, 14, colors.HexColor("#d7f8f6"))
    rr(c, 45, PAGE_H - 65, 24, 24, 8, COLORS["yellow"])
    draw_text(c, "S", 53, PAGE_H - 58, 12, COLORS["ink"], "Helvetica-Bold")
    draw_text(c, page_label, 96, PAGE_H - 41, 9, COLORS["muted"], "Helvetica-Bold")
    draw_text(c, title, 96, PAGE_H - 63, 21, COLORS["ink"], "Helvetica-Bold")
    draw_text(c, subtitle, 96, PAGE_H - 80, 9.5, COLORS["muted"], "Helvetica-Bold", 560)

    x = 34
    y = PAGE_H - 103
    width = PAGE_W - 68
    for i, name in enumerate(["red", "orange", "yellow", "green", "cyan", "blue", "purple"]):
        rr(c, x + i * (width / 7), y, width / 7 - 7, 6, 3, COLORS[name])


def arrow(c, x1, y1, x2, y2, color, label=None):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(5)
    c.line(x1, y1, x2 - 13, y2)
    c.line(x2 - 13, y2 + 10, x2, y2)
    c.line(x2, y2, x2 - 13, y2 - 10)
    c.line(x2 - 13, y2 - 10, x2 - 13, y2 + 10)
    if label:
        rr(c, (x1 + x2) / 2 - 38, y1 + 10, 76, 16, 8, colors.white, COLORS["line"], .5)
        c.setFillColor(COLORS["ink"])
        c.setFont("Helvetica-Bold", 6.4)
        c.drawCentredString((x1 + x2) / 2, y1 + 15, label)


def down_arrow(c, x, y_top, y_bottom, color, label):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(5)
    c.line(x, y_top, x, y_bottom + 14)
    c.line(x - 10, y_bottom + 14, x, y_bottom)
    c.line(x, y_bottom, x + 10, y_bottom + 14)
    c.line(x + 10, y_bottom + 14, x - 10, y_bottom + 14)
    rr(c, x - 45, (y_top + y_bottom) / 2 - 8, 90, 16, 8, colors.white, COLORS["line"], .5)
    c.setFillColor(COLORS["ink"])
    c.setFont("Helvetica-Bold", 6.4)
    c.drawCentredString(x, (y_top + y_bottom) / 2 - 3, label)


def screen_card(c, x, y, w, h, step, role, title, subtitle, items, accent, badge_fill=None, show_koaly=False):
    rr(c, x + 5, y - 5, w, h, 15, colors.Color(.70, .76, .86, alpha=.25))
    rr(c, x, y, w, h, 15, colors.white, COLORS["line"], 1)

    c.setFillColor(colors.HexColor("#fffdf8"))
    c.rect(x, y + h - 28, w, 28, fill=1, stroke=0)
    for i, col in enumerate([COLORS["red"], COLORS["yellow"], COLORS["green"]]):
        c.setFillColor(col)
        c.circle(x + 14 + i * 14, y + h - 14, 4.2, fill=1, stroke=0)
    draw_text(c, role, x + 58, y + h - 18, 7.5, COLORS["ink"], "Helvetica-Bold")

    c.setFillColor(accent)
    c.rect(x, y + h - 34, w, 6, fill=1, stroke=0)

    side_w = 30
    c.setFillColor(colors.HexColor("#252941"))
    c.rect(x, y, side_w, h - 34, fill=1, stroke=0)
    for i, letter in enumerate(["D", "L", "A", "P"]):
        c.setFillColor(COLORS["yellow"] if i == 0 else colors.HexColor("#3c435b"))
        c.circle(x + side_w / 2, y + h - 58 - i * 25, 8, fill=1, stroke=0)
        c.setFillColor(COLORS["ink"] if i == 0 else colors.white)
        c.setFont("Helvetica-Bold", 5.7)
        c.drawCentredString(x + side_w / 2, y + h - 60 - i * 25, letter)

    body_x = x + side_w + 14
    rr(c, body_x - 4, y + 13, w - side_w - 22, h - 57, 12, COLORS["soft"])
    rr(c, body_x, y + h - 72, 28, 24, 8, badge_fill or accent)
    draw_text(c, str(step), body_x + 8, y + h - 64, 10.5, COLORS["ink"] if badge_fill != COLORS["purple"] else colors.white, "Helvetica-Bold")
    draw_text(c, title, body_x + 36, y + h - 59, 13, COLORS["ink"], "Helvetica-Bold", w - side_w - 72, 15)
    draw_text(c, subtitle, body_x, y + h - 96, 8.5, COLORS["muted"], "Helvetica-Bold", w - side_w - 40, 10.5)

    item_y = y + h - 136
    for item in items[:4]:
        rr(c, body_x, item_y, w - side_w - 45, 17, 8, colors.white, COLORS["line"], .5)
        draw_text(c, item, body_x + 8, item_y + 5, 7.2, COLORS["muted"], "Helvetica-Bold")
        item_y -= 22

    if show_koaly and KOALY.exists():
        try:
            c.drawImage(ImageReader(str(KOALY)), x + w - 52, y + 13, 38, 38, mask="auto")
        except Exception:
            pass


def overview_lane(c, y, number, title, color, points):
    rr(c, 42, y, PAGE_W - 84, 90, 18, colors.white, color, 1.4)
    rr(c, 60, y + 50, 32, 26, 9, color)
    draw_text(c, number, 69, y + 58, 10, COLORS["ink"] if title != "Parent" else colors.white, "Helvetica-Bold")
    draw_text(c, f"{title} Path", 60, y + 27, 16, COLORS["ink"], "Helvetica-Bold")
    x = 190
    step_w = 130
    for i, point in enumerate(points):
        rr(c, x, y + 23, step_w, 42, 12, colors.HexColor("#f8fbff"), COLORS["line"], .7)
        draw_text(c, point, x + 11, y + 48, 8.5, COLORS["ink"], "Helvetica-Bold", step_w - 20, 10)
        if i < len(points) - 1:
            arrow(c, x + step_w + 7, y + 44, x + step_w + 45, y + 44, color)
        x += step_w + 53


def overview_page(c):
    page_title(
        c,
        "SGILA UI Flow",
        "Readable overview of how each role moves through the desktop application.",
        "Project diagram",
    )
    draw_text(c, "Use this page for a quick explanation. Use the next pages for readable screen-by-screen detail.", 42, PAGE_H - 135, 11, COLORS["muted"], "Helvetica-Bold", 720)
    overview_lane(c, PAGE_H - 245, "01", "Learner", COLORS["yellow"], ["Open app", "Learner home", "Lesson", "Story", "Activities", "Multiplier results"])
    overview_lane(c, PAGE_H - 365, "02", "Teacher", COLORS["cyan"], ["Open app", "Class dashboard", "Learners", "Report", "Comments", "Export PDF"])
    overview_lane(c, PAGE_H - 485, "03", "Parent", COLORS["purple"], ["Open app", "Parent dashboard", "Children", "Progress", "Comments", "Download report"])
    shared_services(c, 36)
    c.showPage()


def role_page(c, role_name, subtitle, lane_color, cards):
    page_title(c, f"{role_name} Path", subtitle, "Screen-by-screen flow")

    w = 220
    h = 150
    xs = [56, 311, 566]
    y_top = PAGE_H - 292
    y_bottom = PAGE_H - 492

    for index, card in enumerate(cards):
        x = xs[index % 3]
        y = y_top if index < 3 else y_bottom
        screen_card(
            c,
            x,
            y,
            w,
            h,
            index + 1,
            card["role"],
            card["title"],
            card["subtitle"],
            card["items"],
            card["accent"],
            lane_color,
            card.get("koaly", False),
        )
        if index in [0, 1, 3, 4]:
            arrow(c, x + w + 8, y + h / 2, xs[(index % 3) + 1] - 12, y + h / 2, card["accent"], card["arrow"])
        if index == 2:
            down_arrow(c, x + w / 2, y - 15, y_bottom + h + 15, card["accent"], "continue")

    shared_services(c, 28, compact=True)
    c.showPage()


def shared_services(c, y, compact=False):
    h = 60 if compact else 72
    rr(c, 42, y, PAGE_W - 84, h, 16, colors.white, COLORS["line"], .7)
    draw_text(c, "Shared SGILA services", 60, y + h - 22, 9, COLORS["muted"], "Helvetica-Bold")
    draw_text(c, "Session auth, role routing, lesson content, scores, stars, reports, and comments all use the same learning record.", 60, y + h - 40, 10, COLORS["ink"], "Helvetica-Bold", 430)

    chips = [("Auth", "red"), ("Roles", "orange"), ("Lessons", "yellow"), ("Scores", "green"), ("Reports", "purple"), ("Comments", "pink")]
    x = 512
    for label, name in chips:
        fill = COLORS[name]
        rr(c, x, y + 20, 46, 20, 10, fill)
        draw_text(c, label, x + 9, y + 27, 6.6, colors.white if name != "yellow" else COLORS["ink"], "Helvetica-Bold")
        x += 49


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("SGILA readable UI flow")

    overview_page(c)

    learner_cards = [
        {"role": "Learner", "title": "Welcome Back", "subtitle": "Learner signs in or creates an account.", "items": ["Email address", "Password", "Continue"], "accent": COLORS["yellow"], "arrow": "role route", "koaly": True},
        {"role": "Learner", "title": "Learner Home", "subtitle": "This is not an analytics dashboard. It shows lessons, stars, and rewards.", "items": ["10 lessons", "0 stars", "Start learning"], "accent": COLORS["cyan"], "arrow": "select lesson", "koaly": True},
        {"role": "Learner", "title": "Lesson Library", "subtitle": "Learner chooses the next story activity.", "items": ["Lerato's Fruit Basket", "Open story"], "accent": COLORS["orange"], "arrow": "read story"},
        {"role": "Learner", "title": "Story Reader", "subtitle": "Learner reads, listens, and follows highlighted words.", "items": ["Story text", "Play audio", "Next page"], "accent": COLORS["blue"], "arrow": "practice"},
        {"role": "Learner", "title": "Activities", "subtitle": "Comprehension, visual matching, pronunciation, and spelling.", "items": ["Answer questions", "Match word to image", "Hear pronunciation"], "accent": COLORS["purple"], "arrow": "score"},
        {"role": "Learner", "title": "Multiplier Results", "subtitle": "Correct answers unlock stars, mascot feedback, and score boosts.", "items": ["2x multiplier", "Stars earned", "Score saved"], "accent": COLORS["pink"], "arrow": "", "koaly": True},
    ]

    teacher_cards = [
        {"role": "Teacher", "title": "Teacher Login", "subtitle": "Teacher signs in and enters the class workspace.", "items": ["School email", "Password", "Continue"], "accent": COLORS["cyan"], "arrow": "role route"},
        {"role": "Teacher", "title": "Class Dashboard", "subtitle": "Shows learner progress, class average, and low performance alerts.", "items": ["15 learners", "72% average", "4 need support"], "accent": COLORS["blue"], "arrow": "monitor"},
        {"role": "Teacher", "title": "Learner List", "subtitle": "Teacher selects a learner to inspect.", "items": ["Iyaphilisa 0/10", "Naledi 2/10", "Kamogelo 3/10"], "accent": COLORS["purple"], "arrow": "open report"},
        {"role": "Teacher", "title": "Detailed Report", "subtitle": "Scores are grouped by activity and focus area.", "items": ["Writing: vowels", "Audio: replay words", "Comprehension"], "accent": COLORS["pink"], "arrow": "comment"},
        {"role": "Teacher", "title": "Teacher Notes", "subtitle": "Teacher sends comments and reminders to parents.", "items": ["Add parent comment", "Send note"], "accent": COLORS["orange"], "arrow": "export"},
        {"role": "Teacher", "title": "Export Report", "subtitle": "Teacher downloads or shares a learner progress report.", "items": ["Download PDF", "Share report"], "accent": COLORS["green"], "arrow": ""},
    ]

    parent_cards = [
        {"role": "Parent", "title": "Parent Login", "subtitle": "Parent signs in to view linked learner records.", "items": ["Email address", "Password", "Continue"], "accent": COLORS["purple"], "arrow": "role route"},
        {"role": "Parent", "title": "Parent Dashboard", "subtitle": "Shows child progress, alerts, and teacher messages.", "items": ["1 child", "3 alerts", "Comment waiting"], "accent": COLORS["pink"], "arrow": "choose child"},
        {"role": "Parent", "title": "Children", "subtitle": "Parent chooses which child profile to open.", "items": ["Iyaphilisa", "Grade 1", "Open profile"], "accent": COLORS["blue"], "arrow": "review"},
        {"role": "Parent", "title": "Child Profile", "subtitle": "Parent views recent lessons and stars earned.", "items": ["Latest lesson", "Stars", "Completed work"], "accent": COLORS["cyan"], "arrow": "progress"},
        {"role": "Parent", "title": "Progress Report", "subtitle": "Scores and recommended focus areas are shown clearly.", "items": ["Writing", "Audio", "Comprehension"], "accent": COLORS["green"], "arrow": "support"},
        {"role": "Parent", "title": "Comments", "subtitle": "Parent reads teacher notes and downloads the report.", "items": ["Practise vowels", "Download report"], "accent": COLORS["orange"], "arrow": ""},
    ]

    role_page(c, "Learner", "Learner journey with home screen, lesson flow, and multiplier results.", COLORS["yellow"], learner_cards)
    role_page(c, "Teacher", "Teacher journey with class dashboard, learner reports, comments, and export.", COLORS["cyan"], teacher_cards)
    role_page(c, "Parent", "Parent journey with dashboard, child progress, teacher comments, and report download.", COLORS["purple"], parent_cards)

    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
