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
        return html.escape(text) if text else ""

def parse_markdown_segments(text):
    """
    Parses markdown text into segments of 'text' and 'code'.
    Returns a list of dicts:
    [
      {'type': 'text', 'content': '...'},
      {'type': 'code', 'content': '...', 'lang': '...'}
    ]
    """
    if not text:
        return []
        
    segments = []
    
    # Regex to match code blocks: ```lang\ncode\n```
    # Captures: 1=lang (any chars until newline), 2=code
    # Fixed: Changed (\w*) to ([^\n]*) to handle trailing spaces or complex lang strings
    pattern = r'```([^\n]*)\n(.*?)```'
    
    last_idx = 0
    for match in re.finditer(pattern, text, re.DOTALL):
        # Add text before the code block
        start, end = match.span()
        if start > last_idx:
            segments.append({
                'type': 'text',
                'content': text[last_idx:start]
            })
            
        # Add the code block
        segments.append({
            'type': 'code',
            'lang': match.group(1).strip() or "text",
            'content': match.group(2) # Content inside backticks
        })
        
        last_idx = end
        
    # Add remaining text
    if last_idx < len(text):
        segments.append({
            'type': 'text',
            'content': text[last_idx:]
        })
        
    return segments
