import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from redis import Redis
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer
import json
import time
import threading
from datetime import datetime

class AIRecommendationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Recommendation Engine with Semantic Caching")
        self.root.geometry("1200x700")
        self.root.configure(bg="#f0f2f5")
        
        # Initialize connections
        self.redis = Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            socket_connect_timeout=3
        )
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Setup UI and data
        self.setup_ui()
        self.load_sample_data()
        self.start_performance_monitor()

    def setup_ui(self):
        """Configure the user interface"""
        # Configure styles
        style = ttk.Style()
        style.configure("Custom.Treeview", 
                      font=("Helvetica", 11),
                      rowheight=28,
                      background="#ffffff",
                      fieldbackground="#ffffff")
        style.configure("Custom.Treeview.Heading", 
                       font=("Helvetica", 12, "bold"),
                       background="#4a90e2",
                       foreground="white")
        style.map("Custom.Treeview", 
                 background=[("selected", "#357ebd")],
                 foreground=[("selected", "white")])

        # Header Frame
        header_frame = tk.Frame(self.root, bg="#2d3e50", padx=20, pady=15)
        header_frame.pack(fill="x")
        
        # Title Label
        tk.Label(
            header_frame,
            text="AI Recommendation Engine",
            font=("Helvetica", 18, "bold"),
            fg="white",
            bg="#2d3e50"
        ).pack(side="left")

        # Metrics Frame
        metrics_frame = tk.Frame(header_frame, bg="#2d3e50")
        metrics_frame.pack(side="right")
        
        self.cache_hits_var = tk.StringVar(value="Cache Hits: 0")
        self.query_time_var = tk.StringVar(value="Latency: 0ms")
        
        tk.Label(
            metrics_frame,
            textvariable=self.cache_hits_var,
            fg="#a3d9ff",
            bg="#2d3e50",
            font=("Helvetica", 10)
        ).pack(side="left", padx=10)
        
        tk.Label(
            metrics_frame,
            textvariable=self.query_time_var,
            fg="#a3d9ff",
            bg="#2d3e50",
            font=("Helvetica", 10)
        ).pack(side="left")

        # Main Content Frame
        main_frame = tk.Frame(self.root, bg="#f0f2f5")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Left Panel - Search and Controls
        left_panel = tk.Frame(main_frame, bg="#ffffff", bd=2, relief="groove")
        left_panel.pack(side="left", fill="y", padx=(0, 10))

        # Search Frame
        search_frame = tk.Frame(left_panel, bg="#ffffff", padx=10, pady=10)
        search_frame.pack(fill="x")
        
        tk.Label(
            search_frame,
            text="Search Query:",
            font=("Helvetica", 11),
            bg="#ffffff"
        ).pack(anchor="w")
        
        self.search_entry = tk.Entry(
            search_frame,
            font=("Helvetica", 12),
            width=40
        )
        self.search_entry.pack(fill="x", pady=5)
        self.search_entry.bind("<Return>", self.on_search)
        
        tk.Button(
            search_frame,
            text="Search",
            command=self.on_search,
            bg="#4a90e2",
            fg="white",
            font=("Helvetica", 10, "bold")
        ).pack(pady=5)

        # Cache Controls Frame
        cache_frame = tk.Frame(left_panel, bg="#ffffff", padx=10, pady=10)
        cache_frame.pack(fill="x")
        
        tk.Label(
            cache_frame,
            text="Semantic Cache:",
            font=("Helvetica", 11),
            bg="#ffffff"
        ).pack(anchor="w")
        
        self.cache_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(
            cache_frame,
            text="Enable Semantic Caching",
            variable=self.cache_enabled,
            bg="#ffffff",
            command=self.toggle_cache
        ).pack(anchor="w")
        
        tk.Button(
            cache_frame,
            text="Clear Cache",
            command=self.clear_cache,
            bg="#e74c3c",
            fg="white",
            font=("Helvetica", 9)
        ).pack(pady=5)

        # Right Panel - Results
        right_panel = tk.Frame(main_frame, bg="#ffffff", bd=2, relief="groove")
        right_panel.pack(side="right", fill="both", expand=True)

        # Results Treeview
        self.tree = ttk.Treeview(
            right_panel,
            columns=("ID", "Title", "Content", "Score", "Source"),
            show="headings",
            style="Custom.Treeview"
        )
        
        # Configure columns
        self.tree.heading("ID", text="ID")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Content", text="Content Preview")
        self.tree.heading("Score", text="Relevance")
        self.tree.heading("Source", text="Source")
        
        self.tree.column("ID", width=80, anchor="center")
        self.tree.column("Title", width=180)
        self.tree.column("Content", width=400)
        self.tree.column("Score", width=80, anchor="center")
        self.tree.column("Source", width=100, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Helvetica", 10),
            bg="#2d3e50",
            fg="white",
            anchor="w",
            padx=20
        ).pack(side="bottom", fill="x")

    def load_sample_data(self):
        """Initialize sample data with scalability in mind"""
        try:
            # Create index if not exists
            try:
                self.redis.ft("ai_index").info()
            except:
                schema = (
                    TextField("id"),
                    TextField("title"),
                    TextField("content"),
                    VectorField("embedding", "FLAT", {
                        "TYPE": "FLOAT32",
                        "DIM": 384,
                        "DISTANCE_METRIC": "COSINE"
                    })
                )
                self.redis.ft("ai_index").create_index(schema)
            
            # Sample documents
            sample_docs = [
                {"id": "doc1", "title": "Introduction to ML", "content": "Machine learning fundamentals and basic algorithms"},
                {"id": "doc2", "title": "Advanced Neural Networks", "content": "Deep learning architectures and applications"},
                {"id": "doc3", "title": "AI Ethics", "content": "Ethical considerations in artificial intelligence"},
                {"id": "doc4", "title": "Natural Language Processing", "content": "Techniques for understanding human language"},
                {"id": "doc5", "title": "Computer Vision", "content": "Algorithms for image recognition and processing"}
            ]
            
            # Load documents in pipeline for efficiency
            with self.redis.pipeline() as pipe:
                for doc in sample_docs:
                    embedding = self.model.encode(doc["content"])
                    pipe.hset(
                        f"doc:{doc['id']}",
                        mapping={
                            "id": doc["id"],
                            "title": doc["title"],
                            "content": doc["content"],
                            "embedding": embedding.astype(np.float32).tobytes()
                        }
                    )
                pipe.execute()
            
            self.status_var.set(f"Loaded {len(sample_docs)} sample documents")
            
            # Initialize cache metrics
            self.redis.set("cache:hits", 0)
            self.redis.set("cache:misses", 0)
            
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to load data: {str(e)}")
            self.root.destroy()

    def on_search(self, event=None):
        """Enhanced search with semantic caching and performance tracking"""
        query = self.search_entry.get().strip()
        if not query:
            self.status_var.set("Please enter a search query")
            return
            
        start_time = time.time()
        self.status_var.set(f"Searching: {query[:30]}...")
        self.root.update()
        
        try:
            # Clear previous results
            self.tree.delete(*self.tree.get_children())
            
            # Check semantic cache first
            cache_key = f"cache:query:{self.get_query_hash(query)}"
            cached_results = None
            
            if self.cache_enabled.get():
                cached_results = self.redis.get(cache_key)
                if cached_results:
                    self.redis.incr("cache:hits")
                    results = json.loads(cached_results)
                    source = "cache"
                else:
                    self.redis.incr("cache:misses")
            
            if not cached_results:
                # Compute fresh results
                query_embedding = self.model.encode(query)
                results = self.redis.ft("ai_index").search(
                    Query("*=>[KNN 5 @embedding $vec AS score]")
                    .return_fields("id", "title", "content", "score")
                    .dialect(2),
                    {"vec": query_embedding.astype(np.float32).tobytes()}
                ).docs
                
                # Store in cache
                if self.cache_enabled.get():
                    serialized = json.dumps([{
                        'id': doc.id,
                        'title': doc.title,
                        'content': doc.content,
                        'score': doc.score
                    } for doc in results])
                    self.redis.setex(cache_key, 3600, serialized)  # Cache for 1 hour
                
                source = "database"
            
            # Display results
            for doc in (results if cached_results else results):
                score = float(doc['score'] if cached_results else doc.score)
                self.tree.insert("", "end", values=(
                    doc['id'] if cached_results else doc.id,
                    doc['title'] if cached_results else doc.title,
                    (doc['content'] if cached_results else doc.content)[:100] + "...",
                    f"{score:.3f}",
                    "⚡ Cache" if cached_results else "🔍 New"
                ))
            
            # Update metrics
            latency = int((time.time() - start_time) * 1000)
            self.query_time_var.set(f"Latency: {latency}ms")
            self.update_cache_metrics()
            
            self.status_var.set(f"Found {len(results)} results ({source})")
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Search Error", str(e))

    def get_query_hash(self, query):
        """Generate consistent hash for query caching"""
        return str(abs(hash(query)))[:10]

    def toggle_cache(self):
        """Enable/disable semantic caching"""
        state = "enabled" if self.cache_enabled.get() else "disabled"
        self.status_var.set(f"Semantic caching {state}")
        self.update_cache_metrics()

    def clear_cache(self):
        """Clear all cached queries"""
        keys = self.redis.keys("cache:query:*")
        if keys:
            self.redis.delete(*keys)
        self.redis.set("cache:hits", 0)
        self.redis.set("cache:misses", 0)
        self.update_cache_metrics()
        self.status_var.set("Cleared all cached queries")

    def update_cache_metrics(self):
        """Update cache performance metrics"""
        hits = int(self.redis.get("cache:hits") or 0)
        misses = int(self.redis.get("cache:misses") or 0)
        total = hits + misses
        ratio = (hits / total * 100) if total > 0 else 0
        self.cache_hits_var.set(f"Cache: {hits}/{total} ({ratio:.1f}% hit rate)")

    def start_performance_monitor(self):
        """Background thread for real-time metrics"""
        def monitor():
            while True:
                try:
                    self.update_cache_metrics()
                    time.sleep(2)
                except Exception as e:
                    print(f"Monitor error: {str(e)}")
        
        threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = AIRecommendationApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Startup Error", f"Application failed to start:\n{str(e)}")