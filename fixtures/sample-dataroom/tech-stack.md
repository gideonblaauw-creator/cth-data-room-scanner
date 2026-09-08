# Technology Stack

## Edge firmware

- **MCU:** STM32L4 series
- **RTOS:** Zephyr 3.5
- **Sensors:** Capacitive soil moisture, ambient temp/humidity
- **Connectivity:** LoRaWAN to on-site gateway

## Cloud

- **Backend:** Python 3.12, FastAPI
- **Database:** PostgreSQL 16 (managed)
- **Hosting:** EU region (Frankfurt)
- **Auth:** OAuth2 + magic links for grower dashboard

## ML pipeline

- Moisture forecast model trained on 18 months of synthetic + pilot data
- Inference on gateway; cloud retraining weekly

## Security posture (summary)

- TLS 1.3 for all cloud traffic
- Device certificates provisioned at factory
- No secrets or API keys in this document
