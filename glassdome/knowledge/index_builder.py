"""
RAG Index Builder

Indexes all project knowledge:
- Documentation (markdown files)
- Code (ALL Python files - full implementations)
- Configuration files (YAML, JSON, TOML, etc.)
- Session logs
- Git commit messages

Uses sentence-transformers for embeddings + FAISS for vector storage.

Security: Excludes .env files and other sensitive files.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import hashlib

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
except ImportError:
    print("WARNING: sentence-transformers or faiss not installed")
    print("Install with: pip install sentence-transformers faiss-cpu")


class IndexBuilder:
    """Build and manage RAG knowledge index"""
    
    def __init__(
        self,
        project_root: str = "/home/nomad/glassdome",
        model_name: str = "all-MiniLM-L6-v2",  # Fast, 384 dim
        index_path: str = None
    ):
        self.project_root = Path(project_root)
        self.model_name = model_name
        self.index_path = Path(index_path) if index_path else self.project_root / ".rag_index"
        
        # Create index directory
        self.index_path.mkdir(exist_ok=True)
        
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        self.documents = []  # Store doc metadata
        self.embeddings = []  # Store vectors
    
    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from indexing"""
        path_str = str(file_path)
        
        # Exclude sensitive files
        if '.env' in path_str or file_path.name == '.env':
            return True
        
        # Exclude common sensitive patterns
        sensitive_patterns = [
            '.env',
            '.env.local',
            'secrets',
            'credentials',
            'password',
            'private_key',
            '__pycache__',
            '.pyc',
            '.git',
            'venv/',
            'node_modules/',
            '.rag_index/',  # Don't index the index itself
        ]
        
        for pattern in sensitive_patterns:
            if pattern in path_str:
                return True
        
        return False
    
    def index_all(self):
        """Index all knowledge sources"""
        print("\n" + "="*70)
        print("BUILDING RAG INDEX")
        print("="*70)
        
        # Index different knowledge sources
        self._index_markdown_docs()
        self._index_python_code()
        self._index_config_files()
        self._index_session_logs()
        self._index_git_history()
        
        # Build FAISS index
        self._build_faiss_index()
        
        # Save metadata
        self._save_metadata()
        
        print(f"\n✅ Index built successfully!")
        print(f"   Total documents: {len(self.documents)}")
        print(f"   Index location: {self.index_path}")
        print("="*70)
        
    def _index_markdown_docs(self):
        """Index all markdown documentation"""
        print("\n📚 Indexing markdown documentation...")
        
        docs_dir = self.project_root / "docs"
        if not docs_dir.exists():
            print("   ⚠️  docs/ directory not found")
            return
            
        md_files = list(docs_dir.rglob("*.md"))
        print(f"   Found {len(md_files)} markdown files")
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split into chunks (by section headers)
                chunks = self._chunk_markdown(content, md_file.name)
                
                for chunk in chunks:
                    self._add_document(
                        content=chunk['content'],
                        source=str(md_file.relative_to(self.project_root)),
                        doc_type="markdown",
                        metadata=chunk['metadata']
                    )
                    
            except Exception as e:
                print(f"   ⚠️  Error indexing {md_file.name}: {e}")
        
        print(f"   ✅ Indexed {len([d for d in self.documents if d['type'] == 'markdown'])} markdown chunks")
        
    def _chunk_markdown(self, content: str, filename: str) -> List[Dict]:
        """Split markdown into chunks by headers"""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_header = "Introduction"
        
        for line in lines:
            if line.startswith('#'):
                # New section
                if current_chunk:
                    chunks.append({
                        'content': '\n'.join(current_chunk),
                        'metadata': {
                            'section': current_header,
                            'filename': filename
                        }
                    })
                current_chunk = [line]
                current_header = line.lstrip('#').strip()
            else:
                current_chunk.append(line)
        
        # Add last chunk
        if current_chunk:
            chunks.append({
                'content': '\n'.join(current_chunk),
                'metadata': {
                    'section': current_header,
                    'filename': filename
                }
            })
        
        return chunks
    
    def _index_python_code(self):
        """Index ALL Python code (full implementations, not just docstrings)"""
        print("\n🐍 Indexing Python code...")
        
        # Find all Python files
        py_files = list(self.project_root.rglob("*.py"))
        
        # Also include scripts directory
        scripts_dir = self.project_root / "scripts"
        if scripts_dir.exists():
            py_files.extend(scripts_dir.rglob("*.py"))
        
        # Filter out excluded files
        py_files = [f for f in py_files if not self._should_exclude_file(f)]
        
        print(f"   Found {len(py_files)} Python files")
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Chunk by functions/classes (full implementation, not just docstrings)
                chunks = self._chunk_python_code(content, py_file.name)
                
                for chunk in chunks:
                    self._add_document(
                        content=chunk['content'],
                        source=str(py_file.relative_to(self.project_root)),
                        doc_type="code",
                        metadata=chunk['metadata']
                    )
                    
            except Exception as e:
                print(f"   ⚠️  Error indexing {py_file.name}: {e}")
        
        print(f"   ✅ Indexed {len([d for d in self.documents if d['type'] == 'code'])} code chunks")
    
    def _chunk_python_code(self, content: str, filename: str) -> List[Dict]:
        """Chunk Python code by functions and classes (full implementation)"""
        chunks = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for class or function definitions
            if line.strip().startswith('class ') or line.strip().startswith('def '):
                # Extract full definition (not just docstring)
                chunk_lines = []
                indent_level = len(line) - len(line.lstrip())
                
                # Add the definition line
                chunk_lines.append(line)
                i += 1
                
                # Collect all lines at same or deeper indentation
                while i < len(lines):
                    current_line = lines[i]
                    
                    # Empty line - include it
                    if not current_line.strip():
                        chunk_lines.append(current_line)
                        i += 1
                        continue
                    
                    # Check indentation
                    current_indent = len(current_line) - len(current_line.lstrip())
                    
                    # If we hit a line at same or less indentation (and not empty), we're done
                    if current_indent <= indent_level and current_line.strip():
                        break
                    
                    chunk_lines.append(current_line)
                    i += 1
                
                # Only add if chunk has content
                if len(chunk_lines) > 1:
                    chunks.append({
                        'content': '\n'.join(chunk_lines),
                        'metadata': {
                            'filename': filename,
                            'type': 'class' if 'class ' in chunk_lines[0] else 'function',
                            'name': self._extract_name(chunk_lines[0])
                        }
                    })
            else:
                i += 1
        
        # If no functions/classes found, chunk by logical blocks (imports, module-level code)
        if not chunks:
            # Chunk by logical sections
            chunks = self._chunk_by_sections(content, filename)
        
        return chunks
    
    def _extract_name(self, definition_line: str) -> str:
        """Extract function/class name from definition line"""
        if 'class ' in definition_line:
            name = definition_line.split('class ')[1].split('(')[0].split(':')[0].strip()
        elif 'def ' in definition_line:
            name = definition_line.split('def ')[1].split('(')[0].strip()
        else:
            name = "unknown"
        return name
    
    def _chunk_by_sections(self, content: str, filename: str) -> List[Dict]:
        """Chunk code by logical sections (imports, constants, etc.)"""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_section = "module"
        
        for line in lines:
            stripped = line.strip()
            
            # Detect section boundaries
            if stripped.startswith('import ') or stripped.startswith('from '):
                if current_chunk and current_section != "imports":
                    chunks.append({
                        'content': '\n'.join(current_chunk),
                        'metadata': {'filename': filename, 'section': current_section}
                    })
                    current_chunk = []
                current_section = "imports"
            elif stripped.startswith('#'):
                # Comment block
                if current_chunk and not current_chunk[0].strip().startswith('#'):
                    chunks.append({
                        'content': '\n'.join(current_chunk),
                        'metadata': {'filename': filename, 'section': current_section}
                    })
                    current_chunk = []
                current_section = "comments"
            
            current_chunk.append(line)
        
        # Add last chunk
        if current_chunk:
            chunks.append({
                'content': '\n'.join(current_chunk),
                'metadata': {'filename': filename, 'section': current_section}
            })
        
        return chunks
    
    def _index_session_logs(self):
        """Index session logs and critical lessons"""
        print("\n📝 Indexing session logs...")
        
        logs_dir = self.project_root / "docs" / "session_logs"
        if not logs_dir.exists():
            print("   ⚠️  session_logs/ directory not found")
            return
        
        log_files = list(logs_dir.glob("*.md"))
        print(f"   Found {len(log_files)} log files")
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Critical lessons are especially important
                chunks = self._chunk_markdown(content, log_file.name)
                
                for chunk in chunks:
                    self._add_document(
                        content=chunk['content'],
                        source=str(log_file.relative_to(self.project_root)),
                        doc_type="session_log",
                        metadata=chunk['metadata']
                    )
                    
            except Exception as e:
                print(f"   ⚠️  Error indexing {log_file.name}: {e}")
        
        print(f"   ✅ Indexed {len([d for d in self.documents if d['type'] == 'session_log'])} session log chunks")
    
    def _index_config_files(self):
        """Index configuration files (YAML, JSON, TOML)"""
        print("\n⚙️  Indexing configuration files...")
        
        config_extensions = ['.yaml', '.yml', '.json', '.toml', '.ini', '.conf']
        config_files = []
        
        for ext in config_extensions:
            config_files.extend(self.project_root.rglob(f"*{ext}"))
        
        # Filter out excluded files
        config_files = [f for f in config_files if not self._should_exclude_file(f)]
        
        # Exclude node_modules, venv, etc.
        config_files = [
            f for f in config_files 
            if 'node_modules' not in str(f) 
            and 'venv' not in str(f)
            and '.git' not in str(f)
        ]
        
        print(f"   Found {len(config_files)} config files")
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Skip if looks like it contains secrets
                if any(keyword in content.lower() for keyword in ['password', 'secret', 'api_key', 'token']):
                    # Check if it's a template/example file
                    if 'example' not in config_file.name.lower() and 'template' not in config_file.name.lower():
                        print(f"   ⚠️  Skipping {config_file.name} (may contain secrets)")
                        continue
                
                self._add_document(
                    content=content,
                    source=str(config_file.relative_to(self.project_root)),
                    doc_type="config",
                    metadata={
                        'filename': config_file.name,
                        'extension': config_file.suffix
                    }
                )
                
            except Exception as e:
                print(f"   ⚠️  Error indexing {config_file.name}: {e}")
        
        print(f"   ✅ Indexed {len([d for d in self.documents if d['type'] == 'config'])} config chunks")
    
    def _index_git_history(self):
        """Index git commit messages for context"""
        print("\n🔀 Indexing git history...")
        
        try:
            import subprocess
            
            # Get last 100 commits
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%an|%ad|%s|%b', '-100'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("   ⚠️  Could not read git history")
                return
            
            commits = result.stdout.strip().split('\n')
            print(f"   Found {len(commits)} commits")
            
            for commit_line in commits:
                if not commit_line.strip():
                    continue
                    
                parts = commit_line.split('|')
                if len(parts) >= 4:
                    commit_hash = parts[0]
                    author = parts[1]
                    date = parts[2]
                    message = parts[3]
                    body = parts[4] if len(parts) > 4 else ""
                    
                    content = f"Commit: {message}\n{body}"
                    
                    self._add_document(
                        content=content,
                        source=f"git:{commit_hash[:8]}",
                        doc_type="git_commit",
                        metadata={
                            'author': author,
                            'date': date,
                            'hash': commit_hash
                        }
                    )
            
            print(f"   ✅ Indexed {len([d for d in self.documents if d['type'] == 'git_commit'])} commits")
            
        except Exception as e:
            print(f"   ⚠️  Error indexing git history: {e}")
    
    def _add_document(self, content: str, source: str, doc_type: str, metadata: Dict):
        """Add document and generate embedding"""
        if not content.strip():
            return
        
        # Generate embedding
        embedding = self.model.encode(content, convert_to_numpy=True)
        
        # Store document metadata
        doc_id = len(self.documents)
        self.documents.append({
            'id': doc_id,
            'content': content,
            'source': source,
            'type': doc_type,
            'metadata': metadata,
            'indexed_at': datetime.now().isoformat()
        })
        
        self.embeddings.append(embedding)
    
    def _build_faiss_index(self):
        """Build FAISS vector index"""
        print("\n🔍 Building FAISS index...")
        
        if not self.embeddings:
            print("   ⚠️  No embeddings to index!")
            return
        
        # Convert to numpy array
        embeddings_array = np.array(self.embeddings).astype('float32')
        
        # Create FAISS index (flat L2 distance)
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings_array)
        
        print(f"   ✅ FAISS index built with {self.index.ntotal} vectors")
        
        # Save index
        index_file = self.index_path / "faiss.index"
        faiss.write_index(self.index, str(index_file))
        print(f"   💾 Saved to {index_file}")
    
    def _save_metadata(self):
        """Save document metadata"""
        metadata_file = self.index_path / "metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump({
                'documents': self.documents,
                'model_name': self.model_name,
                'dimension': self.dimension,
                'indexed_at': datetime.now().isoformat(),
                'total_docs': len(self.documents)
            }, f, indent=2)
        
        print(f"   💾 Saved metadata to {metadata_file}")


if __name__ == "__main__":
    builder = IndexBuilder()
    builder.index_all()

