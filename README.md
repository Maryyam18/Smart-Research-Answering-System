# Smart Answering Research System – Backend

This repository contains the backend implementation of the **Smart Answering Research System**, a research-oriented platform designed to provide **authentic, citation-backed answers** by combining structured academic data and web-based research sources.

---

## 🚀 Project Overview

The backend processes user queries, retrieves relevant research content from both stored documents and the web, and generates accurate responses using a **Retrieval-Augmented Generation (RAG)** pipeline. The system was developed using the **Agile Scrum methodology across 9 sprints** and presented during the **Open House evaluation**.

---

## 🧩 Tech Stack Overview

### 🔹 Backend Technologies

- **Python (FastAPI)**  
  Used to build high-performance, scalable REST APIs for handling queries, authentication, and data flow.

- **GROBID**  
  Utilized for extracting and structurally parsing research papers (PDFs) into machine-readable formats, enabling accurate content retrieval.

- **Gemini**  
  Integrated for intelligent, context-aware answer generation based on retrieved research data.

- **Tavily**  
  Used for web-based research search. Retrieved sources are converted into embeddings and ranked for relevance, supporting deep research queries.

- **Supabase**  
  Handles database management and authentication, including user data, query history, and session handling.

- **GitHub**  
  Used for version control and collaborative development.

- **Railway**  
  Backend deployment platform providing scalable and reliable API hosting.

---

## ✨ Core Features

- **Research-based question answering**
- **Simple queries:** concise 4–5 line responses  
- **Deep research queries:** detailed answers with multiple references  
- **Citation-backed responses from trusted sources**
- **Authentication and user session management**
- **Query and response history tracking**
- **API support for voice-enabled frontend interactions**

---

## ⚙️ Architecture Overview

- FastAPI-based RESTful services  
- RAG pipeline for retrieval and generation  
- GROBID-powered document parsing  
- Embedding-based ranking for research relevance  
- Supabase for persistent storage and authentication  

---

## 📦 Deployment

The backend is deployed using **Railway**.

---

## 🧪 Development Methodology

- **Agile Scrum methodology**
- Completed in **9 sprints**
- Sprint planning, reviews, and retrospectives followed consistently
- Evaluated during **Open House**

---

## 🎓 Academic Context

- Developed as an academic project  
- Supported by **IDEAL Labs**  
- Department of Computer Science, **UET Lahore**  
- Supervised by **Sir Khaldon Khurshid**

---

## 🤝 Contributions & Feedback

Contributions, suggestions, and feedback are welcome to improve research accuracy and system scalability.

---

⭐ If you find this project useful, feel free to star the repository!
