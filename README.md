# Dialix Backend

## Overview

The backend for Dialix is built using `FastAPI`. This repository contains three main services:

- **RestAPI Service**: Located in the `backend/` folder. Implements API endpoints and business logic.
- **API Worker Service**: Defined in `workers/api.py`. Interacts with external services to handle various tasks.
- **Data Worker Service**: Defined in `workers/data.py`. Operates as a background service (daemon) to receive and insert data into the appropriate tables, usually from the API Worker.

These workers run as separate processes/services/containers using Celery. RabbitMQ is used for message queuing.

## Technology Stack

- **Python**: `3.11.2` (tested)
- **FastAPI**, **Celery**, and additional AI/ML dependencies
- **Operating System**: Debian-based distributions (e.g., Ubuntu). Compatibility with Windows/macOS is untested.
- **PostgreSQL**: Version `16/17`
- **Docker**, **Redis**, and **RabbitMQ**

## Setup Instructions

Ensure your system has the necessary build tools:

```bash
sudo apt-get install make build-essential gcc make
```

Clone the repository and install dependencies from the requirements.txt file.

Create the database(use `psql`):

```sql
create database dialix;
```

Start **redis**

```shell
docker run -d --name redis -p 6379:6379 redis/redis-stack-server:latest
```

Start **RabbitMQ**

```shell
docker run --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4.0-management
```

## Environment Configuration

Create a `.env` file with the following variables(below template):

```shell
DATABASE_URL=postgresql://<USERNAME>:<PASSWORD>@localhost:5432/dialix
AMQP_URL=amqp://<USERNAME>:<PASSWORD>@localhost:5672
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=...
ANTI_SLOW_DOWN=true

MOHIRAI_API_KEY=...

DEPLOYMENT_NAME=gpt4o
OPENAI_API_KEY=...
OPENAI_API_BASE=https://mohir-temp-punct.openai.azure.com/
OPENAI_API_TYPE=azure
OPENAI_API_VERSION=2023-05-15
AUTH_SECRET_KEY=...
AUTH_ALGORITHM=HS256
GOOGLE_APPLICATION_CREDENTIALS=./keys/prod.json
MODEL_PATH=./models/model.h5

BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=c42fFSCEcedcsdvRUR3vteJC3FWVDEWV

TORCH_FORCE_RELOAD=false
```

Ensure you have the necessary AI models, Google credentials, and other secret variables.

## Database Operations

The project previously relied on raw SQL queries, which were cumbersome for complex operations. Now, most database-related code uses SQLAlchemy.

- Database models and sessions: Located in the `database/` folder.
- Utility functions and business logic: Found in the `services/` folder.
- Migrations: Managed using **Alembic**. Configuration files are in the `alembic/ `folder.

### Creating and Applying Migrations

To create a new migration:

```shell
alembic revision --autogenerate -m "<Description>"
```

Apply the migration:

```shell
alembic upgrade head
```

Whenever you make any database related stuff, just create new migration, and then apply it.

## Running the Services

Ensure PostgreSQL, Redis, and RabbitMQ are running. Use the following commands to start services:

RestAPI Service:

```shell
make run-local
```

API Worker:

```shell
make run-api-worker
```

Data Worker:

```shell
make run-data-worker
```

Development Guidelines
Key Components

- `backend/`: API definitions and business logic.
- `workers/api.py`: AI-related operations.
- `workers/data.py`: Post-processing and data insertion.

Important Files and Directories

- `db.py`: Contains legacy raw SQL operations.
- `schemas.py`: Defines Pydantic models for request/response validation.
- `server.py`: Entry point for the FastAPI app.
- `routers/`: Modular API endpoints (e.g., routers/dashboard.py).
- `database/`: SQLAlchemy models and session management.
- `services/`: All database operations (CRUD, filtering).
- `core/`: Essential configurations (settings, exception handlers dependency injection).
- `auth/`: Basic authentication for admin endpoints. User authentication uses JWT.
- `tasks/`: Celery tasks for background processing.

Ensure to apply these changes in the development/production environments.

