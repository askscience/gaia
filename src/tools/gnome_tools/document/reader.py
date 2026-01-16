import os
from pypdf import PdfReader
import docx

class DocumentReader:
    def read(self, file_path: str, max_chars: int = 20000) -> str:
        """Read content from a file based on its extension."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.pdf':
                return self._read_pdf(file_path, max_chars)
            elif ext == '.docx':
                return self._read_docx(file_path, max_chars)
            else:
                return self._read_text(file_path, max_chars)
        except Exception as e:
            raise RuntimeError(f"Error reading file {file_path}: {str(e)}")

    def _read_pdf(self, path: str, max_chars: int) -> str:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            if len(text) > max_chars:
                break
        return text[:max_chars]

    def _read_docx(self, path: str, max_chars: int) -> str:
        doc = docx.Document(path)
        text = []
        current_len = 0
        for para in doc.paragraphs:
            text.append(para.text)
            current_len += len(para.text)
            if current_len > max_chars:
                break
        return "\n".join(text)

    def _read_text(self, path: str, max_chars: int) -> str:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(max_chars)
