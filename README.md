# IoT KPI Dashboard

A comprehensive dashboard for monitoring IoT device performance, uptime, and key performance indicators using Python, Docker, PostgreSQL, and Grafana.

## 🚀 Features

- **Real-time Device Monitoring**: Track device status (active/inactive) with uptime calculations
- **Advanced KPI Metrics**: Device availability, uptime percentage, response times, error rates
- **Intelligent Uptime Analysis**: Not just active/inactive status, but consistent activity patterns
- **Beautiful Visualizations**: Grafana dashboards with real-time updates
- **Scalable Architecture**: Microservices with Docker orchestration
- **Test Device Support**: Built-in support for test devices with sample data

## 🏗️ Architecture

- **API Server**: FastAPI with Python 3.11
- **Database**: PostgreSQL with time-series optimized schema
- **Visualization**: Grafana with custom dashboards
- **Data Collection**: Automated collectors for device metrics
- **Caching**: Redis for performance optimization
- **Orchestration**: Docker Compose for easy deployment

## 📊 KPI Metrics

- **Device Availability**: Percentage of devices currently online
- **Uptime Percentage**: Average device uptime over specified periods
- **Response Time**: Average response time for device communications
- **Error Rate**: Percentage of failed device communications
- **Data Throughput**: Amount of data processed by devices
- **Status Consistency**: Analysis of device activity patterns

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### 1. Clone and Setup

```bash
git clone <your-repo>
cd iot_kpi_project
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Initialize Database

```bash
# Run database initialization script
python scripts/init_db.py
```

### 4. Access Services

- **API Documentation**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/admin123)
- **API Health**: http://localhost:8000/api/v1/health

## 🔧 Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
```

Key configurations:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SAMASTH_API_URL`: External API endpoint
- `COLLECTION_INTERVAL`: Data collection frequency (seconds)

### Database Schema

The system uses a time-series optimized schema:

- **devices**: Device information and metadata
- **device_metrics**: Time-series metrics data
- **device_status_history**: Status change tracking
- **kpi_calculations**: Pre-calculated KPI values

## 📈 Usage

### API Endpoints

#### Devices
- `GET /api/v1/devices` - List all devices
- `GET /api/v1/devices/{device_id}` - Get specific device
- `POST /api/v1/devices` - Create new device
- `PUT /api/v1/devices/{device_id}` - Update device

#### Metrics
- `GET /api/v1/devices/{device_id}/metrics` - Get device metrics
- `POST /api/v1/devices/{device_id}/metrics` - Add device metric
- `GET /api/v1/metrics/summary` - Get metrics summary

#### KPIs
- `GET /api/v1/devices/{device_id}/kpis` - Get device KPIs
- `POST /api/v1/devices/{device_id}/kpis/calculate` - Calculate KPIs
- `GET /api/v1/kpis/summary` - Get KPI summary

### Grafana Dashboards

The system includes pre-configured dashboards:

1. **Device Status Overview**: Real-time device status
2. **Uptime Trends**: Historical uptime analysis
3. **Response Times**: Performance monitoring
4. **Data Throughput**: Network usage patterns
5. **Error Analysis**: Error rate by device type

## 🔄 Data Collection

### Automatic Collection

The system includes a data collector that:

1. **Simulates Device Data**: For test devices
2. **Updates Metrics**: Every 60 seconds (configurable)
3. **Tracks Status Changes**: Monitors device state transitions
4. **Calculates KPIs**: Automated KPI computation

### Manual Data Input

You can also manually add metrics via the API:

```python
import requests

# Add a metric
response = requests.post(
    "http://localhost:8000/api/v1/devices/TEST_DEVICE_001/metrics",
    json={
        "timestamp": "2024-01-01T12:00:00Z",
        "metric_type": "uptime",
        "value": 0.95,
        "unit": "percentage"
    }
)
```

## 🧪 Testing

### Test Devices

The system includes 5 test devices:

1. **TEMP_001**: Temperature Sensor (Building A - Floor 1)
2. **HUMID_001**: Humidity Monitor (Building A - Floor 2)
3. **MOTION_001**: Motion Detector (Building B - Entrance)
4. **AIR_001**: Air Quality Monitor (Building A - Lobby)
5. **CAM_001**: Smart Camera (Building B - Parking)

### Sample Data

The initialization script creates:
- 24 hours of historical metrics
- Status change history
- Realistic device behavior patterns

## 🔍 Monitoring

### Health Checks

- **API Health**: `GET /api/v1/health`
- **Detailed Health**: `GET /api/v1/health/detailed`

### Logs

View service logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f data_collector
```

## 🚀 Production Deployment

### Security Considerations

1. **Change Default Passwords**: Update Grafana and database passwords
2. **API Authentication**: Implement proper authentication
3. **Network Security**: Use proper firewall rules
4. **SSL/TLS**: Enable HTTPS for production

### Scaling

- **Database**: Consider PostgreSQL clustering
- **API**: Use load balancers for multiple API instances
- **Collectors**: Scale collectors based on device count
- **Caching**: Optimize Redis configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
1. Check the logs: `docker-compose logs`
2. Verify database connection
3. Check API health endpoints
4. Review Grafana data source configuration

## 🔮 Future Enhancements

- [ ] Real-time alerts and notifications
- [ ] Machine learning for anomaly detection
- [ ] Mobile app for device management
- [ ] Advanced analytics and reporting
- [ ] Integration with external monitoring tools