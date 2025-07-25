# beyond_cache_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
from redis import Redis
from redis.commands.search.field import TextField, NumericField
from redis.commands.search.query import Query
import json
import threading

class ECommerceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("E-Commerce System")
        self.root.geometry("1200x700")
        self.root.configure(bg="#f5f5f5")
        
        # Initialize Redis connection
        self.redis = Redis(host='localhost', port=6379, decode_responses=True)
        self.setup_data()
        
        # Setup UI
        self.create_widgets()
        self.start_stream_listener()
        
    def setup_data(self):
        """Initialize sample data if not exists"""
        try:
            self.redis.ft("products").info()
        except:
            schema = (
                TextField("name"),
                TextField("description"),
                NumericField("price")
            )
            self.redis.ft("products").create_index(schema)
            
            # Add sample products
            sample_products = [
                ("1001", "Wireless Headphones", "Noise cancelling headphones", 199.99),
                ("1002", "Bluetooth Speaker", "Portable waterproof speaker", 89.99),
                ("1003", "Smart Watch", "Fitness tracking and notifications", 249.99)
            ]
            for pid, name, desc, price in sample_products:
                self.redis.json().set(f"product:{pid}", "$", {
                    "name": name,
                    "description": desc,
                    "price": price,
                    "inventory": 50
                })
                self.redis.ft("products").add_document(
                    f"prod:{pid}",
                    name=name,
                    description=desc,
                    price=price
                )
            self.redis.set("system:total_products", len(sample_products))

    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", padx=20, pady=15)
        header.pack(fill="x")
        
        tk.Label(
            header,
            text="Redis E-Commerce System",
            font=("Helvetica", 18, "bold"),
            fg="white",
            bg="#2c3e50"
        ).pack(side="left")
        
        # Main Content Frame
        main_frame = tk.Frame(self.root, bg="#f5f5f5")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Left Panel - Product Management
        left_panel = tk.Frame(main_frame, bg="#ecf0f1", padx=15, pady=15, bd=2, relief="groove")
        left_panel.pack(side="left", fill="y")
        
        tk.Label(
            left_panel,
            text="Product Management",
            font=("Helvetica", 14, "bold"),
            bg="#ecf0f1"
        ).pack(pady=(0, 15))
        
        # Product Search
        search_frame = tk.Frame(left_panel, bg="#ecf0f1")
        search_frame.pack(fill="x", pady=5)
        
        self.search_entry = tk.Entry(search_frame, font=("Helvetica", 12), width=25)
        self.search_entry.pack(side="left", padx=(0, 5))
        
        tk.Button(
            search_frame,
            text="Search",
            font=("Helvetica", 10, "bold"),
            bg="#3498db",
            fg="white",
            command=self.search_products
        ).pack(side="left")
        
        # Product Treeview
        self.product_tree = ttk.Treeview(
            left_panel,
            columns=("id", "name", "price", "inventory"),
            show="headings",
            height=10
        )
        self.product_tree.heading("id", text="ID")
        self.product_tree.heading("name", text="Name")
        self.product_tree.heading("price", text="Price")
        self.product_tree.heading("inventory", text="Stock")
        self.product_tree.column("id", width=80)
        self.product_tree.column("name", width=180)
        self.product_tree.column("price", width=80)
        self.product_tree.column("inventory", width=80)
        self.product_tree.pack(fill="both", pady=10)
        
        # Right Panel - Orders and Inventory
        right_panel = tk.Frame(main_frame, bg="#ecf0f1", padx=15, pady=15, bd=2, relief="groove")
        right_panel.pack(side="right", fill="both", expand=True)
        
        # Orders Frame
        orders_frame = tk.Frame(right_panel, bg="#ecf0f1")
        orders_frame.pack(fill="both", expand=True)
        
        tk.Label(
            orders_frame,
            text="Order Processing",
            font=("Helvetica", 14, "bold"),
            bg="#ecf0f1"
        ).pack(anchor="w")
        
        self.orders_tree = ttk.Treeview(
            orders_frame,
            columns=("order_id", "product_id", "quantity", "status"),
            show="headings",
            height=8
        )
        self.orders_tree.heading("order_id", text="Order ID")
        self.orders_tree.heading("product_id", text="Product ID")
        self.orders_tree.heading("quantity", text="Qty")
        self.orders_tree.heading("status", text="Status")
        self.orders_tree.pack(fill="both", pady=5)
        
        # Inventory Updates Frame
        inventory_frame = tk.Frame(right_panel, bg="#ecf0f1")
        inventory_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        tk.Label(
            inventory_frame,
            text="Inventory Updates",
            font=("Helvetica", 14, "bold"),
            bg="#ecf0f1"
        ).pack(anchor="w")
        
        self.inventory_text = tk.Text(
            inventory_frame,
            height=6,
            font=("Helvetica", 10),
            bg="white",
            state="disabled"
        )
        self.inventory_text.pack(fill="both")
        
        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("System Ready")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Helvetica", 10),
            bg="#2c3e50",
            fg="white",
            anchor="w",
            padx=20
        ).pack(side="bottom", fill="x")
        
        # Load initial data
        self.load_products()
        self.load_orders()
        
    def load_products(self):
        """Load products into the treeview"""
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        # Get all products
        products = self.redis.keys("product:*")
        for product_key in products:
            product_data = self.redis.json().get(product_key)
            self.product_tree.insert("", "end", values=(
                product_key.split(":")[1],
                product_data["name"],
                f"${product_data['price']:.2f}",
                product_data["inventory"]
            ))
    
    def search_products(self):
        """Search products using RediSearch"""
        query = self.search_entry.get()
        if not query:
            self.load_products()
            return
            
        try:
            results = self.redis.ft("products").search(
                Query(query).slop(1)
            )
            
            for item in self.product_tree.get_children():
                self.product_tree.delete(item)
                
            for doc in results.docs:
                product_data = self.redis.json().get(f"product:{doc.id}")
                self.product_tree.insert("", "end", values=(
                    doc.id,
                    product_data["name"],
                    f"${product_data['price']:.2f}",
                    product_data["inventory"]
                ))
                
            self.status_var.set(f"Found {results.total} products matching '{query}'")
            
        except Exception as e:
            messagebox.showerror("Search Error", str(e))
    
    def load_orders(self):
        """Load recent orders from stream"""
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
            
        orders = self.redis.xrevrange("orders", "+", "-", count=5)
        for order_id, order_data in orders:
            self.orders_tree.insert("", "end", values=(
                order_id.split("-")[0],
                order_data["product_id"],
                order_data["quantity"],
                order_data["status"]
            ))
    
    def start_stream_listener(self):
        """Start background thread to listen for inventory updates"""
        def listener():
            pubsub = self.redis.pubsub()
            pubsub.subscribe("inventory_updates")
            
            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        update = json.loads(message["data"])
                        self.root.after(0, self.display_inventory_update, update)
                    except json.JSONDecodeError:
                        pass
        
        thread = threading.Thread(target=listener, daemon=True)
        thread.start()
    
    def display_inventory_update(self, update):
        """Display inventory updates in the text widget"""
        self.inventory_text.config(state="normal")
        self.inventory_text.insert("end", 
            f"Product {update['product_id']} stock updated to {update['new_stock']}\n")
        self.inventory_text.see("end")
        self.inventory_text.config(state="disabled")
        
        # Refresh product list
        self.load_products()
        
        # Simulate order processing
        self.process_new_orders()
    
    def process_new_orders(self):
        """Simulate order processing"""
        orders = self.redis.xread({"orders": "0-0"}, count=1, block=0)
        if orders:
            stream, messages = orders[0]
            for message_id, message_data in messages:
                # Update order status
                self.redis.xadd("orders", {
                    "order_id": message_data["order_id"],
                    "product_id": message_data["product_id"],
                    "quantity": message_data["quantity"],
                    "status": "processed"
                })
                
                # Update UI
                self.load_orders()
                self.status_var.set(f"Processed order {message_data['order_id']}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ECommerceApp(root)
    
    # Configure styles
    style = ttk.Style()
    style.configure("Treeview", 
                   font=("Helvetica", 11),
                   rowheight=25,
                   background="#ffffff",
                   fieldbackground="#ffffff")
    style.configure("Treeview.Heading", 
                    font=("Helvetica", 12, "bold"),
                    background="#3498db",
                    foreground="white")
    style.map("Treeview", background=[("selected", "#2980b9")])
    
    root.mainloop()