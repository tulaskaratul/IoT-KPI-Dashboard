#!/bin/bash

echo "🚀 Starting IoT KPI Dashboard..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create necessary directories
mkdir -p logs
mkdir -p grafana/dashboards
mkdir -p grafana/provisioning/datasources
mkdir -p grafana/provisioning/dashboards

echo "📦 Building and starting services..."

# Start services
docker-compose up -d --build

echo "⏳ Waiting for services to be ready..."

# Wait for PostgreSQL to be ready
echo "🔍 Waiting for PostgreSQL..."
until docker-compose exec postgres pg_isready -U iot_user -d iot_kpi_db 2>/dev/null; do
    echo "⏳ PostgreSQL is not ready yet..."
    sleep 5
done

echo "✅ PostgreSQL is ready!"

# Wait for API to be ready
echo "🔍 Waiting for API..."
until curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; do
    echo "⏳ API is not ready yet..."
    sleep 2
done

echo "✅ API is ready!"

# Initialize database with sample data
echo "🗄️ Initializing database with sample data..."
python scripts/init_db.py

echo ""
echo "🎉 IoT KPI Dashboard is ready!"
echo ""
echo "📊 Access your services:"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Grafana Dashboard: http://localhost:3000 (admin/admin123)"
echo "   • API Health: http://localhost:8000/api/v1/health"
echo ""
echo "📈 View logs with: docker-compose logs -f"
echo "🛑 Stop services with: docker-compose down"
echo ""
