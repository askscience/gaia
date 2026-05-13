use regex::Regex;
use once_cell::sync::Lazy;

pub struct Segment {
    pub seg_type: SegmentType,
    pub content: String,
    pub lang: Option<String>,
    pub alt: Option<String>,
    pub url: Option<String>,
}

pub enum SegmentType {
    Text,
    Code,
    Image,
    Table,
    WallpaperGrid,
}

pub fn markdown_to_pango(text: &str) -> String {
    if text.is_empty() {
        return String::new();
    }

    let mut text = text.to_string();

    // Escape HTML special characters first
    text = text
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#39;");

    // Process headers (H1-H3) - before other processing
    static H1_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?m)^#\s+(.*?)$").unwrap());
    static H2_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?m)^##\s+(.*?)$").unwrap());
    static H3_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?m)^###\s+(.*?)$").unwrap());

    text = H1_RE
        .replace_all(&text, r#"<span size="x-large" weight="bold">$1</span>"#)
        .to_string();
    text = H2_RE
        .replace_all(&text, r#"<span size="large" weight="bold">$1</span>"#)
        .to_string();
    text = H3_RE
        .replace_all(&text, r#"<span weight="bold">$1</span>"#)
        .to_string();

    // Process PLAN blocks
    static PLAN_RE: Lazy<Regex> =
        Lazy::new(|| Regex::new(r"(?si)\[PLAN\](.*?)(?:\[/PLAN\]|$)").unwrap());

    text = PLAN_RE
        .replace_all(&text, |caps: &regex::Captures| {
            let plan_content = caps.get(1).map(|m| m.as_str().trim()).unwrap_or("");
            format!("<b>Implementation Plan</b>\n\n{plan_content}")
        })
        .to_string();

    // Save code blocks to protect them from formatting
    static CODE_BLOCK_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?s)```(.*?)```").unwrap());
    let mut code_blocks: Vec<String> = Vec::new();
    text = CODE_BLOCK_RE
        .replace_all(&text, |caps: &regex::Captures| {
            let idx = code_blocks.len();
            code_blocks.push(caps[1].to_string());
            format!("XX_CODEBLOCK_{idx}_XX")
        })
        .to_string();

    // Save inline code
    static INLINE_CODE_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"`([^`]+)`").unwrap());
    let mut inline_codes: Vec<String> = Vec::new();
    text = INLINE_CODE_RE
        .replace_all(&text, |caps: &regex::Captures| {
            let idx = inline_codes.len();
            inline_codes.push(caps[1].to_string());
            format!("XX_INLINECODE_{idx}_XX")
        })
        .to_string();

    // Bold
    static BOLD_STAR_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"\*\*([^*]+)\*\*").unwrap());
    static BOLD_UNDER_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"__([^_]+)__").unwrap());
    text = BOLD_STAR_RE.replace_all(&text, r"<b>$1</b>").to_string();
    text = BOLD_UNDER_RE.replace_all(&text, r"<b>$1</b>").to_string();

    // Italic
    static ITALIC_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?<!\w)\*([^*]+)\*(?!\w)").unwrap());
    text = ITALIC_RE.replace_all(&text, r"<i>$1</i>").to_string();

    // Restore code blocks
    for (i, code) in code_blocks.iter().enumerate() {
        text = text.replace(&format!("XX_CODEBLOCK_{i}_XX"), &format!("<tt>{code}</tt>"));
    }

    // Restore inline code
    for (i, code) in inline_codes.iter().enumerate() {
        text = text.replace(
            &format!("XX_INLINECODE_{i}_XX"),
            &format!("<tt>{code}</tt>"),
        );
    }

    text
}

