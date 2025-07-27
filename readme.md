E-Commerce System with Redis and AI Recommendation Engine
This repository contains two Python projects: an E-Commerce System and an AI Recommendation Engine, both powered by Redis for data storage and querying.

## Projects Overview
# 1. E-Commerce System (beyond-cache-ui.py)
This is a simple, scalable, and interactive e-commerce system built using Python's Tkinter for the UI and Redis for backend storage. It supports:

- Product Management: View, add, search, and manage products in the store.

- Order Processing: Process new orders and update order status.

- Inventory Updates: Real-time updates using Redis Pub/Sub.

- Integration with Redis for storing product information and order data.

# 2. AI Recommendation Engine (ai-recommendation-ui.py)
This project demonstrates the use of AI-powered recommendation systems, integrating Redis for vector storage and querying. It uses the Sentence-Transformers model to generate embeddings for text data and provides:

- Query-based search: Enter a query and receive recommendations based on content similarity.

- Results display: Shows top N relevant results based on cosine similarity of text embeddings.


# Project Setup
- Prerequisites
- Python 3.7+

# Docker (for Redis setup)

- Redis 6.0 or higher

# Required Python packages

# Installation Steps
Install Redis with Docker:

- Use the following Docker command to run Redis with the necessary modules for the E-Commerce System:

docker run -p 6379:6379 redislabs/redisearch:latest

This command runs Redis with the RedisSearch module, which is used for indexing and querying.

# Install Python Dependencies:

Install the required Python libraries by running:

pip install redis==4.5.5 sentence-transformers numpy
pip install redisearch-client
Note: It's important to use the exact versions of Redis and other dependencies to ensure compatibility.(Ensure to set up virtual enev)

# Clone this Repository:


git clone https://github.com/CliffordIsaboke/Real-Time-AI-Innovators-Redis-Beyond-the-Cache-.git
cd Real-Time-AI-Innovators-Redis-Beyond-the-Cache

# Run the Projects:

To start the E-Commerce System, run the following command:


python beyond-cache-ui.py

To start the AI Recommendation Engine, run:


python ai-recommendation-ui.py

# Setting Up Redis
- E-Commerce System: Redis is used to store product and order data, leveraging the RediSearch and RedisJSON modules for advanced   indexing and querying.

- AI Recommendation Engine: The system uses Redis Vector Search to store and query document embeddings for content-based recommendations. The Sentence-Transformer model (all-MiniLM-L6-v2) is used to convert text into vector embeddings, which are stored and searched in Redis.

# Running the Application

# E-Commerce System:

- After launching, the application shows a window with a list of products, order processing details, and inventory updates.

- You can search for products, add inventory, and process new orders in real-time.

# AI Recommendation Engine:

- The app allows users to input a query, and it provides recommendations based on content similarity.

-Results are displayed in a table with the most relevant documents.

# Features
# E-Commerce System
Product Management:

- Search products by name or description.

- View and manage product details like name, price, and stock.

Order Management:

- Process orders with automatic status updates.

- Inventory Updates:

- Real-time updates through Redis Pub/Sub.

# AI Recommendation Engine
Search by Query:

- Uses the SentenceTransformer model to encode the user's query into a vector and search the Redis database for similar documents.

# Results:

Shows a list of matching documents with their titles, content previews, and relevance score.


# Troubleshooting
# Redis Connection Issues:

If you encounter connection issues with Redis, ensure the Redis container is running:


docker ps
This should show redislabs/redisearch running on port 6379. If Redis is not running, start the container again:


docker start <container_id>

Missing Redis Modules:

If Redis modules like RedisSearch or RedisJSON are missing, ensure that the Docker container is running redislabs/redisearch as mentioned in the setup instructions.

AI Recommendation Engine:

If the AI engine doesn't return any results, check if the embeddings are properly stored in Redis. You can check this with the following Redis CLI command:


redis-cli HGETALL doc:doc1
This should return the document data along with the vector embeddings.