## Code Quality

Use tools like **ruff** for linting and formatting.

## CI/CD and Deployment

The `.gitlab-ci.yml` file handles CI/CD. Based on the branch name, the pipeline deploys to the appropriate environment (development or production). Only the main branch deploys to production.

Create a feature branch from dev. Push changes and open a merge request to dev. Test on the development environment. Open a PR to main for production deployment.

Avoid selecting "delete branch after merge" to retain feature branches.

## Notes, Findings and Recommendations

Some stuff can be done, if someone has enough time:

- Separate AI services from the RestAPI to reduce resource consumption.
- Complete migration to SQLAlchemy (currently ~70% done).
- Replace long polling with WebSockets for real-time updates.
- Migrate the frontend to React and deploy via Vercel.
- Optimize Docker images for storage efficiency.

Stage mapping, generated from Bitrix via script:

```json
{
  "NEW": "Jarayonda",
  "CALL": "Звонок",
  "CLIENT": "Клиенты",
  "CUSTOMER": "Клиент",
  "EMPLOYEES_1": "менее 50",
  "IN_WORK": "В работе",
  "IT": "Информационные технологии",
  "SALE": "Продажа",
  "PLANNED": "В планах",
  "INFO": "Информация",
  "DRAFT": "Новое",
  "HNR_RU_1": "г-н",
  "DT31_1:N": "Новый",
  "DT36_3:DRAFT": "Черновик",
  "C3:NEW": "Sifatli leads",
  "UC_WR2IMO": "Quiz",
  "C7:NEW": "Kontaktlar",
  "C9:NEW": "Sifatli Lid",
  "C15:NEW": "Qo'ng'iroqlar",
  "C16:NEW": "Ro'yhat",
  "DT39_11:DRAFT": "Черновик",
  "DT39_11:COORDINATION": "Согласование",
  "DT39_11:FILLING": "Заполнение",
  "IN_PROCESS": "Internet",
  "SUPPLIER": "Поставщик",
  "EMPLOYEES_2": "50-250",
  "SUCCESS": "Успешно",
  "TELECOM": "Телекоммуникации и связь",
  "COMPLEX": "Комплексная продажа",
  "PROCESS": "В работе",
  "PHONE": "Телефонный звонок",
  "SENT": "Отправлено клиенту",
  "HNR_RU_2": "г-жа",
  "DT31_1:S": "Отправлен клиенту",
  "UC_DTTX6O": "Gaplashyapman",
  "DT36_3:PROCESSING": "На согласовании",
  "UC_2MBCQS": "TOF_B_18-25 Qancha pul",
  "C7:PREPARATION": "Ko'tarmadi",
  "C3:UC_25TIME": "Ko'tarmadi",
  "C9:PREPAYMENT_INVOICE": "Ko'tarmadi",
  "C15:PREPARATION": "Yangi lidlar",
  "C16:PREPARATION": "Keyinroq bog'lanish",
  "PARTNER": "Партнер",
  "COMPETITOR": "Конкурент",
  "EMPLOYEES_3": "250-500",
  "WRONG_NUMBER": "Неверный номер",
  "MANUFACTURING": "Производство",
  "GOODS": "Продажа товара",
  "COMPLETE": "Выполнена",
  "MESSAGE": "Отправлен email",
  "APPROVED": "Принято",
  "DT31_1:P": "Оплачен",
  "DT36_3:SENT": "Отправлен",
  "UC_486W7O": "Q.A kursi Target",
  "C7:PREPAYMENT_INVOICE": "Keyinroq",
  "C9:EXECUTING": "Gaplashyapman",
  "UC_5BV30V": "MohirdevSalesBot",
  "C15:PREPAYMENT_INVOIC": "Ofisga keladi",
  "C3:UC_LS7HJK": "Jarayonda",
  "DT39_11:SIGNING": "Подписание",
  "WEBFORM": "CRM-форма",
  "OTHER": "Другое",
  "EMPLOYEES_4": "более 500",
  "STOP_CALLING": "Больше не звонить",
  "BANKING": "Банковские услуги",
  "SERVICES": "Продажа услуги",
  "CANCELED": "Отменена",
  "DECLAINED": "Отклонено",
  "UC_GDK4DQ": "Ko'tarmadi",
  "DT31_1:D": "Не оплачен",
  "DT36_3:SEMISIGNED": "Частично подписан",
  "UC_PSK6LM": "Sotib oldi Old",
  "C9:FINAL_INVOICE": "Jarayonda",
  "C15:EXECUTING": "Ofisga keldi",
  "DT39_11:COMPLETED": "Результат",
  "C7:UC_UJDKF1": "Test shartnoma",
  "C3:UC_3G1TOC": "Ibrat farzandlari",
  "RECOMMENDATION": "Tanishlar",
  "CONSULTING": "Консалтинг",
  "SERVICE": "Сервисное обслуживание",
  "APOLOGY": "Анализ причины провала",
  "UC_IPGAVL": "Xorazm Varonka",
  "DT36_3:SIGNED": "Полностью подписан",
  "C7:EXECUTING": "Negativ",
  "C9:UC_9P4GE8": "varonka",
  "C16:WON": "Ma'lumot berildi",
  "UC_NLHMD0": "Ma'lumot berilmagan",
  "C3:UC_HG0320": "Dostup berish kerak",
  "DT39_11:ARCHIVE": "В архиве",
  "FINANCE": "Финансы",
  "DT36_3:ARCHIVE": "В архив",
  "UC_D9LOU6": "Shartnoma asosida",
  "UC_593HPS": "Darsturci nima qiladi",
  "C7:FINAL_INVOICE": "Pozitiv",
  "C9:WON": "Sotib oldi",
  "UC_58J5U1": "Quiz",
  "C15:WON": "Sotib oldi",
  "C16:LOSE": "Ma'lumot bermadi",
  "DT39_11:FAILURE": "Не подписано",
  "C3:UC_GEF8BL": "Marketing",
  "CONVERTED": "Sifatli Leads",
  "CALLBACK": "Instagram",
  "GOVERNMENT": "Правительство",
  "WON": "Sotib oldi",
  "DT36_3:NOTSIGNED": "Не подписано",
  "C3:WON": "Sotib oldi",
  "C7:WON": "Tugatildi",
  "C9:LOSE": "Savatcha",
  "C15:LOSE": "Olmaydi",
  "JUNK": "Sifatsiz Leads",
  "RC_GENERATOR": "Facebook",
  "DELIVERY": "Доставка",
  "LOSE": "Сделка провалена",
  "C3:LOSE": "Sotib olmaydi",
  "C7:LOSE": "Ko'rib chiqilmadi",
  "STORE": "Telegram",
  "ENTERTAINMENT": "Развлечения",
  "NOTPROFIT": "Не для получения прибыли",
  "N": "Новый",
  "UC_QRSDZN": "TOF_B_18-22",
  "S": "Отправлен клиенту",
  "UC_JB7MW7": "Vaucher",
  "1|OPENLINE": "Онлайн-чат - Открытая линия mohirdev",
  "11|TELEGRAM": "Telegram - Open Channel 6",
  "13|TELEGRAM": "Telegram - Open Channel 7",
  "15|TELEGRAM": "Telegram - MohirdevSales Bot",
  "17|TELEGRAM": "Telegram - Открытая линия 9",
  "17|FACEBOOK": "Facebook - Открытая линия 9",
  "17|FACEBOOKCOMMENTS": "Facebook*: Комментарии - Открытая линия 9",
  "15|OPENLINE": "Онлайн-чат - MohirdevSales Bot",
  "P": "Оплачен",
  "5|TELEGRAM": "Telegram - Открытая линия 3",
  "D": "Не оплачен",
  "UC_TERTSY": "To'lovgacha",
  "UC_1CUWQA": "To'liq forma",
  "UC_QFI4IA": "Kodyozmasdan",
  "UC_CQ42A7": "Sayt",
  "UC_TAYQOK": "Happy new year"
}
```
