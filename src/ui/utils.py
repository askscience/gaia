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
    Parses markdown text into segments of 'text', 'code', and 'image'.
    Returns a list of dicts:
    [
      {'type': 'text', 'content': '...'},
      {'type': 'code', 'content': '...', 'lang': '...'},
      {'type': 'image', 'alt': '...', 'url': '...'}
    ]
    """
    if not text:
        return []
        
    segments = []
    
    # Combined regex to match:
    # 1. Wallpaper Grid: [WALLPAPER_GRID]...[/WALLPAPER_GRID]
    # 2. Code: ```lang\ncode\n```
    # 3. Image: ![alt](url)
    
    grid_pattern = r'\[WALLPAPER_GRID\](.*?)\[/WALLPAPER_GRID\]'
    code_pattern = r'```([^\n]*)\n(.*?)```'
    image_pattern = r'!\[([^\]]*)\]\s*\(([^)]+)\)'
    
    current_idx = 0
    
    while current_idx < len(text):
        # Search for all patterns
        grid_match = re.search(grid_pattern, text[current_idx:], re.DOTALL)
        code_match = re.search(code_pattern, text[current_idx:], re.DOTALL)
        image_match = re.search(image_pattern, text[current_idx:])
        
        # Calculate absolute positions (inf if not found)
        grid_start = grid_match.start() + current_idx if grid_match else float('inf')
        code_start = code_match.start() + current_idx if code_match else float('inf')
        image_start = image_match.start() + current_idx if image_match else float('inf')
        
        # No matches left
        if grid_start == float('inf') and code_start == float('inf') and image_start == float('inf'):
            segments.append({'type': 'text', 'content': text[current_idx:]})
            break
            
        # Find the earliest match
        earliest = min(grid_start, code_start, image_start)
        
        # Add text before match
        if earliest > current_idx:
            segments.append({'type': 'text', 'content': text[current_idx:earliest]})
            
        if grid_start == earliest:
            segments.append({
                'type': 'wallpaper_grid',
                'content': grid_match.group(1) # JSON content
            })
            current_idx = grid_match.end() + current_idx
            
        elif code_start == earliest:
            segments.append({
                'type': 'code', 
                'lang': code_match.group(1).strip() or "text",
                'content': code_match.group(2)
            })
            current_idx = code_match.end() + current_idx
            
        elif image_start == earliest:
            segments.append({
                'type': 'image',
                'alt': image_match.group(1),
                'url': image_match.group(2)
            })
            current_idx = image_match.end() + current_idx
            
    return segments
