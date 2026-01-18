import os
import re
import json
import asyncio
import time
from urllib.parse import urlparse
from src.core.config import get_artifacts_dir

def inject_image_attributions(html_content: str, image_pool: list) -> str:
    """
    Finds <img> tags in HTML, and if they match an image from the pool,
    wraps them in a container and adds attribution.
    """
    if not image_pool:
        return html_content
        
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Create a lookup for image data by URL
        image_map = {img['url']: img for img in image_pool}
        
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src')
            if src in image_map:
                img_data = image_map[src]
                
                # Add class to image
                img_tag['class'] = img_tag.get('class', []) + ['inline-image']
                
                # Create container
                container = soup.new_tag('div', attrs={'class': 'inline-image-container'})
                img_tag.wrap(container)
                
                # Create attribution
                attr_div = soup.new_tag('div', attrs={'class': 'inline-attribution'})
                attr_div.append("Image: ")
                
                attr_link = soup.new_tag('a', href=img_data['attribution_url'], target='_blank')
                attr_link.string = img_data['attribution_name']
                attr_div.append(attr_link)
                
                container.append(attr_div)
                
        return str(soup)
    except Exception as e:
        print(f"Error injecting attributions: {e}")
        return html_content

def save_report_artifact(report_md: str, query: str, project_id: str, notes: list, images: list = None):
    """
    Common utility to generate and save the research report HTML.
    Returns artifact metadata.
    """
    if images is None:
        images = []
    # 1. Format sources for HTML
    sources_html = ""
    for note in notes:
        url = note.url
        title = note.title or "Untitled Source"
        domain = urlparse(url).netloc.replace("www.", "")
        
        sources_html += f"""
        <a href="{url}" class="source-item" target="_blank">
            <div class="source-domain">{domain}</div>
            <h4 class="source-title">{title}</h4>
            <div class="source-url">{url}</div>
        </a>
        """
    
    # 2. Extract title and convert markdown to HTML
    try:
        import markdown
        
        # Extract title from Markdown (looking for the first # Title)
        title_match = re.search(r'^#\s*(.*)', report_md, re.MULTILINE)
        display_title = query # Fallback
        
        if title_match:
            display_title = title_match.group(1).strip()
            # Clean the title of common prefixes
            display_title = re.sub(r'^Deep Research Report:\s*', '', display_title, flags=re.IGNORECASE)
            # Remove the title line from markdown to avoid double title in HTML
            report_md = re.sub(r'^#\s*.*', '', report_md, count=1, flags=re.MULTILINE).strip()
            
        # 2a. Remove LLM-generated Sources section to avoid duplication
        report_md = re.sub(r'(?i)^#+\s*(Sources|References|Bibliography).*$', '', report_md, flags=re.MULTILINE|re.DOTALL).strip()
        
        # 2b. Global Citation Normalizer
        # The AI now writes [Title](url). We want to convert to [1] and build a bibliography.
        
        # Track unique URLs to assign IDs
        url_to_id = {}
        next_id = 1
        references = []
        
        def replace_citation(match):
            nonlocal next_id
            text = match.group(1).replace('\n', ' ').strip()
            url = match.group(2).strip()
            
            # Normalize URL (basic)
            if url.endswith("/"): url = url[:-1]
            
            if url not in url_to_id:
                url_to_id[url] = next_id
                # Use text as title if reasonable length, else cleaned URL or "Source"
                title = text if len(text) < 100 else "Source"
                references.append({'id': next_id, 'url': url, 'title': title})
                next_id += 1
            
            ref_id = url_to_id[url]
            return f" [{ref_id}]"

        # Regex to find markdown links: [text](url)
        # We need to be careful not to match images ![text](url)
        # So we use negative lookbehind (?<!!)
        report_md = re.sub(r'(?<!\!)\[([^\]]+)\]\(([^)]+)\)', replace_citation, report_md)
        
        # 2c. Append References Section
        if references:
            report_md += "\n\n## References\n\n"
            for ref in references:
                domain = urlparse(ref['url']).netloc.replace("www.", "")
                report_md += f"[{ref['id']}] **{ref['title']}** - [{domain}]({ref['url']})\n\n"
                
        report_html_body = markdown.markdown(report_md, extensions=['fenced_code', 'tables'])
        
        # Post-process for inline images
        report_html_body = inject_image_attributions(report_html_body, images)
        
    except ImportError:
        display_title = query
        report_html_body = report_md.replace("\n", "<br>") # Fallback

    # 3. Load template
    template_path = os.path.join(os.path.dirname(__file__), "report_template.html")
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_template.html")

    with open(template_path, "r") as f:
        template = f.read()
    
    final_html = template.replace("{{title}}", display_title)
    final_html = final_html.replace("{{subtitle}}", f"Research report on {query}")
    final_html = final_html.replace("{{content}}", report_html_body)
    final_html = final_html.replace("{{sources}}", sources_html)
    
    # 4. Save artifact
    timestamp = int(time.time())
    research_folder = f"research_{timestamp}"
    
    base_artifacts = get_artifacts_dir()
    artifact_dir = os.path.join(base_artifacts, project_id, "deepresearch", research_folder)
    os.makedirs(artifact_dir, exist_ok=True)
    
    report_filename = "index.html"
    report_path = os.path.join(artifact_dir, report_filename)
    
    with open(report_path, "w") as f:
        f.write(final_html)

    # 4b. Generate PDF
    pdf_filename = "report.pdf"
    pdf_path = os.path.join(artifact_dir, pdf_filename)
    pdf_generated = False
    
    try:
        import weasyprint
        # Convert HTML to PDF
        # We use empty list for stylesheets to force it to use inline styles from our template? 
        # Actually our template has <style> which WeasyPrint parses.
        weasyprint.HTML(string=final_html).write_pdf(pdf_path)
        pdf_generated = True
        print(f"[DeepResearch] PDF generated at {pdf_path}")
    except Exception as e:
        print(f"[DeepResearch] PDF generation failed: {e}")
        # Not a critical failure, we still have HTML
    
    # 5. Return metadata
    # We prefer PDF if available, otherwise HTML
    if pdf_generated:
         return {
            "filename": pdf_filename,
            "path": pdf_path,
            "language": "pdf", # 'pdf' isn't a language really, but used for mime type inference or UI display logic
            "type": "research_report"
        }
    else:
        return {
            "filename": report_filename,
            "path": report_path,
            "language": "html",
            "type": "research_report"
        }
