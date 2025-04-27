def colorize_gay(text: str) -> str:
    # ANSI цвета для радуги
    colors = ['🟥', '🟧', '🟨', '🟩', '🟦', '🟪', '⬛']

    colored_text = ""
    for i, char in enumerate(text):
        color = colors[i % len(colors)]
        colored_text += f"{color}{char}"

    return colored_text