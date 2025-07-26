# beyond-cache-ui.py - Complete E-Commerce System with Redis Backend
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from redis import Redis
from redis.commands.search.field import TextField, NumericField
from redis.commands.search.query import Query
import json
import threading
import uuid
from datetime import datetime

class ECommerceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Redis E-Commerce System")
        self.root.geometry("1300x750")
        self.root.configure(bg="#f5f5f5")
        
        # Initialize Redis connection
        self.redis = Redis(
            host='localhost', 
            port=6379, 
            decode_responses=True,
            socket_connect_timeout=3
        )
        
        try:
            self.redis.ping()
            self.setup_data()
        except Exception as e:
            messagebox.showerror("Redis Connection Failed", f"Could not connect to Redis: {str(e)}")
            self.root.destroy()
            return
        
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
                NumericField("price"),
                NumericField("inventory")
            )
            self.redis.ft("products").create_index(schema)
            
            # Add sample products
            sample_products = [
                ("1001", "Wireless Headphones", "Premium noise cancelling headphones", 199.99, 50),
                ("1002", "Bluetooth Speaker", "Waterproof portable speaker", 89.99, 30),
                ("1003", "Smart Watch", "Fitness tracking with notifications", 249.99, 20)
            ]
            for pid, name, desc, price, inventory in sample_products:
                self.add_product_to_redis(pid, name, desc, price, inventory)
            
            self.redis.set("system:total_products", len(sample_products))
            self.redis.xadd("system_log", {"event": "init", "message": "Sample data loaded"})

    def create_widgets(self):
        # Configure styles
        self.configure_styles()
        
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

        # CRUD Buttons
        crud_frame = tk.Frame(left_panel, bg="#ecf0f1")
        crud_frame.pack(fill="x", pady=(0, 10))
        
        tk.Button(
            crud_frame,
            text="➕ Add Product",
            font=("Helvetica", 10, "bold"),
            bg="#27ae60",
            fg="white",
            command=self.show_add_product_dialog
        ).pack(side="left", padx=2, fill="x", expand=True)

        tk.Button(
            crud_frame,
            text="✏️ Edit Selected",
            font=("Helvetica", 10, "bold"),
            bg="#f39c12",
            fg="white",
            command=self.show_edit_product_dialog
        ).pack(side="left", padx=2, fill="x", expand=True)

        tk.Button(
            crud_frame,
            text="❌ Delete Selected",
            font=("Helvetica", 10, "bold"),
            bg="#e74c3c",
            fg="white",
            command=self.delete_selected_product
        ).pack(side="left", padx=2, fill="x", expand=True)

        # Search Frame
        search_frame = tk.Frame(left_panel, bg="#ecf0f1")
        search_frame.pack(fill="x", pady=5)
        
        self.search_entry = tk.Entry(search_frame, font=("Helvetica", 12), width=25)
        self.search_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
        
        tk.Button(
            search_frame,
            text="🔍 Search",
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
            height=12,
            selectmode="browse"
        )
        self.product_tree.heading("id", text="ID")
        self.product_tree.heading("name", text="Name")
        self.product_tree.heading("price", text="Price")
        self.product_tree.heading("inventory", text="Stock")
        self.product_tree.column("id", width=80, anchor="center")
        self.product_tree.column("name", width=180)
        self.product_tree.column("price", width=80, anchor="e")
        self.product_tree.column("inventory", width=80, anchor="center")
        
        scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        self.product_tree.pack(fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Right Panel - Orders and Inventory
        right_panel = tk.Frame(main_frame, bg="#ecf0f1", padx=15, pady=15, bd=2, relief="groove")
        right_panel.pack(side="right", fill="both", expand=True)
        
        # Orders Frame
        orders_frame = tk.Frame(right_panel, bg="#ecf0f1")
        orders_frame.pack(fill="both", expand=True)
        
        tk.Label(
            orders_frame,
            text="📦 Order Processing",
            font=("Helvetica", 14, "bold"),
            bg="#ecf0f1"
        ).pack(anchor="w")
        
        self.orders_tree = ttk.Treeview(
            orders_frame,
            columns=("order_id", "product_id", "quantity", "status", "timestamp"),
            show="headings",
            height=8
        )
        self.orders_tree.heading("order_id", text="Order ID")
        self.orders_tree.heading("product_id", text="Product ID")
        self.orders_tree.heading("quantity", text="Qty")
        self.orders_tree.heading("status", text="Status")
        self.orders_tree.heading("timestamp", text="Time")
        self.orders_tree.column("order_id", width=100)
        self.orders_tree.column("product_id", width=100)
        self.orders_tree.column("quantity", width=50, anchor="center")
        self.orders_tree.column("status", width=100)
        self.orders_tree.column("timestamp", width=150)
        self.orders_tree.pack(fill="both", pady=5)
        
        # Inventory Updates Frame
        inventory_frame = tk.Frame(right_panel, bg="#ecf0f1")
        inventory_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        tk.Label(
            inventory_frame,
            text="📊 Inventory Updates",
            font=("Helvetica", 14, "bold"),
            bg="#ecf0f1"
        ).pack(anchor="w")
        
        self.inventory_text = tk.Text(
            inventory_frame,
            height=8,
            font=("Consolas", 10),
            bg="white",
            state="disabled"
        )
        scrollbar = ttk.Scrollbar(inventory_frame, orient="vertical", command=self.inventory_text.yview)
        self.inventory_text.configure(yscrollcommand=scrollbar.set)
        self.inventory_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("✅ System Ready | Connected to Redis")
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

    def configure_styles(self):
        style = ttk.Style()
        style.configure("Treeview", 
                       font=("Helvetica", 11),
                       rowheight=28,
                       background="#ffffff",
                       fieldbackground="#ffffff")
        style.configure("Treeview.Heading", 
                        font=("Helvetica", 12, "bold"),
                        background="#3498db",
                        foreground="white")
        style.map("Treeview", 
                 background=[("selected", "#2980b9")],
                 foreground=[("selected", "white")])

    # Core Product Functions ====================================

    def add_product_to_redis(self, pid, name, description, price, inventory):
        """Atomic operation to add product to both JSON and search index"""
        product_data = {
            "name": name,
            "description": description,
            "price": float(price),
            "inventory": int(inventory),
            "created_at": datetime.now().isoformat()
        }
        
        # Store in JSON
        self.redis.json().set(f"product:{pid}", "$", product_data)
        
        # Index in RediSearch
        self.redis.ft("products").add_document(
            f"prod:{pid}",
            name=name,
            description=description,
            price=price,
            inventory=inventory
        )
        
        # Log event
        self.redis.xadd("system_log", {
            "event": "product_add",
            "product_id": pid,
            "name": name
        })

    def update_product_in_redis(self, pid, updates):
        """Update existing product data"""
        current = self.redis.json().get(f"product:{pid}")
        if not current:
            raise ValueError(f"Product {pid} not found")
        
        # Update JSON data
        updated = {**current, **updates}
        self.redis.json().set(f"product:{pid}", "$", updated)
        
        # Update search index
        self.redis.ft("products").add_document(
            f"prod:{pid}",
            name=updated.get("name", current["name"]),
            description=updated.get("description", current["description"]),
            price=updated.get("price", current["price"]),
            inventory=updated.get("inventory", current["inventory"])
        )
        
        # Publish inventory update if stock changed
        if "inventory" in updates:
            self.redis.publish("inventory_updates", json.dumps({
                "product_id": pid,
                "new_stock": updates["inventory"],
                "action": "update"
            }))
        
        # Log event
        self.redis.xadd("system_log", {
            "event": "product_update",
            "product_id": pid
        })

    def delete_product_from_redis(self, pid):
        """Remove product from system"""
        # Get product name for logging
        product = self.redis.json().get(f"product:{pid}")
        
        # Delete from JSON store
        self.redis.json().delete(f"product:{pid}")
        
        # Delete from search index
        self.redis.ft("products").delete_document(f"prod:{pid}")
        
        # Update total count
        self.redis.decr("system:total_products")
        
        # Log event
        self.redis.xadd("system_log", {
            "event": "product_delete",
            "product_id": pid,
            "name": product["name"] if product else "Unknown"
        })

    # UI Dialog Functions ======================================

    def show_add_product_dialog(self):
        """Show dialog for adding new product"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Product")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        fields = [
            ("Name:", "", True),
            ("Description:", "", True),
            ("Price:", "0.00", True),
            ("Initial Stock:", "10", True)
        ]
        
        entries = []
        for i, (label, default, required) in enumerate(fields):
            frame = tk.Frame(dialog)
            frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(frame, text=label, width=15, anchor="e").pack(side="left")
            entry = tk.Entry(frame)
            entry.insert(0, default)
            entry.pack(side="left", fill="x", expand=True)
            entries.append(entry)
            
            if required:
                tk.Label(frame, text="*", fg="red").pack(side="left", padx=2)
        
        def submit():
            try:
                # Validate inputs
                name = entries[0].get().strip()
                description = entries[1].get().strip()
                price = float(entries[2].get())
                inventory = int(entries[3].get())
                
                if not name:
                    raise ValueError("Product name is required")
                if price <= 0:
                    raise ValueError("Price must be positive")
                if inventory < 0:
                    raise ValueError("Inventory cannot be negative")
                
                # Generate ID and add product
                pid = str(uuid.uuid4())[:8].upper()
                self.add_product_to_redis(pid, name, description, price, inventory)
                
                # Update UI
                self.load_products()
                self.status_var.set(f"✅ Added new product: {name}")
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e), parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add product: {str(e)}", parent=dialog)
        
        # Submit button
        tk.Button(
            dialog,
            text="Add Product",
            command=submit,
            bg="#27ae60",
            fg="white",
            font=("Helvetica", 10, "bold")
        ).pack(pady=10)

    def show_edit_product_dialog(self):
        """Show dialog for editing existing product"""
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to edit")
            return
            
        pid = self.product_tree.item(selected[0], "values")[0]
        product_data = self.redis.json().get(f"product:{pid}")
        
        if not product_data:
            messagebox.showerror("Error", "Selected product not found in database")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Product {pid}")
        dialog.geometry("400x400")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        # Display product ID (non-editable)
        tk.Label(dialog, text=f"Product ID: {pid}", font=("Helvetica", 10)).pack(pady=5)
        
        fields = [
            ("Name:", product_data["name"], True),
            ("Description:", product_data["description"], False),
            ("Price:", str(product_data["price"]), True),
            ("Inventory:", str(product_data["inventory"]), True)
        ]
        
        entries = []
        for i, (label, value, required) in enumerate(fields):
            frame = tk.Frame(dialog)
            frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(frame, text=label, width=15, anchor="e").pack(side="left")
            entry = tk.Entry(frame)
            entry.insert(0, value)
            entry.pack(side="left", fill="x", expand=True)
            entries.append(entry)
            
            if required:
                tk.Label(frame, text="*", fg="red").pack(side="left", padx=2)
        
        def submit():
            try:
                updates = {
                    "name": entries[0].get().strip(),
                    "description": entries[1].get().strip(),
                    "price": float(entries[2].get()),
                    "inventory": int(entries[3].get())
                }
                
                # Validate
                if not updates["name"]:
                    raise ValueError("Product name is required")
                if updates["price"] <= 0:
                    raise ValueError("Price must be positive")
                if updates["inventory"] < 0:
                    raise ValueError("Inventory cannot be negative")
                
                # Update product
                self.update_product_in_redis(pid, updates)
                
                # Refresh UI
                self.load_products()
                self.status_var.set(f"✅ Updated product: {updates['name']}")
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e), parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update product: {str(e)}", parent=dialog)
        
        # Submit button
        tk.Button(
            dialog,
            text="Save Changes",
            command=submit,
            bg="#f39c12",
            fg="white",
            font=("Helvetica", 10, "bold")
        ).pack(pady=10)

    def delete_selected_product(self):
        """Delete the currently selected product"""
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to delete")
            return
            
        pid = self.product_tree.item(selected[0], "values")[0]
        name = self.product_tree.item(selected[0], "values")[1]
        
        if messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete product:\n\n{name} (ID: {pid})?\n\nThis cannot be undone!",
            icon="warning"
        ):
            try:
                self.delete_product_from_redis(pid)
                self.load_products()
                self.status_var.set(f"❌ Deleted product: {name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete product: {str(e)}")

    # Data Loading Functions ===================================

    def load_products(self):
        """Load products into the treeview"""
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        try:
            # Get all products using JSON
            products = self.redis.keys("product:*")
            for product_key in products:
                product_data = self.redis.json().get(product_key)
                if product_data:
                    self.product_tree.insert("", "end", values=(
                        product_key.split(":")[1],
                        product_data["name"],
                        f"${product_data['price']:.2f}",
                        product_data["inventory"]
                    ))
                    
            self.status_var.set(f"🔄 Loaded {len(products)} products")
        except Exception as e:
            self.status_var.set(f"❌ Error loading products: {str(e)}")
            messagebox.showerror("Error", f"Failed to load products: {str(e)}")

    def search_products(self):
        """Search products using RediSearch"""
        query = self.search_entry.get().strip()
        if not query:
            self.load_products()
            return
            
        try:
            results = self.redis.ft("products").search(
                Query(query).slop(1)
            )
            
            self.product_tree.delete(*self.product_tree.get_children())
            
            for doc in results.docs:
                product_data = self.redis.json().get(f"product:{doc.id}")
                if product_data:
                    self.product_tree.insert("", "end", values=(
                        doc.id,
                        product_data["name"],
                        f"${product_data['price']:.2f}",
                        product_data["inventory"]
                    ))
                    
            self.status_var.set(f"🔍 Found {results.total} products matching '{query}'")
            
        except Exception as e:
            self.status_var.set(f"❌ Search failed: {str(e)}")
            messagebox.showerror("Search Error", str(e))

    def load_orders(self):
        """Load recent orders from stream"""
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
            
        try:
            orders = self.redis.xrevrange("orders", "+", "-", count=10)
            for order_id, order_data in orders:
                timestamp = datetime.fromtimestamp(int(order_id.split("-")[0])/1000)
                self.orders_tree.insert("", "end", values=(
                    order_id.split("-")[0],
                    order_data["product_id"],
                    order_data["quantity"],
                    order_data["status"],
                    timestamp.strftime("%Y-%m-%d %H:%M:%S")
                ))
        except Exception as e:
            self.status_var.set(f"❌ Error loading orders: {str(e)}")

    # Real-Time Functions ======================================

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
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        action = update.get("action", "update")
        if action == "update":
            msg = f"[{timestamp}] Stock update: Product {update['product_id']} → {update['new_stock']} units\n"
        elif action == "add":
            msg = f"[{timestamp}] New product: {update['product_id']} added with {update['new_stock']} units\n"
        else:
            msg = f"[{timestamp}] Inventory change: {update}\n"
        
        self.inventory_text.insert("end", msg)
        self.inventory_text.see("end")
        self.inventory_text.config(state="disabled")
        
        # Refresh product list if needed
        if action in ("update", "add"):
            self.load_products()
        
        # Process any pending orders
        self.process_new_orders()

    def process_new_orders(self):
        """Simulate order processing workflow"""
        try:
            orders = self.redis.xread({"orders": "0-0"}, count=1, block=0)
            if orders:
                stream, messages = orders[0]
                for message_id, message_data in messages:
                    # Check inventory
                    pid = message_data["product_id"]
                    quantity = int(message_data["quantity"])
                    product = self.redis.json().get(f"product:{pid}")
                    
                    if product and product["inventory"] >= quantity:
                        # Update inventory
                        new_stock = product["inventory"] - quantity
                        self.update_product_in_redis(pid, {"inventory": new_stock})
                        
                        # Update order status
                        self.redis.xadd("orders", {
                            "order_id": message_data["order_id"],
                            "product_id": pid,
                            "quantity": quantity,
                            "status": "fulfilled"
                        })
                        
                        # Update UI
                        self.load_orders()
                        self.status_var.set(f"🔄 Processed order {message_data['order_id']}")
                    else:
                        # Mark as failed
                        self.redis.xadd("orders", {
                            "order_id": message_data["order_id"],
                            "product_id": pid,
                            "quantity": quantity,
                            "status": "failed (insufficient stock)"
                        })
        except Exception as e:
            self.status_var.set(f"❌ Order processing error: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = ECommerceApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", f"Application failed to start:\n{str(e)}")
        root.destroy()