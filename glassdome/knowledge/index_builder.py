"""
RAG Index Builder

Indexes all project knowledge:
- Documentation (markdown files)
- Code (Python files with docstrings)
- Session logs
- Git commit messages
- Configuration examples

Uses sentence-transformers for embeddings + FAISS for vector storage.
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
        
    def index_all(self):
        """Index all knowledge sources"""
        print("\n" + "="*70)
        print("BUILDING RAG INDEX")
        print("="*70)
        
        # Index different knowledge sources
        self._index_markdown_docs()
        self._index_python_code()
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
        """Index Python code with docstrings"""
        print("\n🐍 Indexing Python code...")
        
        py_files = list(self.project_root.rglob("glassdome/**/*.py"))
        print(f"   Found {len(py_files)} Python files")
        
        for py_file in py_files:
            if '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract classes and functions with docstrings
                chunks = self._extract_code_chunks(content, py_file.name)
                
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
    
    def _extract_code_chunks(self, content: str, filename: str) -> List[Dict]:
        """Extract functions/classes with docstrings"""
        chunks = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for class or function definitions
            if line.strip().startswith('class ') or line.strip().startswith('def '):
                # Extract definition + docstring
                chunk_lines = [line]
                i += 1
                
                # Get docstring if exists
                in_docstring = False
                while i < len(lines):
                    if '"""' in lines[i] or "'''" in lines[i]:
                        chunk_lines.append(lines[i])
                        if in_docstring:
                            i += 1
                            break
                        in_docstring = True
                    elif in_docstring:
                        chunk_lines.append(lines[i])
                    else:
                        break
                    i += 1
                
                if len(chunk_lines) > 1:  # Has docstring
                    chunks.append({
                        'content': '\n'.join(chunk_lines),
                        'metadata': {
                            'filename': filename,
                            'type': 'class' if 'class ' in chunk_lines[0] else 'function'
                        }
                    })
            else:
                i += 1
        
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

