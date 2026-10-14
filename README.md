# 🛒 ShopSmart AI

> Intelligent shopping list generator powered by OpenAI GPT-4o-mini

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0-3178c6.svg)](https://www.typescriptlang.org/)

## 📋 About

ShopSmart AI is a web application that generates optimized weekly shopping lists using artificial intelligence. The application analyzes your budget, dietary preferences, and selected supermarkets to create personalized shopping lists with price estimates.

**Author:** Ivan Sytnik (КН-М524)  
**Supervisor:** Kharchenko A.O.  
**Institution:** NTU "KhPI" - 2025

## ✨ Features

- 🏪 **Multi-store support** - Lidl, Aldi, Edeka, Rewe, Kaufland
- 💰 **Budget optimization** - AI stays within your budget
- 🥗 **Dietary preferences** - Vegetarian, vegan, gluten-free, etc.
- 👨‍👩‍👧‍👦 **Family size scaling** - Portions adjusted for 1-5+ people
- 📊 **Smart categorization** - Items organized by store and category
- ✅ **Progress tracking** - Check off items as you shop
- 📋 **Export options** - Copy to clipboard or print

## 🛠 Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - High-performance web framework
- **Pydantic** - Data validation
- **OpenAI API** - GPT-4o-mini integration
- **Uvicorn** - ASGI server

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Nginx** - Reverse proxy

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- OpenAI API key

### 1. Clone the repository

```bash
git clone https://github.com/IvanSytnik/shopsmart-ai.git
cd shopsmart-ai
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (runtime + dev tooling)
pip install -r requirements.txt -r requirements-dev.txt

# Lint
ruff check .

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional)
cp .env.example .env.local

# Run development server
npm run dev
```

### 4. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=sk-your-key-here

# Build and start containers
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

Access the application at http://localhost

### Individual Containers

```bash
# Backend
cd backend
docker build -t shopsmart-backend .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-xxx shopsmart-backend

# Frontend
cd frontend
docker build -t shopsmart-frontend .
docker run -p 80:80 shopsmart-frontend
```

## 📖 API Documentation

### Generate Shopping List

```http
POST /generate
Content-Type: application/json

{
  "supermarkets": ["Lidl", "Aldi"],
  "budget": 50.0,
  "preferences": "vegetarian diet",
  "family_size": 2
}
```

### Response

```json
{
  "items": [
    {
      "product": "Organic Milk",
      "quantity": "1L",
      "store": "Lidl",
      "approx_price": "1.29",
      "category": "dairy"
    }
  ],
  "total_cost": 47.50,
  "notes": "Consider seasonal vegetables for better prices.",
  "generated_at": "2025-01-15T10:30:00"
}
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/api/supermarkets` | List of supermarkets |
| GET | `/api/categories` | List of categories |
| POST | `/generate` | Generate shopping list |

## 📁 Project Structure

```
shopsmart-ai/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python runtime dependencies
│   ├── requirements-dev.txt # Test + lint tooling
│   ├── pyproject.toml       # ruff config
│   ├── Dockerfile          # Backend container
│   └── .env.example        # Environment template
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── ShopForm.tsx
│   │   │   ├── ShoppingList.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── ErrorBanner.tsx
│   │   ├── App.tsx         # Main component
│   │   ├── api.ts          # API service
│   │   ├── types.ts        # TypeScript types
│   │   ├── constants.ts    # Constants
│   │   └── index.css       # Global styles
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile          # Frontend container
├── docker-compose.yml      # Container orchestration
└── README.md
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
OPENAI_API_KEY=sk-your-api-key
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
```

#### Frontend (.env.local)
```env
VITE_API_URL=http://localhost:8000
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm run test
```

## 📊 Performance

- **API Response Time:** 3-8 seconds (GPT-4o-mini)
- **Typical Request Size:** ~2KB
- **Typical Response Size:** ~5KB
- **Concurrent Users:** 100+ (with proper scaling)

## 🔒 Security

- CORS configured for specific origins
- Input validation with Pydantic
- No sensitive data stored

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- German supermarket pricing research
- NTU "KhPI" Department of Project Management in IT

## 📞 Contact

**Ivan Sytnik**
- Email: i.sytnik02@gmail.com
- GitHub: [@isytnik](https://github.com/ivansytnik)

---

Made with ❤️ at NTU "KhPI" | 2025
