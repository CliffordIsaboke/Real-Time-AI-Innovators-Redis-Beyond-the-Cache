import tkinter as tk
from tkinter import ttk
import numpy as np
from redis import Redis
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer
import json

class AIRecommendationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Recommendation Engine")
        self.root.geometry("1000x600")
        self.root.configure(bg="#f0f2f5")
        
        # Initialize Redis connection
        self.redis = Redis(host='localhost', port=6379, decode_responses=True)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Setup UI
        self.setup_ui()
        self.load_sample_data()
        
    def setup_ui(self):
        # Header Frame
        header_frame = tk.Frame(self.root, bg="#2d3e50", padx=20, pady=15)
        header_frame.pack(fill="x")
        
        self.title_label = tk.Label(
            header_frame,
            text="AI Recommendation Engine",
            font=("Helvetica", 18, "bold"),
            fg="white",
            bg="#2d3e50"
        )
        self.title_label.pack(side="left")
        
        # Search Frame
        search_frame = tk.Frame(self.root, bg="#f0f2f5", padx=20, pady=20)
        search_frame.pack(fill="x")
        
        self.search_label = tk.Label(
            search_frame,
            text="Enter your query:",
            font=("Helvetica", 12),
            bg="#f0f2f5"
        )
        self.search_label.pack(side="left", padx=(0, 10))
        
        self.search_entry = tk.Entry(
            search_frame,
            font=("Helvetica", 12),
            width=50,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#ccc",
            highlightcolor="#4a90e2"
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", self.on_search)
        
        self.search_button = tk.Button(
            search_frame,
            text="Search",
            font=("Helvetica", 12, "bold"),
            bg="#4a90e2",
            fg="white",
            relief="flat",
            command=self.on_search
        )
        self.search_button.pack(side="left", padx=(10, 0))
        
        # Results Frame
        results_frame = tk.Frame(self.root, bg="#f0f2f5", padx=20, pady=10)
        results_frame.pack(fill="both", expand=True)
        
        # Treeview (Table) for results
        self.tree = ttk.Treeview(
            results_frame,
            columns=("ID", "Title", "Content", "Score"),
            show="headings",
            selectmode="browse",
            style="Custom.Treeview"
        )
        
        # Configure style
        style = ttk.Style()
        style.configure("Custom.Treeview", 
                       font=("Helvetica", 11),
                       rowheight=25,
                       background="#ffffff",
                       fieldbackground="#ffffff")
        style.configure("Custom.Treeview.Heading", 
                        font=("Helvetica", 12, "bold"),
                        background="#4a90e2",
                        foreground="white")
        style.map("Custom.Treeview", background=[("selected", "#4a90e2")])
        
        # Configure columns
        self.tree.heading("ID", text="ID", anchor="w")
        self.tree.heading("Title", text="Title", anchor="w")
        self.tree.heading("Content", text="Content Preview", anchor="w")
        self.tree.heading("Score", text="Relevance", anchor="w")
        
        self.tree.column("ID", width=80, anchor="w")
        self.tree.column("Title", width=200, anchor="w")
        self.tree.column("Content", width=500, anchor="w")
        self.tree.column("Score", width=100, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        
        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Helvetica", 10),
            bg="#2d3e50",
            fg="white",
            anchor="w",
            padx=20
        )
        status_bar.pack(side="bottom", fill="x")
        
    def load_sample_data(self):
        sample_data = [
            {"id": "doc1", "title": "Introduction to ML", "content": "Machine learning fundamentals and basic algorithms"},
            {"id": "doc2", "title": "Advanced Neural Networks", "content": "Deep learning architectures and applications"},
            {"id": "doc3", "title": "AI Ethics", "content": "Ethical considerations in artificial intelligence"},
            {"id": "doc4", "title": "Natural Language Processing", "content": "Techniques for understanding human language"},
            {"id": "doc5", "title": "Computer Vision", "content": "Algorithms for image recognition and processing"}
        ]
        
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
        
        # Load sample data
        for doc in sample_data:
            embedding = self.model.encode(doc["content"])
            self.redis.hset(
                f"doc:{doc['id']}",
                mapping={
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "embedding": embedding.astype(np.float32).tobytes()
                }
            )
        
        self.status_var.set("Loaded 5 sample documents")
        
    def on_search(self, event=None):
        query = self.search_entry.get()
        if not query:
            self.status_var.set("Please enter a search query")
            return
            
        self.status_var.set(f"Searching for: {query}...")
        self.root.update_idletasks()
        
        try:
            # Clear previous results
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # Perform vector search
            query_embedding = self.model.encode(query)
            results = self.redis.ft("ai_index").search(
                Query("*=>[KNN 5 @embedding $vec AS score]")
                .return_fields("id", "title", "content", "score")
                .dialect(2),
                {"vec": query_embedding.astype(np.float32).tobytes()}
            )
            
            # Display results
            for i, doc in enumerate(results.docs):
                score = float(doc['score'])
                self.tree.insert("", "end", values=(
                    doc['id'],
                    doc['title'],
                    doc['content'][:100] + "..." if len(doc['content']) > 100 else doc['content'],
                    f"{score:.3f}"
                ))
                
            self.status_var.set(f"Found {len(results.docs)} results for: {query}")
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AIRecommendationApp(root)
    root.mainloop()