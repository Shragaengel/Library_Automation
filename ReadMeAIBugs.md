# AI-Generated Code: Static Bug Analysis

> Static analysis of the buggy reference code provided in the exam.
> Bugs, explanations, and fixes will be added here.
# 1 actual = reading_list.get_book_count()
actual יהיה רק קריא לפונקציה כי 
get_book_count היא אסיכרונית
פשוט להסיף await reading_list.get_book_count()
# 2 int(year_text.strip())
אין בדיקה ההאם מספר או אותיות 
year_text יכול להכיל אותיות 
int(אותיות) = ValueError
לסנן if isnumric
# 3 while len(collected) < limit:
הלולאה הפנימית יכולה לעבור את ההגבלה כי היא רצה על מספר הדפים בכל עמוד 
    for item in results:
צריך תנאי גם בלולאה הפנימית len(collected) >= limit