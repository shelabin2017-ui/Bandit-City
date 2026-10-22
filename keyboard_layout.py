"""VK keyboard layout helpers: normalize rows and paginate without dropping actions."""
from typing import Iterable, List


def normalize_rows(rows, max_buttons_per_row=2, max_label_length=40):
    """Convert arbitrary keyboard row input to VK-safe rows without losing labels."""
    clean = []
    for row in rows or []:
        if isinstance(row, str):
            row = [row]
        labels = []
        for value in row:
            if value is None or value == "":
                continue
            label = str(value)
            if len(label) > max_label_length:
                # Keep the VK label limit explicit; log at the integration layer.
                label = label[:max_label_length]
            labels.append(label)
        for index in range(0, len(labels), max_buttons_per_row):
            clean.append(labels[index:index + max_buttons_per_row])
    return clean


def paginate_rows(rows, page_size=8):
    """Return pages with up to page_size content rows and a pinned footer row.

    The final input row is treated as navigation/footer and appears on every
    page. Pagination controls occupy one additional row, keeping each VK
    keyboard at no more than 10 rows.
    """
    normalized = normalize_rows(rows)
    if len(normalized) <= 10:
        return [normalized]

    footer = normalized[-1:]
    content = normalized[:-1]
    size = max(1, min(int(page_size), 8))
    chunks = [content[i:i + size] for i in range(0, len(content), size)] or [[]]
    total = len(chunks)
    pages = []
    for index, chunk in enumerate(chunks):
        page = list(chunk)
        controls = []
        if index > 0:
            controls.append("⬅️ Назад меню")
        if index < total - 1:
            controls.append("➡️ Далее меню")
        if controls:
            page.append(controls)
        page.extend(footer)
        pages.append(page)
    return pages
