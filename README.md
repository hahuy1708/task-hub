# TaskHub

TaskHub là API quản lý công việc được xây dựng bằng FastAPI

## Yêu cầu

- Python 3.13 trở lên
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

Cài `uv` trên Windows bằng PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Kiểm tra cài đặt:

```bash
uv --version
```

## Cài đặt project

```
git clone https://github.com/hahuy1708/task-hub.git
```

Mở terminal tại thư mục `task-hub/` (thư mục chứa `pyproject.toml`) và chạy:

```bash
uv sync
```

Lệnh này tạo môi trường `.venv` nếu chưa có và cài dependency từ `pyproject.toml` cùng `uv.lock`, bao gồm các công cụ dev `pytest`, `ruff` và `mypy`.


Tạo file cấu hình local từ mẫu:

```bash
cp .env.example .env
```

Sau đó điền đầy đủ thông tin vào file `.env`

Tạo bảng từ migration:

```bash
uv run alembic upgrade head
```

Chạy API:

```bash
uv run fastapi dev src/task_hub/main.py
```


## API docs

API chạy tại <http://127.0.0.1:8000> sau khi làm theo bước Chạy API ở trên.

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Health check: <http://127.0.0.1:8000/health>

Dừng server bằng `Ctrl+C`.

## Chạy kiểm tra

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

## Cấu trúc mã nguồn

```text
src/task_hub/
├── dependencies.py
├── main.py
├── models/
├── routers/
├── repositories/
├── schemas/
└── services/

tests/
```

- `models/`: entity và enum của Task.
- `schemas/`: kiểm tra dữ liệu vào và định dạng dữ liệu trả về.
- `services/`: thao tác và quy tắc nghiệp vụ.
- `repositories/`: thao tác với cơ sở dữ liệu.
- `routers/`: các HTTP endpoint.
- `dependencies.py`: cung cấp `TaskService` cho router.
- `main.py`: khởi tạo FastAPI, đăng ký router và xử lý lỗi 404.
