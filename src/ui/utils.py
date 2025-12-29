import re
import html

def markdown_to_pango(text):
    """
    Converts basic Markdown to Pango Markup.
    Handles cases to avoid nested/broken tags.
    """
    if not text:
        return ""

    try:
        # Escape HTML special characters first
        text = html.escape(text)

        # Process PLAN blocks - strip tags and add simple header
        def format_plan(match):
            plan_content = match.group(1).strip()
            return f'<b>Implementation Plan</b>\n\n{plan_content}'
        
        text = re.sub(r'\[PLAN\](.*?)\[/PLAN\]', format_plan, text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'\[PLAN\](.*?)$', format_plan, text, flags=re.DOTALL | re.IGNORECASE)

        # Code blocks first (before inline processing) - remove content to protect it
        code_blocks = []
        def save_code_block(match):
            code_blocks.append(match.group(1))
            return f'XX_CODEBLOCK_{len(code_blocks)-1}_XX'
        
        text = re.sub(r'```(.*?)```', save_code_block, text, flags=re.DOTALL)
        
        # Inline code - also protect it
        inline_codes = []
        def save_inline_code(match):
            inline_codes.append(match.group(1))
            return f'XX_INLINECODE_{len(inline_codes)-1}_XX'
        
        text = re.sub(r'`([^`]+)`', save_inline_code, text)

        # Bold (before italic to avoid conflicts with single asterisks)
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__([^_]+)__', r'<b>\1</b>', text)

        # Italic - be more careful with underscores (only match word-bounded)
        text = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'<i>\1</i>', text)
        
        # Restore code blocks
        for i, code in enumerate(code_blocks):
            text = text.replace(f'XX_CODEBLOCK_{i}_XX', f'<tt>{code}</tt>')
        
        # Restore inline code
        for i, code in enumerate(inline_codes):
            text = text.replace(f'XX_INLINECODE_{i}_XX', f'<tt>{code}</tt>')

        return text
    except Exception as e:
        # On any parsing error, return escaped plain text
        print(f"[DEBUG markdown_to_pango] Error: {e}")
        return html.escape(text) if text else ""