pub fn parse_markdown_segments(text: &str) -> Vec<Segment> {
    if text.is_empty() {
        return Vec::new();
    }

    let mut segments: Vec<Segment> = Vec::new();

    static GRID_RE: Lazy<Regex> =
        Lazy::new(|| Regex::new(r"(?s)\[WALLPAPER_GRID\](.*?)\[/WALLPAPER_GRID\]").unwrap());
    static CODE_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(?s)```([^\n]*)\n(.*?)```").unwrap());
    static IMAGE_RE: Lazy<Regex> =
        Lazy::new(|| Regex::new(r"!\[([^\]]*)\]\s*\(([^)]+)\)").unwrap());
    static TABLE_RE: Lazy<Regex> =
        Lazy::new(|| Regex::new(r"(\|[^\n]+\|\n\|[ \t:| -]+\|(?:\n\|[^\n]+\|)*)").unwrap());

    let mut current_idx = 0;

    while current_idx < text.len() {
        let remaining = &text[current_idx..];

        let grid_match = GRID_RE.find(remaining);
        let code_match = CODE_RE.find(remaining);
        let image_match = IMAGE_RE.find(remaining);
        let table_match = TABLE_RE.find(remaining);

        let grid_start = grid_match.as_ref().map(|m| m.start()).unwrap_or(usize::MAX);
        let code_start = code_match.as_ref().map(|m| m.start()).unwrap_or(usize::MAX);
        let image_start = image_match
            .as_ref()
            .map(|m| m.start())
            .unwrap_or(usize::MAX);
        let table_start = table_match
            .as_ref()
            .map(|m| m.start())
            .unwrap_or(usize::MAX);

        let earliest = grid_start.min(code_start).min(image_start).min(table_start);

        if earliest == usize::MAX {
            segments.push(Segment {
                seg_type: SegmentType::Text,
                content: remaining.to_string(),
                lang: None,
                alt: None,
                url: None,
            });
            break;
        }

        if earliest > 0 {
            segments.push(Segment {
                seg_type: SegmentType::Text,
                content: remaining[..earliest].to_string(),
                lang: None,
                alt: None,
                url: None,
            });
        }

        if earliest == grid_start {
            let m = grid_match.unwrap();
            let content = GRID_RE
                .captures(&remaining[earliest..])
                .and_then(|caps| caps.get(1))
                .map(|m| m.as_str().to_string())
                .unwrap_or_default();
            segments.push(Segment {
                seg_type: SegmentType::WallpaperGrid,
                content,
                lang: None,
                alt: None,
                url: None,
            });
            current_idx += m.end();
        } else if earliest == code_start {
            let m = code_match.unwrap();
            let lang = CODE_RE
                .captures(&remaining[earliest..])
                .and_then(|caps| caps.get(1))
                .map(|m| m.as_str().trim().to_string())
                .filter(|s| !s.is_empty())
                .unwrap_or_else(|| "text".to_string());
            let content = CODE_RE
                .captures(&remaining[earliest..])
                .and_then(|caps| caps.get(2))
                .map(|m| m.as_str().to_string())
                .unwrap_or_default();
            segments.push(Segment {
                seg_type: SegmentType::Code,
                content,
                lang: Some(lang),
                alt: None,
                url: None,
            });
            current_idx += m.end();
        } else if earliest == image_start {
            let m = image_match.unwrap();
            let alt = IMAGE_RE
                .captures(&remaining[earliest..])
                .and_then(|caps| caps.get(1))
                .map(|m| m.as_str().to_string());
            let url = IMAGE_RE
                .captures(&remaining[earliest..])
                .and_then(|caps| caps.get(2))
                .map(|m| m.as_str().to_string());
            segments.push(Segment {
                seg_type: SegmentType::Image,
                content: String::new(),
                lang: None,
                alt,
                url,
            });
            current_idx += m.end();
        } else {
            let m = table_match.unwrap();
            let content = remaining[earliest..earliest + m.len()].to_string();
            segments.push(Segment {
                seg_type: SegmentType::Table,
                content,
                lang: None,
                alt: None,
                url: None,
            });
            current_idx += m.end();
        }
    }

    segments
}
